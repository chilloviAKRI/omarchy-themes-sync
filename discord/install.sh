#!/bin/bash
# Install / activate Omarchy Discord sync system
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/.config/omarchy/discord-theme"
HOOKS_THEME="$HOME/.config/omarchy/hooks/theme-set.d"
HOOKS_BOOT="$HOME/.config/omarchy/hooks/post-boot.d"

echo "=== Installing Omarchy Discord & Vencord Theme Sync ==="

mkdir -p "$DEST" "$HOOKS_THEME" "$HOOKS_BOOT"

# Copy files if running from cloned repository
if [[ "$DIR" != "$DEST" ]]; then
    cp -r "$DIR"/* "$DEST/"
fi

# Check if Vencord is installed
if [ ! -d "$HOME/.config/Vencord/dist" ]; then
    echo "Notice: Vencord does not seem to be patched into Discord yet."
    if [ -x "$HOME/.local/bin/vencord-installer" ]; then
        echo "Running vencord-installer..."
        "$HOME/.local/bin/vencord-installer" -install -branch stable || true
    fi
fi

# Make scripts executable
chmod +x "$DEST/omarchy-discord-theme.py"
chmod +x "$DEST/bin/sync.sh"
chmod +x "$DEST/hooks/"*

# Install hooks
install -m 755 "$DEST/hooks/theme-set" "$HOOKS_THEME/discord-theme"
install -m 755 "$DEST/hooks/post-boot" "$HOOKS_BOOT/discord-theme"

# Generate theme now
"$DEST/bin/sync.sh"

echo "=== Done! Discord theme will sync automatically with Omarchy. ==="
