#!/usr/bin/env python3
"""
Omarchy Spotify Theme Generator using Spicetify.

Reads Omarchy's active palette from ~/.local/state/omarchy/current/theme/colors.toml
and generates:
  ~/.config/spicetify/Themes/omarchy/color.ini
  ~/.config/spicetify/Themes/omarchy/user.css
Then runs `spicetify apply -n` to push changes to Spotify's files.
The `omarchy-sync.js` extension running inside Spotify detects the update
within 1 second and hot-reloads the theme live without interrupting playback.

Key visual constraints:
- Text selection: frozen to macOS blue (#0063e6 with #ffffff text).
- Progress bar & volume slider:
  - Clean bar without thumb: circle thumb handle is permanently removed/hidden.
  - High contrast:
    - Unplayed track: subtle translucent bar (22% white in dark / 18% black in light).
    - Played progress fill: vibrant theme accent color.
    - Hover progress fill: accent hover color.
- Checkmarks, buttons, badges, library panels, and player adapt to Omarchy.
"""

from __future__ import annotations

import argparse
import configparser
import os
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

MACOS_SELECTION_BG = "#0063e6"
MACOS_SELECTION_FG = "#ffffff"


def clean_hex(hex_str: str) -> str:
    s = hex_str.strip().lstrip("#")
    if len(s) == 3:
        s = "".join([c * 2 for c in s])
    return s.lower()


def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    s = clean_hex(hex_str)
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


def rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"{max(0, min(255, int(r))):02x}{max(0, min(255, int(g))):02x}{max(0, min(255, int(b))):02x}"


def adjust_lightness(hex_str: str, factor: float) -> str:
    r, g, b = hex_to_rgb(hex_str)
    if factor >= 0:
        r = r + (255 - r) * factor
        g = g + (255 - g) * factor
        b = b + (255 - b) * factor
    else:
        m = 1.0 + factor
        r = r * m
        g = g * m
        b = b * m
    return rgb_to_hex(round(r), round(g), round(b))


def load_palette(colors_path: Path) -> dict[str, str]:
    if not colors_path.is_file():
        raise FileNotFoundError(f"Colors file not found: {colors_path}")
    with open(colors_path, "rb") as f:
        data = tomllib.load(f)

    palette = {
        "mode": data.get("mode", "dark"),
        "accent": data.get("accent", "#81a1c1"),
        "background": data.get("background", "#2e3440"),
        "dark_background": data.get("dark_background", "#222730"),
        "darker_background": data.get("darker_background", "#191c23"),
        "lighter_background": data.get("lighter_background", "#3b4252"),
        "foreground": data.get("foreground", "#d8dee9"),
        "dark_foreground": data.get("dark_foreground", "#667080"),
        "light_foreground": data.get("light_foreground", "#adb5c4"),
        "bright_foreground": data.get("bright_foreground", "#eceff4"),
        "muted": data.get("muted", "#4c566a"),
        "red": data.get("red", "#bf616a"),
        "yellow": data.get("yellow", "#ebcb8b"),
        "green": data.get("green", "#a3be8c"),
        "cyan": data.get("cyan", "#88c0d0"),
        "blue": data.get("blue", "#81a1c1"),
        "magenta": data.get("magenta", "#b48ead"),
    }
    return palette


def build_color_ini(palette: dict[str, str], theme_name: str) -> str:
    is_dark = palette["mode"] != "light"

    accent = clean_hex(palette["accent"])
    bg = clean_hex(palette["background"])
    dark_bg = clean_hex(palette["dark_background"])
    darker_bg = clean_hex(palette["darker_background"])
    lighter_bg = clean_hex(palette["lighter_background"])

    fg = clean_hex(palette["foreground"])
    bright_fg = clean_hex(palette["bright_foreground"])
    light_fg = clean_hex(palette["light_foreground"])
    muted = clean_hex(palette["muted"])
    red = clean_hex(palette["red"])

    accent_hover = adjust_lightness(accent, 0.15 if is_dark else -0.12)
    accent_active = adjust_lightness(accent, -0.18 if is_dark else -0.25)

    if is_dark:
        main_elevated = lighter_bg
        highlight = lighter_bg
        highlight_elevated = adjust_lightness(lighter_bg, 0.10)
        selected_row = adjust_lightness(bg, 0.12)
    else:
        # In light mode: ensure elevated cards, chips, and inputs are soft light tones
        main_elevated = lighter_bg
        highlight = lighter_bg
        highlight_elevated = adjust_lightness(lighter_bg, -0.06)
        selected_row = dark_bg

    color_ini = f"""[Omarchy]
; Generated for Omarchy theme: {theme_name} ({palette['mode']})
text               = {fg}
subtext            = {light_fg}
nav-active-text    = {bright_fg}
main               = {bg}
main-secondary     = {dark_bg}
main-elevated      = {main_elevated}
highlight          = {highlight}
highlight-elevated = {highlight_elevated}
sidebar            = {dark_bg}
player             = {darker_bg}
card               = {lighter_bg}
shadow             = {darker_bg}
selected-row       = {selected_row}
button             = {accent}
button-secondary   = {light_fg}
button-active      = {accent_hover}
button-disabled    = {muted}
nav-active         = {lighter_bg}
play-button        = {accent}
tab-active         = {lighter_bg}
notification       = {accent}
notification-error = {red}
playback-bar       = {accent}
misc               = {accent}
"""
    return color_ini


def build_user_css(palette: dict[str, str], theme_name: str) -> str:
    accent = palette["accent"]
    bg = palette["background"]
    dark_bg = palette["dark_background"]
    darker_bg = palette["darker_background"]
    lighter_bg = palette["lighter_background"]
    fg = palette["foreground"]
    bright_fg = palette["bright_foreground"]
    light_fg = palette["light_foreground"]
    dark_fg = palette["dark_foreground"]
    muted = palette["muted"]
    is_dark = palette["mode"] != "light"

    accent_hover = adjust_lightness(accent, 0.15 if is_dark else -0.12)
    accent_active = adjust_lightness(accent, -0.18 if is_dark else -0.25)

    border_color = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.08)"
    hover_row = "rgba(255, 255, 255, 0.06)" if is_dark else "rgba(0, 0, 0, 0.04)"
    selected_row = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.08)"
    header_opacity = "1.0" if is_dark else "0.35"

    # HIGH-CONTRAST SLIDER COLORS
    track_bg = "rgba(255, 255, 255, 0.22)" if is_dark else "rgba(0, 0, 0, 0.18)"
    track_hover_bg = "rgba(255, 255, 255, 0.32)" if is_dark else "rgba(0, 0, 0, 0.28)"

    # HIGH-CONTRAST PLAYER CONTROLS & PLAY BUTTON COLORS
    if is_dark:
        control_btn_fg = light_fg if light_fg else "#d8dee9"
        control_btn_hover_fg = bright_fg if bright_fg else "#ffffff"
    else:
        control_btn_fg = light_fg if light_fg else "#403E3C"
        control_btn_hover_fg = fg if fg else "#101010"

    css = f"""/* ==========================================================================
   Omarchy Theme for Spotify (Spicetify)
   Theme: {theme_name} ({palette['mode']})
   ========================================================================== */

/* ==========================================================================
   macOS Blue Selection (FROZEN: per user requirement)
   ========================================================================== */
::selection {{
    background-color: {MACOS_SELECTION_BG} !important;
    color: {MACOS_SELECTION_FG} !important;
}}
::-moz-selection {{
    background-color: {MACOS_SELECTION_BG} !important;
    color: {MACOS_SELECTION_FG} !important;
}}
input::selection,
textarea::selection {{
    background-color: {MACOS_SELECTION_BG} !important;
    color: {MACOS_SELECTION_FG} !important;
}}

/* ==========================================================================
   Omarchy Dynamic Palette Styling
   ========================================================================== */

:root,
.progress-bar {{
    --omarchy-accent: {accent};
    --omarchy-accent-hover: #{accent_hover};
    --omarchy-accent-active: #{accent_active};
    --omarchy-bg: {bg};
    --omarchy-dark-bg: {dark_bg};
    --omarchy-darker-bg: {darker_bg};
    --omarchy-lighter-bg: {lighter_bg};
    --omarchy-fg: {fg};
    --omarchy-bright-fg: {bright_fg};
    --omarchy-light-fg: {light_fg};
    --omarchy-muted: {muted};
    --omarchy-border: {border_color};

    /* Spotify Native Progress Bar & Slider Tokens */
    --bg-color: {track_bg} !important;
    --fg-color: var(--omarchy-accent) !important;
    --is-active-fg-color: var(--omarchy-accent-hover) !important;
    --progress-bar-color: var(--omarchy-accent) !important;
    --background-tinted-base: {track_bg} !important;
}}

/* Main App Background & Content Views */
.Root__top-container,
.main-view-container,
.main-view-container__scroll-node,
.main-view-container__scroll-node-child,
main[role="main"] {{
    background-color: var(--spice-main) !important;
}}

/* Top Navigation Bar */
.main-topBar-background {{
    background-color: var(--spice-main) !important;
}}
.main-topBar-overlay {{
    background-color: var(--spice-main) !important;
}}
header.main-topBar-container {{
    border-bottom: 1px solid var(--omarchy-border) !important;
}}

/* Top Bar Navigation Buttons (< >, Home, Search) */
.main-topBar-historyButtons .main-topBar-button {{
    background-color: var(--spice-card) !important;
    color: var(--spice-text) !important;
    border: 1px solid var(--omarchy-border) !important;
}}
.main-topBar-historyButtons .main-topBar-button:hover:not(:disabled) {{
    background-color: var(--spice-highlight-elevated) !important;
    color: var(--spice-text) !important;
}}
.main-topBar-historyButtons .main-topBar-button:disabled {{
    opacity: 0.35 !important;
    background-color: var(--spice-card) !important;
}}

.qxmESh112XlM9plvFzlP,
button[aria-label="Home"],
button[aria-label="Главная"] {{
    background-color: var(--spice-card) !important;
    color: var(--spice-text) !important;
    border: 1px solid var(--omarchy-border) !important;
}}
.qxmESh112XlM9plvFzlP:hover,
button[aria-label="Home"]:hover,
button[aria-label="Главная"]:hover {{
    background-color: var(--spice-highlight-elevated) !important;
    color: var(--spice-text) !important;
}}

.xLC8OrWuExkkvVyzV00Y .RYFwfQTMR9mVodv10kWY,
form[role="search"] input,
.x-searchInput-searchInputInput {{
    background-color: var(--spice-card) !important;
    color: var(--spice-text) !important;
    border: 1px solid var(--omarchy-border) !important;
}}
.xLC8OrWuExkkvVyzV00Y .RYFwfQTMR9mVodv10kWY::placeholder,
form[role="search"] input::placeholder,
.x-searchInput-searchInputInput::placeholder {{
    color: var(--spice-subtext) !important;
}}
.xLC8OrWuExkkvVyzV00Y:hover .RYFwfQTMR9mVodv10kWY,
form[role="search"] input:hover {{
    background-color: var(--spice-highlight-elevated) !important;
}}
.xLC8OrWuExkkvVyzV00Y .RYFwfQTMR9mVodv10kWY:focus,
form[role="search"] input:focus {{
    background-color: var(--spice-card) !important;
    box-shadow: inset 0 0 0 2px var(--spice-button) !important;
}}
.xLC8OrWuExkkvVyzV00Y .dtqolIvjTNVaeTIrR7sK,
.x-searchInput-searchInputSearchIcon,
.x-searchInput-searchInputClearButton {{
    color: var(--spice-subtext) !important;
}}

/* Left Sidebar / Your Library */
.Root__nav-bar,
.main-navBar-navBar,
aside.main-yourLibraryX-libraryRoot,
div[data-testid="left-sidebar"] {{
    background-color: var(--spice-sidebar) !important;
}}

.main-yourLibraryX-entryPoints {{
    background-color: var(--spice-sidebar) !important;
}}

/* Right Sidebar (Now Playing View / Panels) */
.Root__right-sidebar,
.dMf_PkfPVTEuSmc11MZp,
aside[id="Desktop_PanelContainer_Id"],
aside.SwoI_U_X4O3wXD7db3su,
aside[aria-label="Now playing view"],
aside[aria-label="Панель текущего воспроизведения"] {{
    background-color: var(--spice-sidebar) !important;
    border-left: 1px solid var(--omarchy-border) !important;
}}

aside[id="Desktop_PanelContainer_Id"] header,
.NowPlayingView header,
.rtRw3GPEfgr_ZoUOJAYB {{
    color: var(--spice-text) !important;
}}

/* Right Sidebar Cards & Sections (Lyrics, Credits, Queue, Ads) */
.PtOV10BQebDwnZ7uk_dE,
.r17ERjd25OTZTkEkVPpg,
.vMBnf9gWft4BhCKeJTwr,
.sTXGYkJpnfniCRaltJXm,
.uX9xK6buuailuaeXHvy_,
.hMmF6IL0WDN29KL01IzB,
[data-testid="NPV_Panel_OpenDiv"] > div,
[data-testid="NPV_Panel_OpenDiv"] section,
.NowPlayingView section,
.NowPlayingView [data-section-background-base] {{
    background-color: var(--spice-card) !important;
    color: var(--spice-text) !important;
    border: 1px solid var(--omarchy-border) !important;
    border-radius: 8px !important;
}}

.NowPlayingView h1,
.NowPlayingView h2,
.NowPlayingView h3,
.NowPlayingView h4,
.NowPlayingView .encore-text-body-medium-bold,
.NowPlayingView .encore-text-headline-medium {{
    color: var(--spice-text) !important;
}}

.NowPlayingView p,
.NowPlayingView span,
.NowPlayingView .encore-internal-color-text-subdued {{
    color: var(--spice-subtext) !important;
}}

.NowPlayingView button[data-encore-id="buttonSecondary"],
.NowPlayingView .dcHHkPycs626KfCWyagg,
.NowPlayingView .t_B_W3ANI2Z6wniPRzD7 {{
    color: var(--spice-subtext) !important;
    border: 1px solid var(--omarchy-border) !important;
    background-color: transparent !important;
}}
.NowPlayingView button[data-encore-id="buttonSecondary"]:hover {{
    color: var(--spice-text) !important;
    border-color: var(--spice-text) !important;
}}

/* Filter Chips & Pills ("Fast", "Chill", "Rock", etc.) */
.e-101040-legacy-chip__inner,
.e-101040-chip,
[data-encore-id="chip"] {{
    background-color: var(--spice-card) !important;
    color: var(--spice-text) !important;
    border: 1px solid var(--omarchy-border) !important;
}}
.e-101040-legacy-chip:hover > .e-101040-legacy-chip__inner,
.e-101040-chip:hover,
[data-encore-id="chip"]:hover {{
    background-color: var(--spice-highlight-elevated) !important;
    color: var(--spice-text) !important;
}}
.e-101040-legacy-chip__inner--selected,
.e-101040-chip--selected,
[data-encore-id="chip"][aria-selected="true"] {{
    background-color: var(--spice-button) !important;
    color: #ffffff !important;
    border-color: var(--spice-button) !important;
}}

.sceEMSuUkZnHE6_PG5jl button,
button[aria-label="Scroll right"],
button[aria-label="Scroll left"],
button[aria-label="Прокрутить вправо"],
button[aria-label="Прокрутить влево"] {{
    background-color: var(--spice-card) !important;
    color: var(--spice-text) !important;
    border: 1px solid var(--omarchy-border) !important;
}}
.sceEMSuUkZnHE6_PG5jl button:hover,
button[aria-label="Scroll right"]:hover,
button[aria-label="Scroll left"]:hover {{
    background-color: var(--spice-highlight-elevated) !important;
}}

/* Playlist & Album Dynamic Header Gradient (Balanced contrast in light mode) */
.A0hGajCN2_Y1J_AjxSJh,
.rRzDzkFoPB1jsHaUjsDT,
div[data-seamless-gradient],
.main-entityHeader-background.main-entityHeader-gradient {{
    opacity: {header_opacity} !important;
}}

/* Bottom Playback Bar (Now Playing) */
.Root__now-playing-bar,
footer.main-nowPlayingBar-container,
div[data-testid="now-playing-bar"] {{
    background-color: var(--spice-player) !important;
    border-top: 1px solid var(--omarchy-border) !important;
}}

/* ==========================================================================
   Play / Pause Button (Bottom Player Bar)
   Synchronized dynamically with Omarchy themes:
   Circle background takes active theme accent;
   Icon inside matches Spotify player background color.
   ========================================================================== */
button[data-testid="control-button-playpause"],
button[data-testid="control-button-playpause"] > span,
button[data-testid="control-button-playpause"] [class*="button-primary__inner"],
button[data-testid="control-button-playpause"] [class*="ButtonInner"],
.main-playPauseButton-button {{
    background-color: var(--omarchy-accent) !important;
    --background-base: var(--omarchy-accent) !important;
    --background-highlight: var(--omarchy-accent-hover) !important;
    --background-press: var(--omarchy-accent-active) !important;
    border-radius: 50% !important;
    transition: transform 0.15s ease, background-color 0.15s ease !important;
}}

button[data-testid="control-button-playpause"]:hover,
button[data-testid="control-button-playpause"]:hover > span,
button[data-testid="control-button-playpause"]:hover [class*="button-primary__inner"],
button[data-testid="control-button-playpause"]:hover [class*="ButtonInner"],
.main-playPauseButton-button:hover {{
    background-color: var(--omarchy-accent-hover) !important;
}}

button[data-testid="control-button-playpause"]:hover,
.main-playPauseButton-button:hover {{
    transform: scale(1.06) !important;
}}

button[data-testid="control-button-playpause"]:active,
button[data-testid="control-button-playpause"]:active > span,
button[data-testid="control-button-playpause"]:active [class*="button-primary__inner"],
button[data-testid="control-button-playpause"]:active [class*="ButtonInner"],
.main-playPauseButton-button:active {{
    background-color: var(--omarchy-accent-active) !important;
    transform: scale(0.98) !important;
}}

/* Icon inside play/pause circle: EXACT MATCH with Spotify player background */
button[data-testid="control-button-playpause"] svg,
button[data-testid="control-button-playpause"] svg *,
button[data-testid="control-button-playpause"] [data-encore-id="icon"] svg,
button[data-testid="control-button-playpause"] [data-encore-id="icon"] svg *,
.main-playPauseButton-button svg,
.main-playPauseButton-button svg * {{
    fill: var(--spice-player) !important;
    color: var(--spice-player) !important;
    --text-base: var(--spice-player) !important;
    --essential-base: var(--spice-player) !important;
}}

/* Page Play Buttons (Playlists, Albums, Artists, Card hover) */
.main-playButton-PlayButton,
button[data-testid="play-button"],
.main-playButton-primary {{
    background-color: var(--spice-button) !important;
    --background-base: var(--spice-button) !important;
    --background-highlight: var(--spice-button-active) !important;
    border-radius: 50% !important;
    transition: transform 0.15s ease, background-color 0.15s ease !important;
}}

.main-playButton-PlayButton:hover,
button[data-testid="play-button"]:hover,
.main-playButton-primary:hover {{
    background-color: var(--spice-button-active) !important;
    transform: scale(1.05) !important;
}}

/* Icon inside page play buttons: matches Spotify main content background */
.main-playButton-PlayButton svg,
.main-playButton-PlayButton svg *,
button[data-testid="play-button"] svg,
button[data-testid="play-button"] svg *,
.main-playButton-primary svg,
.main-playButton-primary svg * {{
    fill: var(--spice-main) !important;
    color: var(--spice-main) !important;
    --text-base: var(--spice-main) !important;
    --essential-base: var(--spice-main) !important;
}}

/* ==========================================================================
   Player Control Buttons (Shuffle, Skip Back/Forward, Repeat, Right Bar)
   High contrast, clearly visible on all themes, vivid active states.
   ========================================================================== */

/* 1. Inactive / default state: high contrast, no dark blending */
div[data-testid="player-controls"] button:not([data-testid="control-button-playpause"]),
.player-controls__buttons button:not([data-testid="control-button-playpause"]),
.main-nowPlayingBar-right button,
.main-nowPlayingBar-left button:not(.main-addButton-button) {{
    color: {control_btn_fg} !important;
    opacity: 0.85 !important;
    transition: color 0.15s ease, opacity 0.15s ease, transform 0.15s ease !important;
}}

div[data-testid="player-controls"] button:not([data-testid="control-button-playpause"]) svg,
.player-controls__buttons button:not([data-testid="control-button-playpause"]) svg,
.main-nowPlayingBar-right button svg,
.main-nowPlayingBar-left button:not(.main-addButton-button) svg {{
    fill: currentColor !important;
    color: currentColor !important;
}}

/* 2. Hover state: bright, 100% opacity, subtle scale */
div[data-testid="player-controls"] button:not([data-testid="control-button-playpause"]):hover:not(:disabled),
.player-controls__buttons button:not([data-testid="control-button-playpause"]):hover:not(:disabled),
.main-nowPlayingBar-right button:hover:not(:disabled),
.main-nowPlayingBar-left button:not(.main-addButton-button):hover:not(:disabled) {{
    color: {control_btn_hover_fg} !important;
    opacity: 1.0 !important;
    transform: scale(1.08) !important;
}}

/* 3. Active / toggled buttons (Shuffle ON, Repeat ON, Repeat Track, Lyrics, Queue, etc.) */
button[data-testid="control-button-shuffle"][aria-checked="true"],
button[data-testid="control-button-repeat"][aria-checked="true"],
button[data-testid="control-button-repeat"][aria-checked="mixed"],
button[data-testid="lyrics-button"][aria-expanded="true"],
button[data-testid="control-button-npv"][aria-expanded="true"],
button[data-testid="control-button-queue"][aria-expanded="true"],
.main-nowPlayingBar-right button[aria-expanded="true"],
button[data-testid="add-button"][aria-checked="true"],
button.main-addButton-button[aria-checked="true"],
button.main-addButton-active {{
    color: var(--omarchy-accent) !important;
    opacity: 1.0 !important;
}}

button[data-testid="control-button-shuffle"][aria-checked="true"]:hover,
button[data-testid="control-button-repeat"][aria-checked="true"]:hover,
button[data-testid="control-button-repeat"][aria-checked="mixed"]:hover,
button[data-testid="lyrics-button"][aria-expanded="true"]:hover,
button[data-testid="control-button-npv"][aria-expanded="true"]:hover,
button[data-testid="control-button-queue"][aria-expanded="true"]:hover,
.main-nowPlayingBar-right button[aria-expanded="true"]:hover,
button[data-testid="add-button"][aria-checked="true"]:hover {{
    color: var(--omarchy-accent-hover) !important;
    opacity: 1.0 !important;
    transform: scale(1.08) !important;
}}

/* Active dot indicator under Shuffle & Repeat buttons */
.KIr7xb8M8kwrXLA0Myzy:before,
.GRt7501sdglGEjReOsjn:before,
button[data-testid="control-button-shuffle"][aria-checked="true"]::after,
button[data-testid="control-button-repeat"][aria-checked="true"]::after,
button[data-testid="control-button-repeat"][aria-checked="mixed"]::after {{
    background-color: var(--omarchy-accent) !important;
}}

/* 4. Disabled buttons (e.g. Prev at first track) */
div[data-testid="player-controls"] button:disabled,
.player-controls__buttons button:disabled,
.main-nowPlayingBar-right button:disabled {{
    opacity: 0.28 !important;
    color: var(--omarchy-muted) !important;
    cursor: not-allowed !important;
    transform: none !important;
}}

/* 5. Timestamps */
.playback-bar__progress-time,
div[data-testid="playback-position"],
div[data-testid="playback-duration"] {{
    color: {control_btn_fg} !important;
    font-size: 0.75rem !important;
    opacity: 0.85 !important;
}}

/* ==========================================================================
   PROGRESS BAR & VOLUME SLIDERS (CLEAN, HIGH CONTRAST, NO THUMB HANDLE)
   ========================================================================== */

/* 1. The unplayed / empty background track */
.x-progressBar-progressBarBg,
div[data-testid="progress-bar-background"] {{
    background-color: {track_bg} !important;
    border-radius: 4px !important;
    height: 4px !important;
    top: 50% !important;
    transform: translateY(-50%) !important;
    transition: background-color 0.2s ease;
}}

.playback-progressbar:hover .x-progressBar-progressBarBg,
.playback-progressbar-isInteractive:hover .x-progressBar-progressBarBg,
div[data-testid="volume-bar"]:hover .x-progressBar-progressBarBg {{
    background-color: {track_hover_bg} !important;
}}

/* 2. The active / played progress fill */
.x-progressBar-fillColor,
.x-progressBar-progressFillColor {{
    background-color: var(--omarchy-accent) !important;
    border-radius: 4px !important;
    height: 100% !important;
    transition: background-color 0.2s ease;
}}

.playback-progressbar:hover .x-progressBar-fillColor,
.playback-progressbar-isInteractive:hover .x-progressBar-fillColor,
div[data-testid="volume-bar"]:hover .x-progressBar-fillColor {{
    background-color: var(--omarchy-accent-hover) !important;
}}

/* 3. Slider Thumb Handle: PERMANENTLY REMOVED / HIDDEN */
.progress-bar__slider,
div[data-testid="progress-bar-handle"],
.playback-progressbar .progress-bar__slider,
.playback-progressbar-isInteractive .progress-bar__slider,
div[data-testid="volume-bar"] .progress-bar__slider,
div[data-testid="progress-bar"] .progress-bar__slider,
.playback-progressbar:hover .progress-bar__slider,
.playback-progressbar-isInteractive:hover .progress-bar__slider,
.playback-progressbar-isInteractive:focus-within .progress-bar__slider,
.progress-bar:hover .progress-bar__slider,
div[data-testid="volume-bar"]:hover .progress-bar__slider,
div[data-testid="volume-bar"]:focus-within .progress-bar__slider,
div[data-testid="progress-bar"]:hover .progress-bar__slider,
div[data-testid="progress-bar"]:focus-within .progress-bar__slider {{
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    width: 0 !important;
    height: 0 !important;
    pointer-events: none !important;
}}

/* Tracklist Rows */
.main-trackList-trackListRow {{
    border-radius: 6px;
    transition: background-color 0.15s ease;
}}
.main-trackList-trackListRow:hover {{
    background-color: {hover_row} !important;
}}
.main-trackList-trackListRow.main-trackList-selected,
.main-trackList-trackListRow.main-trackList-selected:hover {{
    background-color: {selected_row} !important;
}}
.main-trackList-trackListRow.main-trackList-active .main-trackList-rowTitle {{
    color: var(--spice-button) !important;
}}

/* Cards & Grid Items */
.main-card-card {{
    background-color: var(--spice-card) !important;
    border-radius: 8px !important;
    border: 1px solid var(--omarchy-border) !important;
    transition: background-color 0.2s ease, transform 0.2s ease;
}}
.main-card-card:hover {{
    background-color: var(--spice-main-secondary) !important;
}}

/* Checkboxes, Switches & Heart/Check Icons (Adapt to Theme) */
input[type="checkbox"]:checked,
.x-toggle-indicator[data-checked="true"] {{
    background-color: var(--spice-button) !important;
}}
button.main-addButton-button[aria-checked="true"],
button.main-addButton-active,
button[aria-checked="true"] svg,
svg.main-trackList-rowHeartButton[aria-checked="true"] {{
    color: var(--spice-button) !important;
    fill: var(--spice-button) !important;
}}

/* Context Menus & Popups */
div[data-tippy-root] ul,
.main-contextMenu-menu {{
    background-color: var(--spice-sidebar) !important;
    border: 1px solid var(--omarchy-border) !important;
    border-radius: 8px !important;
    box-shadow: 0 10px 28px rgba(0, 0, 0, 0.45) !important;
}}
.main-contextMenu-menuItemButton:hover {{
    background-color: var(--spice-card) !important;
    color: var(--spice-text) !important;
}}

/* Search Input */
.x-searchInput-searchInputInput {{
    background-color: var(--spice-card) !important;
    color: var(--spice-text) !important;
    border: 1px solid var(--omarchy-border) !important;
    border-radius: 20px !important;
}}
.x-searchInput-searchInputInput::placeholder {{
    color: var(--spice-subtext) !important;
}}

/* Custom Scrollbars */
.os-scrollbar-handle {{
    background: rgba(255, 255, 255, 0.18) !important;
    border-radius: 6px !important;
}}
.os-scrollbar-handle:hover {{
    background: var(--spice-button) !important;
}}
"""
    return css


def ensure_spicetify_config(home: Path) -> None:
    """Ensures config-xpui.ini has omarchy theme and omarchy-sync.js extension."""
    config_file = home / ".config" / "spicetify" / "config-xpui.ini"
    if not config_file.is_file():
        return

    config = configparser.ConfigParser()
    config.read(config_file, encoding="utf-8")

    changed = False
    if "Setting" in config:
        if config["Setting"].get("current_theme") != "omarchy":
            config["Setting"]["current_theme"] = "omarchy"
            changed = True
        if config["Setting"].get("color_scheme") != "Omarchy":
            config["Setting"]["color_scheme"] = "Omarchy"
            changed = True
        if config["Setting"].get("inject_css") != "1":
            config["Setting"]["inject_css"] = "1"
            changed = True
        if config["Setting"].get("replace_colors") != "1":
            config["Setting"]["replace_colors"] = "1"
            changed = True

    if "AdditionalOptions" in config:
        exts = [e.strip() for e in config["AdditionalOptions"].get("extensions", "").split("|") if e.strip()]
        if "omarchy-sync.js" not in exts:
            exts.append("omarchy-sync.js")
            config["AdditionalOptions"]["extensions"] = "|".join(exts)
            changed = True

    if changed:
        with open(config_file, "w", encoding="utf-8") as f:
            config.write(f)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Omarchy Spotify Theme")
    parser.add_argument("--theme-name", help="Omarchy theme name", default=None)
    parser.add_argument("--colors-file", help="Path to colors.toml", default=None)
    parser.add_argument("--no-apply", action="store_true", help="Do not run spicetify apply")
    args = parser.parse_args()

    home = Path.home()
    if args.colors_file:
        colors_path = Path(args.colors_file)
    else:
        colors_path = home / ".local" / "state" / "omarchy" / "current" / "theme" / "colors.toml"

    if args.theme_name:
        theme_name = args.theme_name
    else:
        name_file = home / ".local" / "state" / "omarchy" / "current" / "theme.name"
        if name_file.is_file():
            theme_name = name_file.read_text(encoding="utf-8").strip()
        else:
            theme_name = "Omarchy"

    try:
        palette = load_palette(colors_path)
    except Exception as e:
        print(f"Error loading palette from {colors_path}: {e}", file=sys.stderr)
        return 1

    theme_dir = home / ".config" / "spicetify" / "Themes" / "omarchy"
    theme_dir.mkdir(parents=True, exist_ok=True)

    color_ini_content = build_color_ini(palette, theme_name)
    user_css_content = build_user_css(palette, theme_name)

    (theme_dir / "color.ini").write_text(color_ini_content, encoding="utf-8")
    (theme_dir / "user.css").write_text(user_css_content, encoding="utf-8")

    print(f"Wrote theme files to {theme_dir}")

    ensure_spicetify_config(home)

    if not args.no_apply:
        spicetify_bin = home / ".spicetify" / "spicetify"
        if not spicetify_bin.is_file():
            spicetify_bin = Path("spicetify")

        cmd = [str(spicetify_bin), "apply", "-n"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"Successfully applied Spotify Omarchy theme '{theme_name}'")
        else:
            print(f"Warning: 'spicetify apply' exited with code {res.returncode}:\n{res.stderr}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
