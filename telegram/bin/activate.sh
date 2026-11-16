#!/bin/bash
# One-time helper: make AyuGram/Telegram Desktop USE the generated theme.
#
# The .tdesktop-theme zip contains BOTH colors.tdesktop-theme AND a 1x1
# background.png (dark for dark Omarchy themes, light for light ones).
# Telegram needs that background to register the theme with the correct
# light/dark type - without it, it falls back to the default (light)
# wallpaper and calls even a fully dark palette a "light theme".
#
# After the first application the file is watched IN PLACE (same inode) by
# QFileSystemWatcher, so every `omarchy theme set ...` updates AyuGram live.
set -uo pipefail

DIR="$HOME/.config/omarchy/telegram-theme"
OUT="$DIR/omarchy.tdesktop-theme"
[[ -f $OUT ]] || "$DIR/bin/sync.sh"

cat <<EOF
== Telegram / AyuGram theme activation (ONE time only) ==

Generated theme file:
  $OUT

Apply it from AyuGram:
  Settings -> Chat Settings -> "Choose from file", pick the path above
or:
  drag the file into any chat and click it in the attachment preview.

The zip now ships a dark 1x1 background.png (like the stock Telegram night
themes), so Telegram registers the theme as DARK. Every Omarchy theme switch
rewrites this same file in place and AyuGram re-applies it live - no restart.

Current Omarchy theme: $(cat "$HOME/.local/state/omarchy/current/theme.name" 2>/dev/null || echo '?')
EOF

if [[ -t 0 ]] && command -v wl-copy >/dev/null 2>&1; then
  read -r -p "Copy the theme path to clipboard? [y/N] " answer
  if [[ ${answer,,} == y* ]]; then
    printf '%s' "$OUT" | wl-copy
    echo "Path copied."
  fi
fi
