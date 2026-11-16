#!/bin/bash
# Regenerate the Telegram/AyuGram theme from the current Omarchy theme and
# rewrite the .tdesktop-theme file IN PLACE (same inode), so the running
# AyuGram QFileSystemWatcher re-applies it immediately - no restart needed.
set -uo pipefail

DIR="$HOME/.config/omarchy/telegram-theme"
GEN="$DIR/omarchy-telegram-theme.py"
OUT="$DIR/omarchy.tdesktop-theme"
LOG="$HOME/.local/state/omarchy/telegram-theme.log"
THEME_NAME="${1:-$(cat "$HOME/.local/state/omarchy/current/theme.name" 2>/dev/null || echo omarchy)}"

mkdir -p "$(dirname "$LOG")"

# Keep day and night theme keys synchronized in Telegram/AyuGram tdata
"$DIR/bin/sync-tdata-keys" >>"$LOG" 2>&1 || true

if ! python3 "$GEN" --theme-name "$THEME_NAME" >>"$LOG" 2>&1; then
  echo "[$(date -Is)] FAILED to generate theme for '$THEME_NAME'" >>"$LOG"
  notify-send -u normal "Telegram theme" "Could not sync with Omarchy theme. See $LOG" 2>/dev/null || true
  exit 1
fi

# A second, identical-content rewrite. If the first inotify event caught the
# file mid-write (a truncated zip), this pulse makes AyuGram apply a complete
# one. The pulse only changes a comment in the palette header.
sleep 0.4
python3 "$GEN" --theme-name "$THEME_NAME" --pulse >>"$LOG" 2>&1 || true

echo "[$(date -Is)] applied '$THEME_NAME' -> $OUT" >>"$LOG"
