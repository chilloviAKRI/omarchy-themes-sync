#!/usr/bin/env python3
"""
Omarchy -> Telegram Desktop / AyuGram Desktop theme generator.

Reads the active Omarchy palette and writes a .tdesktop-theme file (a zip
holding colors.tdesktop-theme). AyuGram/Telegram watches that file with
QFileSystemWatcher and re-applies it live, so rewriting the file on every
`omarchy theme set` keeps the messenger in sync with the desktop.

The whole trick is that a subset of palette keys is FROZEN: online badges,
message/chat selection, ticks and checkboxes keep the stock Telegram values
(resolved to concrete hex) instead of being tinted with Omarchy colors. On
some Omarchy themes those indicators would otherwise blend into the
background and become invisible.

The frozen key list lives in frozen.txt next to this script - edit it to
add/remove keys. Missing file -> the default list is regenerated.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import re
import subprocess
import sys
import tomllib
import zipfile
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_DIR = HERE / "base"
FROZEN_FILE = HERE / "frozen.txt"
DEFAULT_OUT = HERE / "omarchy.tdesktop-theme"
STATE = Path.home() / ".local/state/omarchy/current/theme"

LINE_RE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9_]*)\s*:\s*([^;]+?)\s*;")
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$")

# ---------------------------------------------------------------------------
# Frozen keys: ONLY text selection is kept blue.
# All other indicators (badges, online dots, checkmarks) adapt to Omarchy.
# ---------------------------------------------------------------------------

FROZEN_MARKERS = (
    "selected", "select", "selcolor",
)
FROZEN_EXACT: set[str] = set()


def default_frozen(keys: set[str]) -> list[str]:
    result = set()
    for key in keys:
        low = key.lower()
        if any(marker in low for marker in FROZEN_MARKERS):
            result.add(key)
        elif key in FROZEN_EXACT:
            result.add(key)
    return sorted(result)


def load_frozen(keys: set[str]) -> tuple[set[str], bool]:
    if FROZEN_FILE.exists():
        wanted = {
            line.strip() for line in FROZEN_FILE.read_text().splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        return (wanted & keys), False
    frozen = default_frozen(keys)
    FROZEN_FILE.write_text(
        "# Telegram palette keys that are NEVER tinted with Omarchy colors.\n"
        "# One key per line; '#' starts a comment. Delete this file to\n"
        "# regenerate the default list.\n"
        + "\n".join(frozen) + "\n"
    )
    return set(frozen), True


# ---------------------------------------------------------------------------
# Base palette parsing / reference resolving
# ---------------------------------------------------------------------------

def parse_palette(text: str) -> dict[str, str]:
    """key -> raw value ('#rrggbb', '#rrggbbaa', or another key name)."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        m = LINE_RE.match(line)
        if not m:
            continue
        key, value = m.group(1), m.group(2).strip()
        if key in out:
            raise ValueError(f"duplicate palette key: {key}")
        out[key] = value
    if "windowBg" not in out:
        raise ValueError("base palette has no windowBg - is it a real Telegram palette?")
    return out


def resolve_all(raw: dict[str, str]) -> dict[str, str]:
    """Resolve every alias to a concrete hex, using the ORIGINAL base values."""
    resolved: dict[str, str] = {}

    def resolve(key: str, stack: tuple[str, ...]) -> str:
        if key in resolved:
            return resolved[key]
        if key in stack:
            raise ValueError(f"cyclic palette reference: {' -> '.join((*stack, key))}")
        value = raw[key]
        if value.startswith("#"):
            if not HEX_RE.match(value):
                raise ValueError(f"bad hex for {key}: {value}")
            result = value.lower()
        elif value in raw:
            result = resolve(value, (*stack, key))
        else:
            # Unknown alias (e.g. a key defined only in the app binary).
            # Keeping the raw value is safe: the app resolves it itself.
            result = value
        resolved[key] = result
        return result

    for key in raw:
        resolve(key, ())
    return resolved


# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------

def norm_hex(value: str) -> str:
    value = value.strip()
    if not value.startswith("#"):
        value = "#" + value
    value = value.lower()
    if not HEX_RE.match(value):
        raise ValueError(f"not a hex color: {value}")
    return value[:7]  # drop alpha, we add our own where needed


def lum(hex_color: str) -> float:
    h = norm_hex(hex_color)
    channels = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a: str, b: str) -> float:
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def text_on(bg: str, *candidates: str) -> str:
    """Pick the most readable text color for a background."""
    return max(dict.fromkeys(candidates), key=lambda c: contrast(c, bg))


def mix(a: str, b: str, amount: float) -> str:
    """Blend a -> b, amount is the share of b (0..1)."""
    a, b = norm_hex(a), norm_hex(b)
    amount = max(0.0, min(1.0, amount))
    out = []
    for i in (1, 3, 5):
        x, y = int(a[i:i + 2], 16), int(b[i:i + 2], 16)
        out.append(f"{round(x * (1 - amount) + y * amount):02x}")
    return "#" + "".join(out)


def alpha(color: str, value: str) -> str:
    return norm_hex(color) + value.lower()


def frozen_values_for(night: dict[str, str], day: dict[str, str],
                      keys: set[str]) -> dict[str, str]:
    """Pick ONE fixed value per frozen key, independent of the active theme.

    Stock palettes are internally consistent: an icon color pairs with its
    badge background, and selected text pairs with the selection fill. Picking
    each key independently (e.g. by contrast) would break those pairs. So we
    choose per GROUP: whichever variant (night or day) has the better
    worst-case visibility on both a light and a dark desktop, all keys of the
    group come from that same variant.
    """
    light_bg, dark_bg = "#ffffff", "#202b36"

    def visibility(color: str) -> float:
        if not color.startswith("#"):
            return -1.0
        return min(contrast(color, light_bg), contrast(color, dark_bg))

    def group(key: str) -> str:
        # Badge + check must match; selected bubble + selected text must match.
        if "verifiedicon" in key.lower() or "verifiedcheck" in key.lower():
            return "verified"
        if "unread" in key.lower():
            return "unread"
        if key.endswith("Selected") or "select" in key.lower():
            return "selection"
        if "online" in key.lower() or "sent" in key.lower() or "sending" in key.lower():
            return "status"
        if "check" in key.lower():
            return "checks"
        return "other:" + key

    groups: dict[str, list[str]] = {}
    for key in sorted(keys):
        groups.setdefault(group(key), []).append(key)

    out: dict[str, str] = {}
    for members in groups.values():
        def total(variant: dict[str, str]) -> float:
            return sum(visibility(variant[k]) for k in members if k in variant)

        # The night palette wins ties: its indicators were designed for dark
        # surfaces, and most Omarchy themes are dark.
        chosen = day if total(day) > total(night) + 1e-9 else night
        for key in members:
            if key in chosen:
                out[key] = chosen[key]
            elif key in night and key in day:
                out[key] = night[key]
            elif key in night or key in day:
                out[key] = night.get(key, day.get(key, "#888888"))
    return out


# ---------------------------------------------------------------------------
# Omarchy colors (prefer omarchy-theme-color: it fills aliases + fallbacks)
# ---------------------------------------------------------------------------

def omarchy_colors(path: Path) -> tuple[dict[str, str], str, str]:
    colors: dict[str, str] = {}
    try:
        proc = subprocess.run(
            ["omarchy-theme-color", "--file", str(path), "--all"],
            capture_output=True, text=True, check=True,
        )
        for line in proc.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) == 2:
                if parts[1].startswith("#"):
                    colors[parts[0]] = norm_hex(parts[1])
                elif parts[0] in ("mode", "theme_type"):
                    colors[parts[0]] = parts[1].strip()
    except (OSError, subprocess.CalledProcessError):
        pass

    if not colors and path.exists():
        with path.open("rb") as fh:
            for key, value in tomllib.load(fh).items():
                if isinstance(value, str):
                    if value.startswith("#"):
                        colors[key] = norm_hex(value)
                    elif key in ("mode", "theme_type"):
                        colors[key] = value.strip()

    if "background" not in colors or "foreground" not in colors:
        raise ValueError(
            f"could not read Omarchy colors from {path} "
            "(is omarchy-theme-color available and colors.toml valid?)"
        )

    def get(*names: str, default: str | None = None) -> str:
        for name in names:
            if name in colors:
                return colors[name]
        if default is None:
            raise ValueError(f"missing Omarchy color: {names[0]}")
        return norm_hex(default)

    bg = get("background")
    fg = get("foreground")

    mode = colors.get("mode", colors.get("theme_type", ""))
    if mode not in ("dark", "light"):
        mode = "dark" if lum(bg) < 0.35 else "light"
    is_dark = (mode == "dark")

    default_dark = "#1e1e1e" if is_dark else mix(bg, "#000000", 0.05)
    default_darker = "#161616" if is_dark else mix(bg, "#000000", 0.10)
    default_lighter = "#3c3836" if is_dark else mix(bg, fg, 0.08)

    result = {
        "bg": bg,
        "dark": get("dark_background", "dark_bg", default=default_dark),
        "darker": get("darker_background", "darker_bg", default=default_darker),
        "lighter": get("lighter_background", "lighter_bg", default=default_lighter),
        "fg": fg,
        "dim": get("dark_foreground", "dark_fg", default=mix(bg, fg, 0.45)),
        "bright": get("bright_foreground", "bright_fg", default=fg),
        "muted": get("muted", default=mix(bg, fg, 0.4)),
        "accent": get("accent", default=get("blue", default=fg)),
        "selection": get("selection", "selection_background", default=mix(bg, fg, 0.15)),
        "red": get("red", default="#e06060"),
        "green": get("green", default="#60c060"),
        "cyan": get("cyan", default="#60c0c0"),
        "blue": get("blue", default=fg),
        "yellow": get("yellow", default="#d0a050"),
        "orange": get("orange", default="#d08050"),
        "magenta": get("magenta", default="#c060c0"),
    }
    return result, mode, colors.get("mode", mode)


# ---------------------------------------------------------------------------
# Anchor overrides: the keys actually tinted with Omarchy colors.
# Everything else in the base palette is left as-is; aliases automatically
# inherit these anchors (or the frozen hex values).
# ---------------------------------------------------------------------------

def anchors(c: dict[str, str], mode: str = "dark") -> dict[str, str]:
    bg, dark, darker, lighter = c["bg"], c["dark"], c["darker"], c["lighter"]
    fg, dim, bright, muted = c["fg"], c["dim"], c["bright"], c["muted"]
    accent, red = c["accent"], c["red"]

    # Outgoing bubbles carry the Omarchy accent, BUT the ticks/timestamps on
    # them are frozen stock white. A light accent (e.g. Tokyo Night blue) would
    # make white ticks invisible, so darken the bubble until white has >= 4.5
    # contrast. The hue stays Omarchy, the indicators stay visible.
    bubble = accent
    for _ in range(20):
        if contrast("#ffffff", bubble) >= 4.5:
            break
        bubble = mix(bubble, "#000000", 0.06)
    on_accent = "#ffffff"
    out_text = mix(on_accent, bubble, 0.28)   # secondary text on accent bubbles

    badge = accent
    for _ in range(20):
        if contrast("#ffffff", badge) >= 4.5:
            break
        badge = mix(badge, "#000000", 0.06)

    is_dark = (mode == "dark")
    muted_badge = mix(darker, fg, 0.18) if is_dark else mix(lighter, "#000000", 0.22)
    active_chat_bg = mix(bg, accent, 0.22) if is_dark else mix(bg, accent, 0.16)
    active_chat_ripple = mix(bg, accent, 0.32) if is_dark else mix(bg, accent, 0.24)

    tick_in_bubble = accent
    for _ in range(20):
        if contrast(tick_in_bubble, bubble) >= 3.2:
            break
        tick_in_bubble = mix(tick_in_bubble, "#ffffff", 0.1)

    a: dict[str, str] = {
        # --- window / generic surfaces ---
        "windowBg": bg,
        "windowBgOver": lighter,
        "windowBgRipple": lighter,
        "windowBgActive": accent,
        "windowFg": fg,
        "windowFgOver": fg,
        "windowFgActive": on_accent,
        "windowSubTextFg": dim,
        "windowSubTextFgOver": dim,
        "windowBoldFg": bright,
        "windowBoldFgOver": bright,
        "windowShadowFgFallback": dark,
        "imageBg": darker,

        # --- buttons ---
        "activeButtonBg": accent,
        "activeButtonBgOver": mix(accent, lighter, 0.14),
        "activeButtonBgRipple": mix(accent, lighter, 0.26),
        "activeButtonFg": on_accent,
        "activeButtonFgOver": on_accent,
        "activeButtonSecondaryFg": out_text,
        "activeButtonSecondaryFgOver": out_text,
        "activeLineFg": accent,
        "activeLineFgError": red,
        "lightButtonBg": bg,
        "lightButtonBgOver": lighter,
        "lightButtonBgRipple": lighter,
        "lightButtonFg": accent,
        "lightButtonFgOver": accent,
        "attentionButtonFg": red,
        "attentionButtonFgOver": red,
        "attentionButtonBgOver": alpha(red, "40"),
        "attentionButtonBgRipple": alpha(red, "64"),
        "outlineButtonBg": bg,
        "outlineButtonBgOver": lighter,
        "outlineButtonOutlineFg": accent,
        "outlineButtonBgRipple": lighter,

        # --- menus / scrollbars / inputs ---
        "menuBg": bg,
        "menuBgOver": lighter,
        "menuBgRipple": darker,
        "menuIconFg": dim,
        "menuIconFgOver": fg,
        "menuSubmenuArrowFg": muted,
        "menuFgDisabled": muted,
        "menuSeparatorFg": darker,
        "scrollBarBg": alpha(fg, "53"),
        "scrollBarBgOver": alpha(fg, "7a"),
        "scrollBg": alpha(fg, "1a"),
        "scrollBgOver": alpha(fg, "2c"),
        "smallCloseIconFg": muted,
        "smallCloseIconFgOver": fg,
        "placeholderFg": dim,
        "placeholderFgActive": muted,
        "inputBorderFg": darker,
        "filterInputBorderFg": lighter,
        "filterInputInactiveBg": lighter,
        "filterInputActiveBg": lighter,
        "sliderBgInactive": darker,
        "sliderBgActive": accent,
        "tooltipBg": dark,
        "tooltipFg": fg,
        "tooltipBorderFg": dark,

        # --- title bar ---
        "titleBg": dark,
        "titleBgActive": lighter,
        "titleFg": dim,
        "titleFgActive": fg,
        "titleButtonBg": dark,
        "titleButtonFg": dim,
        "titleButtonBgOver": lighter,
        "titleButtonFgOver": fg,
        "titleButtonBgActive": lighter,
        "titleButtonFgActive": dim,
        "titleButtonBgActiveOver": lighter,
        "titleButtonFgActiveOver": fg,
        "titleButtonCloseBg": dark,
        "titleButtonCloseFg": dim,
        "titleButtonCloseBgOver": red,
        "titleButtonCloseBgActive": lighter,
        "titleButtonCloseBgActiveOver": red,

        # --- boxes / contacts ---
        "cancelIconFg": dim,
        "cancelIconFgOver": fg,
        "boxBg": bg,
        "boxTextFgError": red,
        "boxTitleFg": fg,
        "boxSearchBg": bg,
        "boxTitleAdditionalFg": dim,
        "boxDividerBg": darker,
        "boxDividerFg": dim,
        "membersAboutLimitFg": dim,
        "contactsBg": bg,
        "contactsBgOver": lighter,
        "contactsStatusFg": dim,
        "contactsStatusFgOver": dim,
        "callArrowMissedFg": red,

        # --- intro / login ---
        "introBg": bg,
        "introTitleFg": fg,
        "introDescriptionFg": dim,
        "introErrorFg": red,
        "introCoverTopBg": mix(accent, darker, 0.35),
        "introCoverBottomBg": mix(accent, darker, 0.6),
        "introCoverIconsFg": mix(accent, bg, 0.45),

        # --- chat list ---
        "dialogsBg": bg,
        "dialogsNameFg": fg,
        "dialogsDateFg": dim,
        "dialogsTextFg": dim,
        "dialogsTextFgService": accent,
        "dialogsDraftFg": red,
        "dialogsBgOver": lighter,
        "dialogsNameFgOver": fg,
        "dialogsDateFgOver": dim,
        "dialogsTextFgOver": dim,
        "dialogsTextFgServiceOver": accent,
        "dialogsRippleBg": lighter,
        "searchedBarBg": lighter,
        "searchedBarFg": dim,
        "topBarBg": bg,
        "dialogsArchiveFg": dim,
        "dialogsArchiveFgOver": fg,

        # --- active chat row (adapts to Omarchy) ---
        "dialogsBgActive": active_chat_bg,
        "dialogsRippleBgActive": active_chat_ripple,
        "dialogsNameFgActive": fg,
        "dialogsDateFgActive": dim,
        "dialogsTextFgActive": dim,
        "dialogsTextFgServiceActive": accent,
        "dialogsChatIconFgActive": fg,

        # --- unread badges (adapt to Omarchy) ---
        "dialogsUnreadBg": badge,
        "dialogsUnreadBgOver": mix(badge, lighter, 0.15),
        "dialogsUnreadFg": "#ffffff",
        "dialogsUnreadFgOver": "#ffffff",
        "dialogsUnreadBgMuted": muted_badge,
        "dialogsUnreadBgMutedOver": mix(muted_badge, fg, 0.12),
        "dialogsUnreadBgActive": "#ffffff" if is_dark else badge,
        "dialogsUnreadFgActive": accent if is_dark else "#ffffff",
        "dialogsUnreadBgMutedActive": mix(active_chat_bg, fg, 0.25),

        # --- online badge and status (adapt to Omarchy) ---
        "dialogsOnlineBadgeFg": accent,
        "dialogsOnlineBadgeFgActive": accent,
        "contactsStatusFgOnline": accent,
        "windowActiveTextFg": accent,

        # --- verified check badge (adapt to Omarchy) ---
        "dialogsVerifiedIconBg": badge,
        "dialogsVerifiedIconBgOver": mix(badge, lighter, 0.15),
        "dialogsVerifiedIconFg": "#ffffff",
        "dialogsVerifiedIconFgOver": "#ffffff",
        "dialogsVerifiedIconBgActive": "#ffffff" if is_dark else badge,
        "dialogsVerifiedIconFgActive": accent if is_dark else "#ffffff",
        "profileVerifiedCheckBg": badge,
        "profileVerifiedCheckFg": "#ffffff",

        # --- checkboxes (adapt to Omarchy) ---
        "checkboxFg": muted,
        "overviewCheckBg": badge,
        "overviewCheckFg": "#ffffff",
        "overviewCheckBorder": dim,

        # --- sidebar & tray badges / radial (adapt to Omarchy) ---
        "sideBarBadgeBg": badge,
        "sideBarBadgeFg": "#ffffff",
        "sideBarBadgeBgMuted": lighter,
        "trayCounterBg": badge,
        "trayCounterFg": "#ffffff",
        "radialFg": accent,

        # --- checkmarks (adapt to Omarchy) ---
        "dialogsSentIconFg": accent,
        "dialogsSentIconFgOver": mix(accent, lighter, 0.15),
        "dialogsSentIconFgActive": on_accent,
        "historyOutIconFg": tick_in_bubble,
        "historyOutIconFgSelected": on_accent,
        "historyIconFgInverted": tick_in_bubble,

        # --- chat area ---
        "emojiPanBg": bg,
        "emojiPanCategories": bg,
        "emojiPanHeaderFg": dim,
        "emojiPanHeaderBg": lighter,
        "emojiIconFg": dim,
        "emojiIconFgActive": accent,
        "historyTextInFg": fg,
        "historyTextOutFg": on_accent,
        # historyOutIconFg / historyIconFgInverted / *Selected are FROZEN
        # (white ticks). They stay visible thanks to the darkened bubble.
        "historyLinkInFg": accent,
        "historyLinkOutFg": on_accent,
        "historyFileNameInFg": fg,
        "historyFileNameOutFg": on_accent,
        "historyComposeAreaBg": bg,
        "historyComposeAreaFg": fg,
        "historyComposeIconFg": dim,
        "historyComposeIconFgOver": fg,
        "historyComposeButtonBg": bg,
        "historyComposeButtonBgOver": lighter,
        "historyComposeButtonBgRipple": lighter,
        "historySendIconFg": accent,
        "historySendIconFgOver": accent,
        "historyReplyBg": bg,
        "historyReplyIconFg": accent,
        "historyPinnedBg": dark,
        "historyToDownBg": dark,
        "historyToDownBgOver": lighter,
        "historyToDownBgRipple": lighter,
        "historyToDownFg": fg,
        "historyScrollBarBg": alpha(fg, "7a"),
        "historyScrollBarBgOver": alpha(fg, "bc"),
        "historyScrollBg": alpha(fg, "4c"),
        "historyScrollBgOver": alpha(fg, "6b"),
        "historyUnreadBarBg": dark,
        "historyUnreadBarFg": fg,

        # --- message bubbles ---
        "msgInBg": lighter,
        "msgOutBg": bubble,
        "msgInServiceFg": dim,
        "msgInDateFg": dim,
        "msgInMonoFg": bright,
        "msgOutMonoFg": on_accent,
        "msgInReplyBarColor": accent,
        "msgOutReplyBarColor": on_accent,
        "msgServiceBg": alpha(darker, "d5"),
        "msgServiceFg": fg,
        "msgFileThumbIconFg": fg,
        "msgImgReplyBarColor": fg,
        "msgWaveformInActive": accent,
        "msgWaveformOutActive": on_accent,
        "msgWaveformInInactive": muted,
        "msgWaveformOutInactive": alpha(on_accent, "40"),
        "msgBotKbOverBgAdd": alpha(accent, "1f"),
        "msgBotKbRippleBg": alpha(accent, "1a"),
        "botKbBg": lighter,
        "botKbDownBg": mix(lighter, fg, 0.12),

        # --- misc panels ---
        "mainMenuBg": bg,
        "mainMenuCoverBg": mix(accent, darker, 0.35),
        "mainMenuCoverFg": on_accent,
        "mainMenuCloudBg": mix(accent, darker, 0.55),
        "mediaPlayerBg": bg,
        "mediaPlayerActiveFg": accent,
        "mediaPlayerInactiveFg": darker,
        "notificationBg": bg,
        "profileStatusFgOver": dim,
        "sideBarBg": dark,
        "sideBarBgRipple": lighter,
        "sideBarTextFg": dim,
        "sideBarIconFg": dim,
        "sideBarBgActive": active_chat_bg,
        "sideBarTextFgActive": fg,
        "sideBarIconFgActive": accent,
        "importantTooltipFgLink": accent,
        "statisticsChartInactive": alpha(darker, "c8"),
        "statisticsChartActive": alpha(lighter, "d8"),

        # --- peer names and userpics (adapt to Omarchy palette) ---
        "historyPeer1NameFg": c["red"],
        "historyPeer1UserpicBg": c["red"],
        "historyPeer1UserpicBg2": mix(c["red"], darker, 0.25),
        "historyPeer2NameFg": c["green"],
        "historyPeer2UserpicBg": c["green"],
        "historyPeer2UserpicBg2": mix(c["green"], darker, 0.25),
        "historyPeer3NameFg": c["yellow"],
        "historyPeer3UserpicBg": c["yellow"],
        "historyPeer3UserpicBg2": mix(c["yellow"], darker, 0.25),
        "historyPeer4NameFg": c["blue"],
        "historyPeer4UserpicBg": c["blue"],
        "historyPeer4UserpicBg2": mix(c["blue"], darker, 0.25),
        "historyPeer5NameFg": c["magenta"],
        "historyPeer5UserpicBg": c["magenta"],
        "historyPeer5UserpicBg2": mix(c["magenta"], darker, 0.25),
        "historyPeer6NameFg": mix(c["magenta"], c["red"], 0.4),
        "historyPeer6UserpicBg": mix(c["magenta"], c["red"], 0.4),
        "historyPeer6UserpicBg2": mix(mix(c["magenta"], c["red"], 0.4), darker, 0.25),
        "historyPeer7NameFg": c["cyan"],
        "historyPeer7UserpicBg": c["cyan"],
        "historyPeer7UserpicBg2": mix(c["cyan"], darker, 0.25),
        "historyPeer8NameFg": c["orange"],
        "historyPeer8UserpicBg": c["orange"],
        "historyPeer8UserpicBg2": mix(c["orange"], darker, 0.25),
        "historyPeerUserpicFg": "#ffffff",
        "historyPeerArchiveUserpicBg": muted_badge,

        # --- file bubbles and downloads (adapt to Omarchy) ---
        "msgFile1Bg": c["blue"],
        "msgFile1BgDark": mix(c["blue"], darker, 0.3),
        "msgFile1BgOver": mix(c["blue"], lighter, 0.2),
        "msgFile2Bg": c["green"],
        "msgFile2BgDark": mix(c["green"], darker, 0.3),
        "msgFile2BgOver": mix(c["green"], lighter, 0.2),
        "msgFile3Bg": c["red"],
        "msgFile3BgDark": mix(c["red"], darker, 0.3),
        "msgFile3BgOver": mix(c["red"], lighter, 0.2),
        "msgFile4Bg": c["yellow"],
        "msgFile4BgDark": mix(c["yellow"], darker, 0.3),
        "msgFile4BgOver": mix(c["yellow"], lighter, 0.2),
        "msgFileInBg": accent,
        "msgFileInBgOver": mix(accent, lighter, 0.2),
        "msgFileOutBg": on_accent,
        "msgFileOutBgOver": mix(on_accent, darker, 0.1),
        "msgFileThumbLinkInFg": accent,
        "msgFileThumbLinkOutFg": on_accent,
        "historyFileInIconFg": on_accent,
        "historyFileInRadialFg": accent,
        "historyFileOutIconFg": bubble,
        "historyFileOutRadialFg": on_accent,
        "historyFileThumbIconFg": fg,
        "historyFileThumbRadialFg": accent,
        "historyVideoMessageProgressFg": accent,

        # --- media viewer (adapt to Omarchy) ---
        "mediaviewBg": alpha(darker, "fa") if is_dark else alpha(dark, "fa"),
        "mediaviewCaptionBg": alpha(darker, "99"),
        "mediaviewControlBg": alpha(darker, "60"),
        "mediaviewMenuBg": dark,
        "mediaviewMenuBgOver": lighter,
        "mediaviewMenuBgRipple": lighter,
        "mediaviewTextLinkFg": accent,
        "mediaviewPlaybackActive": accent,
        "mediaviewPlaybackActiveOver": bright,
        "mediaviewPlaybackInactive": alpha(fg, "30"),
        "mediaviewPlaybackInactiveOver": alpha(fg, "50"),
        "mediaviewPlaybackProgressFg": accent,
        "mediaviewFileBlueCornerFg": c["blue"],
        "mediaviewFileGreenCornerFg": c["green"],
        "mediaviewFileRedCornerFg": c["red"],
        "mediaviewFileYellowCornerFg": c["yellow"],
        "mediaviewTransparentBg": bg,
        "mediaviewTransparentFg": dim,

        # --- calls (adapt to Omarchy) ---
        "callBg": alpha(darker, "f8") if is_dark else alpha(bg, "f8"),
        "callBarBg": mix(dark, accent, 0.35),
        "callBarBgMuted": dark,
        "callBarMuteRipple": mix(dark, accent, 0.5),
        "callBarUnmuteRipple": lighter,
        "callAnswerBg": c["green"],
        "callAnswerBgOuter": alpha(c["green"], "30"),
        "callAnswerRipple": mix(c["green"], lighter, 0.2),
        "callHangupBg": c["red"],
        "callHangupRipple": mix(c["red"], darker, 0.2),
        "callCancelBg": darker if is_dark else lighter,
        "callCancelFg": fg,
        "callCancelRipple": lighter,
        "callFingerprintBg": alpha(darker, "80"),
        "callArrowFg": c["green"],
        "callIconFg": on_accent,
        "callNameFg": fg,
        "callStatusFg": dim,
        "callMuteRipple": alpha(fg, "15"),

        # --- chat elements and popups (adapt to Omarchy) ---
        "dialogsSendingIconFg": dim,
        "dialogsSendingIconFgActive": alpha(fg, "80"),
        "dialogsDraftFgActive": red,
        "historyCallArrowInFg": c["green"],
        "historyCallArrowOutFg": on_accent,
        "historyCallArrowMissedInFg": red,
        "historyForwardChooseBg": alpha(darker, "80"),
        "historySendingInIconFg": dim,
        "historySendingOutIconFg": alpha(on_accent, "80"),
        "historySendingInvertedIconFg": alpha(on_accent, "80"),
        "mediaInFg": dim,
        "mediaOutFg": out_text,
        "mediaPlayerDisabledFg": dim,
        "msgDateImgBg": alpha(darker, "60"),
        "msgDateImgBgOver": alpha(darker, "85"),
        "msgDateImgFg": fg,
        "msgOutDateFg": out_text,
        "msgOutServiceFg": out_text,
        "profileAdminStartFg": accent,
        "boxTextFgGood": c["green"],
        "reportSpamBg": lighter,
        "toastBg": alpha(darker, "d0"),
        "videoPlayIconBg": alpha(darker, "80"),
        "videoPlayIconFg": on_accent,
        "youtubePlayIconBg": alpha(red, "d0"),
        "windowShadowFg": alpha(darker, "80"),
        "shadowFg": alpha(darker, "60"),
        "layerBg": alpha(darker, "80"),
        "slideFadeOutBg": alpha(darker, "60"),
        "radialBg": alpha(darker, "60"),
        "stickerPreviewBg": alpha(darker, "d0"),
        "stickerPanDeleteBg": alpha(darker, "d0"),
        "photoCropPointFg": alpha(fg, "80"),
        "notificationSampleNameFg": dim,
        "notificationSampleTextFg": fg,
        "notificationSampleCloseFg": dim,
        "historyToDownShadow": alpha(darker, "40"),
        "historyUnreadBarBorder": alpha(darker, "00"),
        "msgInShadow": alpha(darker, "00"),
        "msgOutShadow": alpha(darker, "00"),
        "titleShadow": alpha(darker, "00"),
        "imageBgTransparent": bg,
        "introCoverPlaneTrace": accent,
        "introCoverPlaneInner": lighter,
        "introCoverPlaneOuter": dim,
        "introCoverPlaneTop": fg,

        # --- group calls and voice chats (adapt to Omarchy) ---
        "groupCallBg": dark,
        "groupCallActiveFg": accent,
        "groupCallMembersBg": darker,
        "groupCallMembersBgOver": lighter,
        "groupCallMembersBgRipple": lighter,
        "groupCallMembersFg": fg,
        "groupCallMemberActiveIcon": c["green"],
        "groupCallMemberActiveStatus": c["green"],
        "groupCallMemberInactiveIcon": dim,
        "groupCallMemberInactiveStatus": dim,
        "groupCallMemberMutedIcon": red,
        "groupCallMemberNotJoinedStatus": dim,
        "groupCallIconFg": on_accent,
        "groupCallMenuBg": dark,
        "groupCallMenuBgOver": lighter,
        "groupCallMenuBgRipple": lighter,
        "groupCallLeaveBg": alpha(red, "80"),
        "groupCallLeaveBgRipple": alpha(red, "a0"),
        "groupCallVideoTextFg": alpha(fg, "e0"),
        "groupCallVideoSubTextFg": alpha(fg, "c0"),

        # --- picture in picture, wallet and calling extras ---
        "mediaviewPipControlsFg": alpha(fg, "d9"),
        "mediaviewPipControlsFgOver": fg,
        "mediaviewPipFade": alpha(darker, "95"),
        "mediaviewPipPlaybackActive": accent,
        "mediaviewPipPlaybackInactive": alpha(fg, "26"),
        "callBgOpaque": darker,
        "callBgButton": alpha(darker, "80"),
        "callIconBg": alpha(fg, "20"),
        "callIconBgActive": on_accent,
        "callIconFgActive": darker,
        "callIconActiveRipple": lighter,
        "spellUnderline": alpha(red, "88"),
        "trayCounterBgMute": muted,
        "trayCounterBgMacInvert": on_accent,
        "trayCounterFgMacInvert": alpha(on_accent, "01"),
        "paymentsTipActive": c["green"],
        "photoEditorItemBaseHandleFg": accent,
        "walletTitleBg": dark,
        "walletTopBg": darker,
        "walletBalanceFg": fg,
        "walletSubBalanceFg": dim,
        "walletTopLabelFg": dim,
        "walletTitleButtonFg": dim,
        "walletTitleButtonBgOver": lighter,
        "walletTitleButtonFgOver": fg,
        "songCoverOverlayFg": alpha(darker, "66"),

        # --- maps, calls and extras ---
        "mapPointDrop": red,
        "mapPointDot": on_accent,
        "mediaviewPlaybackIconRipple": alpha(fg, "14"),
        "groupCallLive1": c["green"],
        "groupCallLive2": c["cyan"],
        "groupCallMuted1": c["blue"],
        "groupCallMuted2": c["cyan"],
        "groupCallForceMutedBar1": c["magenta"],
        "groupCallForceMutedBar2": c["blue"],
        "groupCallForceMutedBar3": c["cyan"],
        "groupCallForceMuted1": c["blue"],
        "groupCallForceMuted2": c["magenta"],
        "groupCallForceMuted3": red,
        "outdatedFg": on_accent,
        "outdateSoonBg": c["orange"],
        "outdatedBg": red,
        "walletTopIconRipple": alpha(fg, "12"),
    }
    return dict(a)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def build(raw: dict[str, str], frozen_values: dict[str, str],
          over: dict[str, str], fallback: dict[str, str],
          meta: dict[str, str], pulse: str) -> str:
    lines = [
        "// Omarchy -> Telegram Desktop / AyuGram Desktop theme",
        f"// theme: {meta['theme']}   mode: {meta['mode']}   base: {meta['base']}",
        f"// frozen: {len(frozen_values)} indicator keys keep stock Telegram colors",
        f"// generated: {_dt.datetime.now().isoformat(timespec='seconds')}",
        f"// pulse: {pulse}",
        "//",
        "// Generated by omarchy-telegram-theme.py - edit frozen.txt, not this file.",
        "",
    ]
    for key, value in raw.items():
        if key in frozen_values:
            out = frozen_values[key]      # concrete hex, never an alias
        elif key in over:
            out = over[key]
        elif not value.startswith("#") and value not in raw:
            # The day/night stock palettes are not perfectly identical: a few
            # aliases point at keys defined only in the other palette. Resolve
            # those from the complementary base so no alias dangles.
            out = fallback.get(value, value)
        else:
            out = value                   # keep the alias -> inherits anchors
        lines.append(f"{key}: {out};")
    return "\n".join(lines) + "\n"


def solid_png(rgb: tuple[int, int, int]) -> bytes:
    """A 1x1 opaque PNG, exactly like the stock Telegram night themes ship.

    Without a background image in the .tdesktop-theme zip, Telegram falls back
    to DefaultWallPaper() (a light wallpaper) and the theme is registered as
    LIGHT even when every palette color is dark. A dark 1x1 background marks
    the theme as dark and keeps the chat area in the Omarchy palette instead
    of resetting it to the default light wallpaper.
    """
    import struct

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    r, g, b = rgb
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)  # 1x1, RGB8
    raw = bytes((0, r, g, b))                              # filter byte + pixel
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def write_theme(out_path: Path, palette: str, mode: str,
                background: str) -> None:
    """Write in place (same inode!) so QFileSystemWatcher keeps watching."""
    import io
    h = norm_hex(background)
    rgb = (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("colors.tdesktop-theme", palette.encode("utf-8"))
        zf.writestr("background.png", solid_png(rgb))
    data = buf.getvalue()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        with out_path.open("r+b") as fh:
            fh.seek(0)
            fh.write(data)
            fh.truncate()
            fh.flush()
            os.fsync(fh.fileno())
    else:
        with out_path.open("wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--colors", type=Path, default=STATE / "colors.toml",
                    help="Omarchy colors.toml (default: current theme)")
    ap.add_argument("--theme-name", default=None)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--pulse", action="store_true",
                    help="rewrite once more (a second fileChanged event)")
    ap.add_argument("--frozen-base", choices=("auto", "night", "day"), default=None,
                    help="which stock palette supplies frozen colors "
                         "(default: auto = fixed, best-contrast mix of both)")
    args = ap.parse_args()

    colors_path = args.colors
    if args.theme_name and (colors_path == STATE / "colors.toml" or not colors_path.exists()):
        slug = args.theme_name.lower().strip().replace(" ", "-")
        user_theme = Path.home() / f".config/omarchy/themes/{slug}/colors.toml"
        sys_theme = Path(f"/usr/share/omarchy/themes/{slug}/colors.toml")
        if user_theme.exists():
            colors_path = user_theme
        elif sys_theme.exists():
            colors_path = sys_theme

    colors, mode, raw_mode = omarchy_colors(colors_path)
    base_name = "day" if mode == "light" else "night"
    base_path = BASE_DIR / f"{base_name}.palette"
    if not base_path.exists():
        raise SystemExit(f"missing base palette: {base_path}")
    raw = parse_palette(base_path.read_text())

    night_res = resolve_all(parse_palette((BASE_DIR / "night.palette").read_text()))
    day_res = resolve_all(parse_palette((BASE_DIR / "day.palette").read_text()))
    frozen, created = load_frozen(set(night_res) | set(day_res))

    if created:
        print(f"omarchy-telegram-theme: created default frozen list: {FROZEN_FILE}",
              file=sys.stderr)

    choice = args.frozen_base or os.environ.get("OMARCHY_TG_FROZEN_BASE", "auto")
    is_light_theme = (mode == "light" or lum(colors["bg"]) > 0.35)
    if choice == "auto":
        source = day_res if is_light_theme else night_res
        chosen = {k: source[k] for k in frozen if k in source}
    else:
        source = night_res if choice == "night" else day_res
        chosen = {k: source[k] for k in frozen if k in source}

    # A couple of stock pairs are too low-contrast on light Omarchy themes
    # (blue online dot on a white chat list, blue ticks, white check in a
    # light-blue badge). overrides.txt lists fixed dark/light variants for
    # those keys only; every other frozen color stays exactly stock.
    OVERRIDES = HERE / "overrides.txt"
    if OVERRIDES.exists():
        for line in OVERRIDES.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            key, spec = (part.strip() for part in line.split(":", 1))
            if key not in chosen:
                continue
            parts = spec.split()
            if len(parts) == 1:
                dark_hex, light_hex = parts[0], parts[0]
            elif len(parts) == 2:
                dark_hex, light_hex = parts
            else:
                raise ValueError(f"override for {key} needs 1 or 2 hex values: {spec}")
            for value in (dark_hex, light_hex):
                if not value.startswith("#"):
                    raise ValueError(f"override for {key} must be hex colors: {spec}")
            chosen[key] = norm_hex(light_hex if is_light_theme else dark_hex)
    # Freeze only keys that exist in the active base palette (the app ignores
    # the rest anyway); resolve any leftover alias to a concrete hex.
    active_resolved = resolve_all(raw)
    frozen_values = {
        key: chosen.get(key, active_resolved.get(key, "#888888"))
        for key in frozen
        if key in raw
    }
    complement = "day" if base_name == "night" else "night"
    fallback = resolve_all(parse_palette((BASE_DIR / f"{complement}.palette").read_text()))

    theme_name = args.theme_name
    if theme_name is None:
        name_path = STATE.parent / "theme.name"
        theme_name = name_path.read_text().strip() if name_path.exists() else "omarchy"

    palette = build(
        raw,
        frozen_values,
        anchors(colors, mode=mode),
        fallback,
        {"theme": theme_name, "mode": mode, "base": base_name},
        pulse=str(_dt.datetime.now().strftime("%s%f")) if args.pulse else "0",
    )
    # A dark 1x1 background is what makes Telegram register the theme as DARK
    # (it also prevents the fallback to the light DefaultWallPaper). For light
    # Omarchy themes the background stays light, matching their real mode.
    bg_color = colors["darker"] if mode == "dark" else colors["bg"]
    if mode == "dark" and lum(bg_color) > 0.3:
        bg_color = mix(bg_color, "#000000", 0.5)
    write_theme(args.out, palette, mode, bg_color)
    print(f"wrote {args.out}  (theme={raw_mode or mode}, base={base_name}, "
          f"frozen={len(frozen)}{' [list created]' if created else ''})")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # keep the hook non-fatal but loud
        print(f"omarchy-telegram-theme: {exc}", file=sys.stderr)
        sys.exit(1)
