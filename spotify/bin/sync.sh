#!/bin/bash
# Regenerate the Spotify Spicetify theme from the active Omarchy theme.
set -uo pipefail

DIR="$HOME/.config/omarchy/spotify-theme"
GEN="$DIR/omarchy-spotify-theme.py"
LOG="$HOME/.local/state/omarchy/spotify-theme.log"
THEME_NAME="${1:-$(cat "$HOME/.local/state/omarchy/current/theme.name" 2>/dev/null || echo omarchy)}"

mkdir -p "$(dirname "$LOG")"

if ! python3 "$GEN" --theme-name "$THEME_NAME" >>"$LOG" 2>&1; then
    echo "[$(date -Is)] FAILED to generate Spotify theme for '$THEME_NAME'" >>"$LOG"
    exit 1
fi

echo "[$(date -Is)] applied Spotify theme '$THEME_NAME'" >>"$LOG"
