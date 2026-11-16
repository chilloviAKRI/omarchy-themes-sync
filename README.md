# 🎨 Omarchy Themes Sync

> Dynamic, real-time theme synchronization for **Telegram Desktop / AyuGram**, **Discord (Vencord)**, and **Spotify (Spicetify)** with [Omarchy](https://github.com/omarchy/omarchy) Linux desktop themes.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: Linux](https://img.shields.io/badge/Platform-Linux-orange.svg)]()
[![Omarchy Compatible](https://img.shields.io/badge/Omarchy-Compatible-emerald.svg)]()

---

## 🌟 Highlights

- ⚡ **Zero-Restart Live Hot-Reload**: Themes switch instantly across all apps when changing the desktop theme via Omarchy (`omarchy theme set <name>`).
- 🌗 **Full Dark & Light Mode Support**: Seamless adaptation for both dark (`last-horizon`, `catppuccin-mocha`, `gruvbox`) and light palettes (`flexoki-light`, `catppuccin-latte`).
- 💎 **macOS Blue Selection**: Unified native-feel selection indicator (`#0063e6` with `#ffffff` text) across all platforms.
- 🎵 **Spotify Clean UX**:
  - Distinguishable, high-contrast track & volume slider bars.
  - Eliminated distracting slider thumb ball for a minimalist, modern aesthetic.
  - Custom light theme overrides for navigation buttons, search pills, filter chips, right-sidebar NowPlaying cards, and dynamic playlist header contrast.
- 📱 **Telegram Dual-Mode Integration**: Generates single unified `.tdesktop-theme` package syncing both Day and Night modes with running system colors.

---

## 📦 What's Included

```
omarchy-themes-sync/
├── install.sh                  # Unified interactive / CLI installer
├── telegram/                   # Telegram Desktop / AyuGram theme generator
│   ├── omarchy-telegram-theme.py
│   ├── bin/sync-tdata-keys.c   # C helper for tdata theme key table sync
│   ├── base/                   # Base palette templates
│   └── hooks/                  # Omarchy theme-set & post-boot hooks
├── discord/                    # Discord / Vencord QuickCSS generator
│   ├── omarchy-discord-theme.py
│   └── hooks/                  # Omarchy theme-set & post-boot hooks
└── spotify/                    # Spotify / Spicetify theme generator & extension
    ├── omarchy-spotify-theme.py
    ├── extensions/omarchy-sync.js  # Live WebSocket/polling hot-reload extension
    └── hooks/                  # Omarchy theme-set & post-boot hooks
```

---

## 🚀 Quick Start & Installation

Clone the repository and run the installer:

```bash
git clone https://github.com/chilloviAKRI/omarchy-themes-sync.git
cd omarchy-themes-sync
chmod +x install.sh
./install.sh
```

### CLI Options

You can install all components at once or selectively:

```bash
# Install everything (Telegram, Discord, Spotify)
./install.sh --all

# Install individual components
./install.sh --telegram
./install.sh --discord
./install.sh --spotify
```

---

## ⚙️ App Prerequisites & One-Time Setup

### 1. ✈️ Telegram Desktop / AyuGram

**Requirements**: `python3`, `gcc`, `libcrypto` (OpenSSL).

**One-Time Theme Activation**:
1. Open Telegram Desktop / AyuGram.
2. Go to: **Settings** (`Настройки`) ➔ **Chat Settings** (`Настройки чатов`) ➔ click the **three vertical dots** (`⋮`) at top right ➔ **Choose from file** (`Выбрать из файла`).
3. Select the generated theme:
   ```
   ~/.config/omarchy/telegram-theme/omarchy.tdesktop-theme
   ```
4. **Light mode sync (Важно для синхронизации светлой темы)**:
   - Switch Telegram to **Day Mode** (click the sun/moon icon).
   - Click the three dots ➔ **Choose from file** again and select `~/.config/omarchy/telegram-theme/omarchy.tdesktop-theme`.
   - Now both Night and Day modes track `omarchy.tdesktop-theme` and dynamically update whenever you switch your Omarchy theme!

---

### 2. 🎮 Discord (Vencord)

**Requirements**: Discord with [Vencord](https://vencord.dev) installed.

**One-Time Setup**:
1. Open Discord Settings ➔ **Vencord** ➔ **Vencord Settings**.
2. Under **QuickCSS**, ensure the toggle is **Enabled**.
3. The generator writes directly to `~/.config/Vencord/settings/quickCss.css`. Vencord detects file changes and hot-reloads instantly without needing Discord to restart.

---

### 3. 🎧 Spotify (Spicetify)

**Requirements**: Spotify Desktop with [Spicetify CLI](https://spicetify.app) installed.

**One-Time Setup**:
1. The installer automatically configures `~/.config/spicetify/config-xpui.ini`:
   - `current_theme = omarchy`
   - `color_scheme = Omarchy`
   - `extensions = omarchy-sync.js`
2. Run spicetify apply once if prompted:
   ```bash
   spicetify apply
   ```
3. Spotify will now hot-reload theme changes on the fly via the `omarchy-sync.js` extension without interrupting playback.

---

## 🧪 Testing Manual Theme Changes

To test how your apps adapt to different themes without changing your desktop:

```bash
# Test a light theme (e.g. Flexoki Light)
python3 ~/.config/omarchy/spotify-theme/omarchy-spotify-theme.py --colors-file /usr/share/omarchy/themes/flexoki-light/colors.toml --theme-name "flexoki-light"
python3 ~/.config/omarchy/discord-theme/omarchy-discord-theme.py --colors-file /usr/share/omarchy/themes/flexoki-light/colors.toml --theme-name "flexoki-light"
python3 ~/.config/omarchy/telegram-theme/omarchy-telegram-theme.py --colors-file /usr/share/omarchy/themes/flexoki-light/colors.toml --theme-name "flexoki-light"

# Return to active Omarchy desktop theme
~/.config/omarchy/hooks/theme-set.d/spotify-theme
~/.config/omarchy/hooks/theme-set.d/discord-theme
~/.config/omarchy/hooks/theme-set.d/telegram-theme
```

---

## 🛠️ How It Works Behind the Scenes

Omarchy executes scripts in `~/.config/omarchy/hooks/theme-set.d/` whenever the desktop theme changes:
1. **Hook Trigger**: `theme-set.d/{telegram,discord,spotify}-theme` is called with the theme name as `$1`.
2. **Palette Resolution**: The generators read `~/.local/state/omarchy/current/theme/colors.toml` (and `/usr/share/omarchy/themes/<name>/colors.toml`).
3. **Smart Adaptation**:
   - Contrast calculation (adjusts elevation tints and background brightness).
   - Selection highlighting locked to `#0063e6`.
   - SVG icons, badges, borders, and buttons colored dynamically to match active accent colors.
4. **Instant Ingestion**: Files are injected directly into each client's storage or hot-reload bus.

---

## 🤝 Contributing

Contributions, bug reports, and theme improvements are welcome! Feel free to open an issue or submit a pull request.

---

## 📄 License

MIT License. Created by [chilloviAKRI](https://github.com/chilloviAKRI).
