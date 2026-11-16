#!/bin/bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/.config/omarchy/telegram-theme"
HOOKS_DIR="$HOME/.config/omarchy/hooks"

echo "=== Установка Omarchy Telegram Theme Sync ==="

mkdir -p "$DEST"

# Копируем проект в ~/.config/omarchy/telegram-theme (если запускается из другого места)
if [[ "$DIR" != "$DEST" ]]; then
  cp -r "$DIR"/* "$DEST/"
fi

if [[ ! -x "$DEST/bin/sync-tdata-keys" ]]; then
  gcc -O2 "$DEST/bin/sync-tdata-keys.c" -lcrypto -o "$DEST/bin/sync-tdata-keys" 2>/dev/null || true
fi
chmod +x "$DEST/omarchy-telegram-theme.py" "$DEST/bin/"* "$DEST/hooks/"* "$DEST/install.sh" 2>/dev/null || true
"$DEST/bin/sync-tdata-keys" >/dev/null 2>&1 || true

# Устанавливаем хуки Omarchy
mkdir -p "$HOOKS_DIR/theme-set.d" "$HOOKS_DIR/post-boot.d"
cp "$DEST/hooks/theme-set" "$HOOKS_DIR/theme-set.d/telegram-theme"
cp "$DEST/hooks/post-boot" "$HOOKS_DIR/post-boot.d/telegram-theme"
chmod +x "$HOOKS_DIR/theme-set.d/telegram-theme" "$HOOKS_DIR/post-boot.d/telegram-theme"

# Генерируем тему для текущей темы Omarchy
"$DEST/bin/sync.sh"

echo ""
echo "Установка успешно завершена!"
echo ""
echo "Разовая активация темы в Telegram Desktop / AyuGram:"
echo "1. Откройте Настройки -> Настройки чатов -> три точки вверху -> Выбрать из файла"
echo "2. Выберите файл:"
echo "   $DEST/omarchy.tdesktop-theme"
echo ""
echo "После этого тема будет автоматически переключаться при любой смене темы в Omarchy!"
