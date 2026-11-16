#!/bin/bash
# Regenerate the Discord theme for Vencord/Vesktop from the current Omarchy theme.
# Vencord and Vesktop watch the theme files and hot-reload changes in real-time.
set -uo pipefail

DIR="$HOME/.config/omarchy/discord-theme"
GEN="$DIR/omarchy-discord-theme.py"
LOG="$HOME/.local/state/omarchy/discord-theme.log"
THEME_NAME="${1:-$(cat "$HOME/.local/state/omarchy/current/theme.name" 2>/dev/null || echo omarchy)}"

mkdir -p "$(dirname "$LOG")"

if ! python3 "$GEN" --theme-name "$THEME_NAME" >>"$LOG" 2>&1; then
  echo "[$(date -Is)] FAILED to generate Discord theme for '$THEME_NAME'" >>"$LOG"
  exit 1
fi

# Pulse rewrite ensures the file change event fires reliably
sleep 0.2
python3 "$GEN" --theme-name "$THEME_NAME" --pulse >>"$LOG" 2>&1 || true

echo "[$(date -Is)] applied Discord theme '$THEME_NAME'" >>"$LOG"
