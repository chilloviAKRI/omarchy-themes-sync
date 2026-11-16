#!/usr/bin/env python3
"""
Omarchy Discord / Vencord Theme Generator.

Reads Omarchy's current palette from ~/.local/state/omarchy/current/theme/colors.toml
and generates a comprehensive Discord theme for Vencord and Vesktop.
Synchronizes live whenever Omarchy switches theme.

Selection color is frozen to macOS blue (#0063e6) per user requirement.
Checkmarks, switches, badges, backgrounds, sidebars, text, inputs, buttons
and all other UI elements dynamically adapt to Omarchy's active theme.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore


# macOS blue text selection (mandatory per user request)
MACOS_SELECTION_BG = "#0063e6"
MACOS_SELECTION_FG = "#ffffff"


def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    s = hex_str.strip().lstrip("#")
    if len(s) == 3:
        s = "".join([c * 2 for c in s])
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


def rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{max(0, min(255, int(r))):02x}{max(0, min(255, int(g))):02x}{max(0, min(255, int(b))):02x}"


def rgba(hex_str: str, alpha: float) -> str:
    r, g, b = hex_to_rgb(hex_str)
    return f"rgba({r}, {g}, {b}, {alpha:.2f})"


def adjust_lightness(hex_str: str, factor: float) -> str:
    """Lightens (factor > 0) or darkens (factor < 0) a hex color (-1.0 to +1.0)."""
    r, g, b = hex_to_rgb(hex_str)
    if factor >= 0:
        r = r + (255 - r) * factor
        g = g + (255 - g) * factor
        b = b + (255 - b) * factor
    else:
        multiplier = 1.0 + factor
        r = r * multiplier
        g = g * multiplier
        b = b * multiplier
    return rgb_to_hex(round(r), round(g), round(b))


def mix(hex1: str, hex2: str, weight: float = 0.5) -> str:
    """Mixes two colors. weight=1.0 is 100% hex1, weight=0.0 is 100% hex2."""
    r1, g1, b1 = hex_to_rgb(hex1)
    r2, g2, b2 = hex_to_rgb(hex2)
    r = r1 * weight + r2 * (1.0 - weight)
    g = g1 * weight + g2 * (1.0 - weight)
    b = b1 * weight + b2 * (1.0 - weight)
    return rgb_to_hex(round(r), round(g), round(b))


def load_palette(colors_path: Path) -> dict[str, str]:
    if not colors_path.is_file():
        raise FileNotFoundError(f"Colors file not found: {colors_path}")
    with open(colors_path, "rb") as f:
        data = tomllib.load(f)

    # Defaults for safety
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
        "orange": data.get("orange", "#d5967a"),
        "green": data.get("green", "#a3be8c"),
        "cyan": data.get("cyan", "#88c0d0"),
        "blue": data.get("blue", "#81a1c1"),
        "magenta": data.get("magenta", "#b48ead"),
    }
    return palette


def build_css(palette: dict[str, str], theme_name: str) -> str:
    is_dark = palette["mode"] != "light"

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

    red = palette["red"]
    green = palette["green"]
    yellow = palette["yellow"]
    blue = palette["blue"]
    cyan = palette["cyan"]
    magenta = palette["magenta"]

    accent_hover = adjust_lightness(accent, 0.12 if is_dark else -0.10)
    accent_active = adjust_lightness(accent, -0.15 if is_dark else -0.20)
    accent_contrast_fg = "#ffffff" if is_dark else "#191c23"

    border_color = rgba("#ffffff" if is_dark else "#000000", 0.08)
    border_strong = rgba("#ffffff" if is_dark else "#000000", 0.15)
    border_subtle = rgba("#ffffff" if is_dark else "#000000", 0.05)

    hover_bg = rgba("#ffffff" if is_dark else "#000000", 0.05)
    active_bg = rgba("#ffffff" if is_dark else "#000000", 0.10)
    selected_bg = rgba(accent, 0.18)

    mention_bg = rgba(accent, 0.15)
    mention_hover = rgba(accent, 0.22)

    # Brand tint ladder
    brand_shades = {}
    for i in range(1, 10):
        factor = (5 - i) * 0.10
        brand_shades[f"brand-{i * 100}"] = adjust_lightness(accent, factor)

    css = f"""/**
 * @name Omarchy
 * @author Omarchy
 * @version 1.0.0
 * @description Omarchy live synchronized theme: {theme_name} ({palette['mode']})
 * @source https://github.com/omarchy
 */

/* ==========================================================================
   Omarchy Theme Variables & Palette Tokens
   ========================================================================== */
:root,
html,
body,
.theme-dark,
.theme-light,
.visual-refresh,
.visual-refresh.theme-dark,
.visual-refresh.theme-light {{
    --omarchy-theme: "{theme_name}";
    --omarchy-mode: "{palette['mode']}";

    /* Base Palette */
    --omarchy-bg: {bg};
    --omarchy-dark-bg: {dark_bg};
    --omarchy-darker-bg: {darker_bg};
    --omarchy-lighter-bg: {lighter_bg};

    --omarchy-fg: {fg};
    --omarchy-bright-fg: {bright_fg};
    --omarchy-light-fg: {light_fg};
    --omarchy-dark-fg: {dark_fg};
    --omarchy-muted: {muted};

    --omarchy-accent: {accent};
    --omarchy-accent-hover: {accent_hover};
    --omarchy-accent-active: {accent_active};
    --omarchy-accent-contrast: {accent_contrast_fg};

    --omarchy-red: {red};
    --omarchy-green: {green};
    --omarchy-yellow: {yellow};
    --omarchy-blue: {blue};
    --omarchy-cyan: {cyan};
    --omarchy-magenta: {magenta};

    --omarchy-border: {border_color};
    --omarchy-border-strong: {border_strong};
    --omarchy-border-subtle: {border_subtle};

    --omarchy-hover-bg: {hover_bg};
    --omarchy-active-bg: {active_bg};
    --omarchy-selected-bg: {selected_bg};

    /* Brand Scale */
    --brand-experiment: {accent};
    --brand-experiment-hover: {accent_hover};
    --brand-experiment-active: {accent_active};
    --brand-500: {accent} !important;
    --brand-530: {accent_hover};
    --brand-560: {accent_active};
    --brand-600: {accent_active};
    --brand-260: {accent};
    --brand-360: {accent};
    --brand-400: {accent};
    --brand-100: {brand_shades['brand-100']};
    --brand-200: {brand_shades['brand-200']};
    --brand-300: {brand_shades['brand-300']};
    --brand-700: {brand_shades['brand-700']};
    --brand-800: {brand_shades['brand-800']};
    --brand-900: {brand_shades['brand-900']};

    --accent-color: {accent} !important;
    --blurple-50: {accent} !important;
    --blurple-60: {accent_active} !important;

    /* Backgrounds: Classic Discord Tokens */
    --background-primary: {bg} !important;
    --background-secondary: {dark_bg} !important;
    --background-secondary-alt: {dark_bg} !important;
    --background-tertiary: {darker_bg} !important;
    --background-accent: {lighter_bg} !important;
    --background-floating: {darker_bg} !important;
    --background-mobile-primary: {bg} !important;
    --background-mobile-secondary: {dark_bg} !important;
    --channeltextarea-background: {dark_bg} !important;
    --app-frame-background: {darker_bg} !important;
    --modal-background: {bg} !important;
    --modal-footer-background: {dark_bg} !important;

    /* Backgrounds: Visual Refresh & Redesign Tokens */
    --bg-base-primary: {bg} !important;
    --bg-base-secondary: {dark_bg} !important;
    --bg-base-tertiary: {darker_bg} !important;
    --background-base-lowest: {darker_bg} !important;
    --background-base-lower: {darker_bg} !important;
    --background-base-low: {dark_bg} !important;
    --background-surface-high: {dark_bg} !important;
    --background-surface-higher: {lighter_bg} !important;
    --background-surface-highest: {lighter_bg} !important;
    --bg-surface-raised: {dark_bg} !important;
    --bg-surface-overlay: {darker_bg} !important;
    --chat-background: {bg} !important;
    --chat-background-default: {bg} !important;
    --chat-border: {border_color} !important;
    --home-background: {bg} !important;
    --card-background-default: {dark_bg} !important;

    /* Text & Headers */
    --text-normal: {fg} !important;
    --text-default: {fg} !important;
    --text-muted: {muted} !important;
    --text-subtle: {light_fg} !important;
    --text-strong: {bright_fg} !important;
    --header-primary: {bright_fg} !important;
    --header-secondary: {light_fg} !important;
    --text-link: {accent} !important;
    --text-brand: {accent} !important;
    --channels-default: {light_fg} !important;
    --channel-icon: {dark_fg} !important;
    --channel-text-area-placeholder: {muted} !important;
    --chat-text-muted: {muted} !important;

    /* Interactive & Hover */
    --interactive-normal: {light_fg} !important;
    --interactive-hover: {bright_fg} !important;
    --interactive-active: {bright_fg} !important;
    --interactive-muted: {muted} !important;
    --interactive-background-hover: {hover_bg} !important;
    --interactive-background-selected: {selected_bg} !important;
    --interactive-background-active: {active_bg} !important;

    /* Messages & Mentions */
    --message-background-hover: {hover_bg} !important;
    --message-highlight-background-default: {rgba(accent, 0.08)} !important;
    --message-highlight-background-hover: {rgba(accent, 0.12)} !important;
    --message-mentioned-background-default: {mention_bg} !important;
    --message-mentioned-background-hover: {mention_hover} !important;
    --mention-foreground: {accent} !important;
    --mention-background: {rgba(accent, 0.20)} !important;
    --message-reacted-background-default: {rgba(accent, 0.20)} !important;
    --message-reacted-text-default: {accent} !important;

    /* Controls, Buttons & Inputs */
    --control-primary-background-default: {accent} !important;
    --control-primary-background-hover: {accent_hover} !important;
    --control-primary-background-active: {accent_active} !important;
    --control-primary-text-default: {accent_contrast_fg} !important;
    --control-primary-text-hover: {accent_contrast_fg} !important;
    --control-secondary-background-default: {lighter_bg} !important;
    --control-secondary-background-hover: {hover_bg} !important;
    --control-secondary-text-default: {fg} !important;
    --control-brand-foreground: {accent} !important;
    --control-brand-foreground-new: {accent} !important;

    --input-background-default: {dark_bg} !important;
    --input-text-default: {fg} !important;
    --input-placeholder-text-default: {muted} !important;
    --input-border-default: {border_color} !important;
    --input-border-hover: {accent} !important;
    --input-border-active: {accent} !important;

    /* Badges & Unread */
    --badge-notification-background: {accent} !important;
    --background-feedback-notification: {accent} !important;
    --badge-background-default: {accent} !important;
    --badge-text-default: {accent_contrast_fg} !important;
    --badge-text-brand: {accent_contrast_fg} !important;

    /* Status Indicators */
    --status-positive: {green} !important;
    --status-positive-background: {green} !important;
    --status-positive-text: #ffffff !important;
    --status-online: {green} !important;
    --icon-status-online: {green} !important;
    --text-status-online: {green} !important;

    --status-warning: {yellow} !important;
    --status-warning-background: {yellow} !important;
    --status-warning-text: #ffffff !important;
    --icon-status-idle: {yellow} !important;
    --text-status-idle: {yellow} !important;

    --status-danger: {red} !important;
    --icon-status-dnd: {red} !important;
    --text-status-dnd: {red} !important;

    --icon-status-offline: {muted} !important;
    --text-status-offline: {muted} !important;

    /* Feedback Colors */
    --text-feedback-positive: {green} !important;
    --icon-feedback-positive: {green} !important;
    --text-feedback-warning: {yellow} !important;
    --icon-feedback-warning: {yellow} !important;
    --text-feedback-critical: {red} !important;
    --icon-feedback-critical: {red} !important;
    --text-feedback-info: {cyan} !important;
    --icon-feedback-info: {cyan} !important;

    /* Borders & Dividers */
    --border-subtle: {border_subtle} !important;
    --border-normal: {border_color} !important;
    --border-strong: {border_strong} !important;
    --border-muted: {border_subtle} !important;

    /* Checkboxes, Switches & Radio */
    --checkbox-background-default: {dark_bg} !important;
    --checkbox-background-selected-default: {accent} !important;
    --checkbox-background-selected-hover: {accent_hover} !important;
    --checkbox-border-selected-default: {accent} !important;
    --checkbox-border-default: {border_color} !important;
    --checkbox-icon-active: {accent_contrast_fg} !important;

    --switch-background-default: {lighter_bg} !important;
    --switch-background-selected-default: {accent} !important;
    --switch-background-selected-hover: {accent_hover} !important;

    --radio-background-selected-default: {accent} !important;
    --radio-background-selected-hover: {accent_hover} !important;
    --radio-thumb-background-active: {accent_contrast_fg} !important;

    --progressbar-indicator-background: {accent} !important;
    --progressbar-track-background: {dark_bg} !important;

    /* Scrollbars */
    --scrollbar-thin-thumb: {rgba(accent, 0.40)} !important;
    --scrollbar-thin-track: transparent !important;
    --scrollbar-auto-thumb: {rgba(accent, 0.40)} !important;
    --scrollbar-auto-track: transparent !important;
    --scrollbar-auto-scrollbar-color-thumb: {rgba(accent, 0.40)} !important;
    --scrollbar-auto-scrollbar-color-track: transparent !important;

    /* Profile Overlays */
    --user-profile-overlay-background: {dark_bg} !important;
    --user-profile-overlay-background-hover: {lighter_bg} !important;
}}

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
textarea::selection,
[contenteditable]::selection {{
    background-color: {MACOS_SELECTION_BG} !important;
    color: {MACOS_SELECTION_FG} !important;
}}

/* ==========================================================================
   Structural Layout Overrides
   ========================================================================== */

/* Guilds (Servers) sidebar */
nav[class*="guilds_"],
div[class*="guilds_"],
ul[class*="tree_"] {{
    background-color: var(--omarchy-darker-bg) !important;
}}

/* Channels sidebar & Voice panel */
div[class*="sidebar_"],
nav[class*="sidebar_"],
div[class*="container_"] > div[class*="sidebar_"] {{
    background-color: var(--omarchy-dark-bg) !important;
}}

/* User Status Panel at bottom of channels */
section[class*="panels_"] {{
    background-color: var(--omarchy-darker-bg) !important;
    border-top: 1px solid var(--omarchy-border) !important;
}}

/* Chat Main Area */
div[class*="chat_"],
main[class*="chatContent_"],
div[class*="messagesWrapper_"] {{
    background-color: var(--omarchy-bg) !important;
}}

/* Chat Header / Titlebar */
section[class*="title_"],
div[class*="subtitleContainer_"],
header[class*="header_"] {{
    background-color: var(--omarchy-bg) !important;
    border-bottom: 1px solid var(--omarchy-border) !important;
}}

/* Members List */
aside[class*="membersWrap_"],
div[class*="members_"] {{
    background-color: var(--omarchy-dark-bg) !important;
}}

/* Chat Text Area (Input Bar) */
div[class*="channelTextArea_"],
div[class*="scrollableContainer_"] {{
    background-color: var(--omarchy-dark-bg) !important;
    border: 1px solid var(--omarchy-border) !important;
    border-radius: 8px !important;
}}

/* Active & Selected Channel Items */
div[class*="modeSelected_"] div[class*="link_"],
div[class*="modeSelected_"] a[class*="link_"] {{
    background-color: var(--omarchy-selected-bg) !important;
}}
div[class*="modeSelected_"] div[class*="link_"] svg,
div[class*="modeSelected_"] div[class*="link_"] span {{
    color: var(--omarchy-bright-fg) !important;
}}

/* Channel Item Hover */
div[class*="wrapper_"]:hover div[class*="link_"] {{
    background-color: var(--omarchy-hover-bg) !important;
}}

/* Unread Pills & Number Badges */
span[class*="unreadPill_"] {{
    background-color: var(--omarchy-accent) !important;
}}
div[class*="numberBadge_"] {{
    background-color: var(--omarchy-accent) !important;
    color: {accent_contrast_fg} !important;
}}

/* Checkboxes, Switches & Radios (Adapt to Theme) */
div[data-mana-component="switch"]:has(input:checked),
div[class*="switch_"][class*="checked_"] {{
    background-color: var(--omarchy-accent) !important;
}}
div[class*="checkbox_"][class*="checked_"] {{
    background-color: var(--omarchy-accent) !important;
    border-color: var(--omarchy-accent) !important;
}}
div[class*="checkbox_"][class*="checked_"] svg path {{
    fill: {accent_contrast_fg} !important;
}}

/* Vencord Specific Elements */
div.vc-switch-container {{
    --primary-400: var(--omarchy-lighter-bg) !important;
}}
div.vc-switch-container:has(input:checked) {{
    background-color: var(--omarchy-accent) !important;
}}
div.vc-settings-tab-bar {{
    border-right: 1px solid var(--omarchy-border) !important;
}}
div.vc-addon-card {{
    background-color: var(--omarchy-dark-bg) !important;
    border: 1px solid var(--omarchy-border) !important;
}}

/* Code Blocks & Inline Pre */
pre, code {{
    font-family: monospace;
}}
code.inline {{
    background-color: var(--omarchy-darker-bg) !important;
    color: var(--omarchy-bright-fg) !important;
    border-radius: 4px;
}}
pre code {{
    background-color: var(--omarchy-darker-bg) !important;
    border: 1px solid var(--omarchy-border) !important;
}}

/* Modals & Popouts */
div[class*="modal_"],
div[class*="root_"][class*="small_"],
div[class*="root_"][class*="medium_"],
div[class*="root_"][class*="large_"] {{
    background-color: var(--omarchy-bg) !important;
    border: 1px solid var(--omarchy-border-strong) !important;
}}
div[class*="footer_"] {{
    background-color: var(--omarchy-dark-bg) !important;
}}

/* Context Menus */
div[id*="menu-"],
div[role="menu"] {{
    background-color: var(--omarchy-darker-bg) !important;
    border: 1px solid var(--omarchy-border) !important;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35) !important;
}}
div[role="menuitem"]:hover,
div[role="menuitem"][class*="focused_"] {{
    background-color: var(--omarchy-selected-bg) !important;
    color: var(--omarchy-bright-fg) !important;
}}
"""
    return css


def update_vencord_settings(settings_file: Path) -> bool:
    """Ensures omarchy.theme.css is enabled in Vencord's settings.json."""
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    theme_name = "omarchy.theme.css"

    data = {
        "notifyAboutUpdates": True,
        "autoUpdate": True,
        "autoUpdateNotification": True,
        "useQuickCss": True,
        "themeLinks": [],
        "enabledThemes": [theme_name],
        "enableReactDevtools": False,
        "frameless": False,
        "transparent": False,
        "plugins": {},
    }

    if settings_file.is_file():
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                existing = json.load(f)
            if isinstance(existing, dict):
                data = existing
                data["useQuickCss"] = True
                enabled = data.get("enabledThemes", [])
                if not isinstance(enabled, list):
                    enabled = []
                if theme_name not in enabled:
                    enabled.append(theme_name)
                data["enabledThemes"] = enabled
        except Exception as e:
            print(f"Warning: could not read existing settings {settings_file}: {e}")

    try:
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving settings {settings_file}: {e}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Omarchy Discord Theme")
    parser.add_argument("--theme-name", help="Omarchy theme name", default=None)
    parser.add_argument("--colors-file", help="Path to colors.toml", default=None)
    parser.add_argument("--pulse", action="store_true", help="Pulse write to trigger reload")
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

    css = build_css(palette, theme_name)
    if args.pulse:
        css += f"\n/* Pulse refresh: {os.getpid()} */\n"

    # Targets to write
    theme_targets = [
        home / ".config" / "Vencord" / "themes" / "omarchy.theme.css",
        home / ".config" / "Vencord" / "settings" / "quickCss.css",
    ]

    vesktop_dir = home / ".config" / "vesktop"
    if vesktop_dir.is_dir():
        theme_targets.extend([
            vesktop_dir / "themes" / "omarchy.theme.css",
            vesktop_dir / "settings" / "quickCss.css",
        ])

    written = 0
    for target in theme_targets:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                f.write(css)
            written += 1
        except Exception as e:
            print(f"Error writing theme to {target}: {e}", file=sys.stderr)

    # Update settings
    settings_targets = [
        home / ".config" / "Vencord" / "settings" / "settings.json",
    ]
    if vesktop_dir.is_dir():
        settings_targets.append(vesktop_dir / "settings" / "settings.json")

    for s_file in settings_targets:
        update_vencord_settings(s_file)

    print(f"Successfully generated Discord Omarchy theme '{theme_name}' -> {written} files updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
