#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <sys/stat.h>
#include <openssl/sha.h>
#include <openssl/md5.h>
#include <openssl/aes.h>
#include <openssl/evp.h>

static void derive_keys(const unsigned char *key, const unsigned char *msgKey, uint32_t x, unsigned char *aesKey, unsigned char *aesIV) {
    unsigned char sha1_a[20], sha1_b[20], sha1_c[20], sha1_d[20];
    unsigned char buf_a[48], buf_b[48], buf_c[48], buf_d[48];

    memcpy(buf_a, msgKey, 16);
    memcpy(buf_a + 16, key + x, 32);
    SHA1(buf_a, sizeof(buf_a), sha1_a);

    memcpy(buf_b, key + 32 + x, 16);
    memcpy(buf_b + 16, msgKey, 16);
    memcpy(buf_b + 32, key + 48 + x, 16);
    SHA1(buf_b, sizeof(buf_b), sha1_b);

    memcpy(buf_c, key + 64 + x, 32);
    memcpy(buf_c + 32, msgKey, 16);
    SHA1(buf_c, sizeof(buf_c), sha1_c);

    memcpy(buf_d, msgKey, 16);
    memcpy(buf_d + 16, key + 96 + x, 32);
    SHA1(buf_d, sizeof(buf_d), sha1_d);

    memcpy(aesKey, sha1_a, 8);
    memcpy(aesKey + 8, sha1_b + 8, 12);
    memcpy(aesKey + 20, sha1_c + 4, 12);

    memcpy(aesIV, sha1_a + 8, 12);
    memcpy(aesIV + 12, sha1_b, 8);
    memcpy(aesIV + 20, sha1_c + 16, 4);
    memcpy(aesIV + 24, sha1_d, 8);
}

static void to_file_part(uint64_t val, char out[17]) {
    for (int i = 0; i < 16; ++i) {
        unsigned char v = (val & 0x0F);
        out[i] = (v < 10) ? ('0' + v) : ('A' + (v - 10));
        val >>= 4;
    }
    out[16] = '\0';
}

static void copy_tdata_file(const char *settings_path, uint64_t src_key, uint64_t dst_key) {
    char dir[1024];
    strncpy(dir, settings_path, sizeof(dir));
    char *slash = strrchr(dir, '/');
    if (!slash) return;
    *slash = '\0';

    char src_part[17], dst_part[17];
    to_file_part(src_key, src_part);
    to_file_part(dst_key, dst_part);

    char src_path[1024], dst_path[1024];
    snprintf(src_path, sizeof(src_path), "%s/%ss", dir, src_part);
    snprintf(dst_path, sizeof(dst_path), "%s/%ss", dir, dst_part);

    FILE *in = fopen(src_path, "rb");
    if (!in) return;
    FILE *out = fopen(dst_path, "wb");
    if (!out) { fclose(in); return; }

    char buf[4096];
    size_t n;
    while ((n = fread(buf, 1, sizeof(buf), in)) > 0) {
        fwrite(buf, 1, n, out);
    }
    fclose(in);
    fclose(out);
    printf("[%s] Cloned theme file: %ss -> %ss\n", settings_path, src_part, dst_part);
}

static int process_settings_file(const char *path) {
    if (access(path, F_OK) != 0) {
        return 0; // File does not exist, nothing to do
    }

    FILE *f = fopen(path, "rb");
    if (!f) return 0;

    char magic[4];
    if (fread(magic, 1, 4, f) != 4 || memcmp(magic, "TDF$", 4) != 0) {
        fclose(f);
        return 0;
    }

    uint32_t version;
    if (fread(&version, 4, 1, f) != 1) { fclose(f); return 0; }

    fseek(f, 0, SEEK_END);
    long total_size = ftell(f);
    fseek(f, 8, SEEK_SET);

    long dataSize = total_size - 8 - 16;
    if (dataSize <= 0) { fclose(f); return 0; }

    unsigned char *file_payload = malloc(dataSize);
    if (!file_payload) { fclose(f); return 0; }
    if ((long)fread(file_payload, 1, dataSize, f) != dataSize) {
        free(file_payload);
        fclose(f);
        return 0;
    }

    unsigned char file_md5[16];
    if (fread(file_md5, 1, 16, f) != 16) {
        free(file_payload);
        fclose(f);
        return 0;
    }
    fclose(f);

    // Verify MD5 signature
    MD5_CTX md5_ctx;
    MD5_Init(&md5_ctx);
    MD5_Update(&md5_ctx, file_payload, dataSize);
    int32_t ds32 = (int32_t)dataSize;
    MD5_Update(&md5_ctx, &ds32, sizeof(ds32));
    MD5_Update(&md5_ctx, &version, sizeof(version));
    MD5_Update(&md5_ctx, magic, 4);
    unsigned char calc_md5[16];
    MD5_Final(calc_md5, &md5_ctx);
    if (memcmp(calc_md5, file_md5, 16) != 0) {
        free(file_payload);
        return 0;
    }

    uint32_t salt_len = __builtin_bswap32(*(uint32_t*)file_payload);
    if (salt_len != 32 || 4 + salt_len + 4 > (uint32_t)dataSize) {
        free(file_payload);
        return 0;
    }
    unsigned char *salt = file_payload + 4;
    uint32_t enc_len = __builtin_bswap32(*(uint32_t*)(file_payload + 4 + salt_len));
    if (enc_len <= 16 || 4 + salt_len + 4 + enc_len > (uint32_t)dataSize) {
        free(file_payload);
        return 0;
    }
    unsigned char *enc = file_payload + 4 + salt_len + 4;

    unsigned char key[256];
    PKCS5_PBKDF2_HMAC_SHA1("", 0, salt, salt_len, 4, 256, key);

    unsigned char *msgKey = enc;
    unsigned char *encData = enc + 16;
    uint32_t fullLen = enc_len - 16;

    unsigned char aesKeyDec[32], aesIVDec[32];
    derive_keys(key, msgKey, 8, aesKeyDec, aesIVDec);

    unsigned char *decrypted = malloc(fullLen);
    if (!decrypted) { free(file_payload); return 0; }

    AES_KEY rkey;
    AES_set_decrypt_key(aesKeyDec, 256, &rkey);
    unsigned char iv_dec_init[32];
    memcpy(iv_dec_init, aesIVDec, 32);
    AES_ige_encrypt(encData, decrypted, fullLen, &rkey, iv_dec_init, AES_DECRYPT);

    unsigned char sha1_check[20];
    SHA1(decrypted, fullLen, sha1_check);
    if (memcmp(sha1_check, msgKey, 16) != 0) {
        free(decrypted);
        free(file_payload);
        return 0;
    }

    uint32_t dataLen = *(uint32_t*)decrypted;
    int patched = 0;
    for (uint32_t i = 4; i + 24 <= 4 + dataLen; i++) {
        uint32_t bId = __builtin_bswap32(*(uint32_t*)(decrypted + i));
        if (bId == 0x54) { // dbiThemeKey
            uint64_t *pKeyDay = (uint64_t*)(decrypted + i + 4);
            uint64_t *pKeyNight = (uint64_t*)(decrypted + i + 12);
            uint64_t keyDay = __builtin_bswap64(*pKeyDay);
            uint64_t keyNight = __builtin_bswap64(*pKeyNight);

            if (keyDay == 0 && keyNight != 0) {
                uint64_t newKeyDay = keyNight + 1;
                copy_tdata_file(path, keyNight, newKeyDay);
                *pKeyDay = __builtin_bswap64(newKeyDay);
                patched = 1;
                printf("[%s] Assigned keyDay (0x%lx) from keyNight (0x%lx)\n", path, newKeyDay, keyNight);
            } else if (keyNight == 0 && keyDay != 0) {
                uint64_t newKeyNight = keyDay + 1;
                copy_tdata_file(path, keyDay, newKeyNight);
                *pKeyNight = __builtin_bswap64(newKeyNight);
                patched = 1;
                printf("[%s] Assigned keyNight (0x%lx) from keyDay (0x%lx)\n", path, newKeyNight, keyDay);
            } else if (keyDay != 0 && keyNight != 0) {
                printf("[%s] Both theme keys are already configured (keyDay=0x%lx, keyNight=0x%lx)\n", path, keyDay, keyNight);
            }
            break;
        }
    }

    if (!patched) {
        free(decrypted);
        free(file_payload);
        return 1;
    }

    // Re-encrypt
    unsigned char new_msgKey[20];
    SHA1(decrypted, fullLen, new_msgKey);

    unsigned char aesKeyEnc[32], aesIVEnc[32];
    derive_keys(key, new_msgKey, 8, aesKeyEnc, aesIVEnc); // send = false for localstorage

    unsigned char *new_encData = malloc(fullLen);
    AES_KEY ekey;
    AES_set_encrypt_key(aesKeyEnc, 256, &ekey);
    unsigned char iv_enc[32];
    memcpy(iv_enc, aesIVEnc, 32);
    AES_ige_encrypt(decrypted, new_encData, fullLen, &ekey, iv_enc, AES_ENCRYPT);

    // Verify round-trip with a clean IV copy
    unsigned char *test_dec = malloc(fullLen);
    AES_KEY test_rkey;
    AES_set_decrypt_key(aesKeyEnc, 256, &test_rkey);
    unsigned char iv_dec_test[32];
    memcpy(iv_dec_test, aesIVEnc, 32);
    AES_ige_encrypt(new_encData, test_dec, fullLen, &test_rkey, iv_dec_test, AES_DECRYPT);
    if (memcmp(test_dec, decrypted, fullLen) != 0) {
        fprintf(stderr, "[%s] Self-test verification failed, aborting write!\n", path);
        free(test_dec);
        free(new_encData);
        free(decrypted);
        free(file_payload);
        return 0;
    }
    free(test_dec);

    uint32_t new_enc_len = 16 + fullLen;
    uint32_t new_dataSize = 4 + salt_len + 4 + new_enc_len;
    unsigned char *new_payload = malloc(new_dataSize);
    *(uint32_t*)new_payload = __builtin_bswap32(salt_len);
    memcpy(new_payload + 4, salt, salt_len);
    *(uint32_t*)(new_payload + 4 + salt_len) = __builtin_bswap32(new_enc_len);
    memcpy(new_payload + 4 + salt_len + 4, new_msgKey, 16);
    memcpy(new_payload + 4 + salt_len + 4 + 16, new_encData, fullLen);

    // Compute MD5
    MD5_CTX new_md5_ctx;
    MD5_Init(&new_md5_ctx);
    MD5_Update(&new_md5_ctx, new_payload, new_dataSize);
    int32_t new_ds32 = (int32_t)new_dataSize;
    MD5_Update(&new_md5_ctx, &new_ds32, sizeof(new_ds32));
    MD5_Update(&new_md5_ctx, &version, sizeof(version));
    MD5_Update(&new_md5_ctx, magic, 4);
    unsigned char new_md5[16];
    MD5_Final(new_md5, &new_md5_ctx);

    // Backup original
    char bak_path[1024];
    snprintf(bak_path, sizeof(bak_path), "%s.bak", path);
    rename(path, bak_path);

    char tmp_path[1024];
    snprintf(tmp_path, sizeof(tmp_path), "%s.tmp", path);
    FILE *out = fopen(tmp_path, "wb");
    if (!out) {
        rename(bak_path, path);
        free(new_payload);
        free(new_encData);
        free(decrypted);
        free(file_payload);
        return 0;
    }
    fwrite(magic, 1, 4, out);
    fwrite(&version, 4, 1, out);
    fwrite(new_payload, 1, new_dataSize, out);
    fwrite(new_md5, 1, 16, out);
    fclose(out);

    if (rename(tmp_path, path) == 0) {
        printf("[%s] Successfully updated settings with synchronized day/night theme keys!\n", path);
    } else {
        rename(bak_path, path);
    }

    free(new_payload);
    free(new_encData);
    free(decrypted);
    free(file_payload);
    return 1;
}

int main(int argc, char **argv) {
    const char *home = getenv("HOME");
    if (!home) home = "/home/akrilochka";

    char p1[1024], p2[1024];
    snprintf(p1, sizeof(p1), "%s/.local/share/AyuGramDesktop/tdata/settingss", home);
    snprintf(p2, sizeof(p2), "%s/.local/share/TelegramDesktop/tdata/settingss", home);

    process_settings_file(p1);
    process_settings_file(p2);
    return 0;
}
