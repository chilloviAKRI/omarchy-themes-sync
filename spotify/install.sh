#!/bin/bash
# Install / activate Omarchy Spotify sync system
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/.config/omarchy/spotify-theme"
HOOKS_THEME="$HOME/.config/omarchy/hooks/theme-set.d"
HOOKS_BOOT="$HOME/.config/omarchy/hooks/post-boot.d"

echo "=== Installing Omarchy Spotify & Spicetify Theme Sync ==="

mkdir -p "$DEST" "$HOOKS_THEME" "$HOOKS_BOOT"

# Copy files if running from cloned repository
if [[ "$DIR" != "$DEST" ]]; then
    cp -r "$DIR"/* "$DEST/"
fi

# Ensure user launcher exists
mkdir -p "$HOME/.local/bin"
cat <<'EOF' > "$HOME/.local/bin/spotify"
#!/bin/bash
XDG_CONFIG_HOME=${XDG_CONFIG_HOME:-~/.config}

if [[ -f "${XDG_CONFIG_HOME}/spotify-flags.conf" ]]; then
    mapfile -t SPOTIFY_USER_FLAGS <<< "$(grep -v '^#' "${XDG_CONFIG_HOME}/spotify-flags.conf")"
fi

exec "$HOME/.local/share/spotify-client/spotify" "${SPOTIFY_USER_FLAGS[@]}" "$@"
EOF
chmod +x "$HOME/.local/bin/spotify"

# Install spicetify extension if directory exists
if [[ -d "$HOME/.config/spicetify" ]]; then
    mkdir -p "$HOME/.config/spicetify/Extensions"
    cp "$DEST/extensions/omarchy-sync.js" "$HOME/.config/spicetify/Extensions/"
fi

# Make scripts executable
chmod +x "$DEST/omarchy-spotify-theme.py"
chmod +x "$DEST/bin/sync.sh"
chmod +x "$DEST/hooks/"*

# Install hooks
install -m 755 "$DEST/hooks/theme-set" "$HOOKS_THEME/spotify-theme"
install -m 755 "$DEST/hooks/post-boot" "$HOOKS_BOOT/spotify-theme"

# Generate theme now
"$DEST/bin/sync.sh"

echo "=== Done! Spotify theme will sync automatically with Omarchy. ==="
