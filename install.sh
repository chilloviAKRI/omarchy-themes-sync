#!/bin/bash
# ==============================================================================
# Omarchy Dynamic Themes Sync Installer
# Supports: Telegram Desktop / AyuGram, Discord (Vencord), Spotify (Spicetify)
# ==============================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BOLD='\033[1m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_banner() {
    echo -e "${BLUE}${BOLD}"
    echo "  ___                               _             "
    echo " / _ \ _ __ ___   __ _ _ __ ___| |__  _   _     "
    echo "| | | | '_ \` _ \ / _\` | '__/ __| '_ \| | | |    "
    echo "| |_| | | | | | | (_| | | | (__| | | | |_| |    "
    echo " \___/|_| |_| |_|\__,_|_|  \___|_| |_|\__, |    "
    echo "  _____ _                              |___/     "
    echo " |_   _| |__   ___ _ __ ___   ___  ___          "
    echo "   | | | '_ \ / _ \ '_ \` _ \ / _ \/ __|         "
    echo "   | | | | | |  __/ | | | | |  __/\__ \         "
    echo "   |_| |_| |_|\___|_| |_| |_|\___||___/         "
    echo "               S Y N C                          "
    echo -e "${NC}"
    echo -e "Dynamic theme synchronization for ${BOLD}Telegram${NC}, ${BOLD}Discord${NC}, and ${BOLD}Spotify${NC} with Omarchy Linux themes."
    echo ""
}

install_telegram() {
    echo -e "\n${BLUE}==>${NC} ${BOLD}Installing Telegram Desktop / AyuGram Theme Sync...${NC}"
    if [[ -f "$REPO_DIR/telegram/install.sh" ]]; then
        bash "$REPO_DIR/telegram/install.sh"
        echo -e "${GREEN}✓ Telegram Theme Sync installed successfully.${NC}"
    else
        echo -e "${RED}Error: telegram/install.sh not found.${NC}"
        return 1
    fi
}

install_discord() {
    echo -e "\n${BLUE}==>${NC} ${BOLD}Installing Discord (Vencord) Theme Sync...${NC}"
    if [[ -f "$REPO_DIR/discord/install.sh" ]]; then
        bash "$REPO_DIR/discord/install.sh"
        echo -e "${GREEN}✓ Discord Theme Sync installed successfully.${NC}"
    else
        echo -e "${RED}Error: discord/install.sh not found.${NC}"
        return 1
    fi
}

install_spotify() {
    echo -e "\n${BLUE}==>${NC} ${BOLD}Installing Spotify (Spicetify) Theme Sync...${NC}"
    if [[ -f "$REPO_DIR/spotify/install.sh" ]]; then
        bash "$REPO_DIR/spotify/install.sh"
        echo -e "${GREEN}✓ Spotify Theme Sync installed successfully.${NC}"
    else
        echo -e "${RED}Error: spotify/install.sh not found.${NC}"
        return 1
    fi
}

print_summary() {
    echo -e "\n${GREEN}${BOLD}==============================================================================${NC}"
    echo -e "${GREEN}${BOLD}                 Installation & Setup Complete!                               ${NC}"
    echo -e "${GREEN}${BOLD}==============================================================================${NC}"
    echo ""
    echo -e "${BOLD}Важные шаги активации / Activation Instructions:${NC}"
    echo ""
    echo -e "${YELLOW}1. Telegram Desktop / AyuGram:${NC}"
    echo "   • Откройте: Настройки -> Настройки чатов -> [три точки вверху] -> Выбрать из файла"
    echo "   • Выберите файл темы: ~/.config/omarchy/telegram-theme/omarchy.tdesktop-theme"
    echo "   • Если вы хотите, чтобы светлая тема тоже синхронизировалась:"
    echo "     Переключите Telegram в дневной режим (Day) и выберите этот же файл еще раз!"
    echo "     После этого и ночной, и дневной режим привязаны к omarchy.tdesktop-theme и"
    echo "     синхронизируются с темами Omarchy автоматически без перезапуска."
    echo ""
    echo -e "${YELLOW}2. Discord (Vencord):${NC}"
    echo "   • Требуется установленный Vencord (https://vencord.dev)."
    echo "   • Тема hot-reload'ится мгновенно через QuickCss без перезапуска Discord."
    echo ""
    echo -e "${YELLOW}3. Spotify (Spicetify):${NC}"
    echo "   • Требуется Spicetify CLI (https://spicetify.app)."
    echo "   • Тема hot-reload'ится на лету через расширение omarchy-sync.js."
    echo "   • Шарик-ползунок удален, цвета прогресс-бара контрастны, macOS Blue selection."
    echo ""
    echo -e "Все хуки установлены в ${BOLD}~/.config/omarchy/hooks/theme-set.d/${NC}."
    echo -e "При любой смене темы в Omarchy все ваши приложения обновятся моментально!"
}

main() {
    print_banner

    if [[ $# -gt 0 ]]; then
        case "$1" in
            --all|-a)
                install_telegram
                install_discord
                install_spotify
                print_summary
                ;;
            --telegram|-t)
                install_telegram
                ;;
            --discord|-d)
                install_discord
                ;;
            --spotify|-s)
                install_spotify
                ;;
            --help|-h)
                echo "Usage: ./install.sh [OPTION]"
                echo "Options:"
                echo "  --all, -a        Install sync for Telegram, Discord, and Spotify"
                echo "  --telegram, -t   Install sync for Telegram / AyuGram"
                echo "  --discord, -d    Install sync for Discord (Vencord)"
                echo "  --spotify, -s    Install sync for Spotify (Spicetify)"
                echo "  --help, -h       Show this help message"
                ;;
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                exit 1
                ;;
        esac
        exit 0
    fi

    echo "Choose what to install:"
    echo "  1) All (Telegram, Discord, Spotify) [Recommended]"
    echo "  2) Telegram Desktop / AyuGram only"
    echo "  3) Discord (Vencord) only"
    echo "  4) Spotify (Spicetify) only"
    echo "  q) Quit"
    echo ""
    read -rp "Select an option [1-4, q]: " choice

    case "$choice" in
        1|"")
            install_telegram
            install_discord
            install_spotify
            print_summary
            ;;
        2)
            install_telegram
            ;;
        3)
            install_discord
            ;;
        4)
            install_spotify
            ;;
        q|Q)
            echo "Cancelled."
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid selection.${NC}"
            exit 1
            ;;
    esac
}

main "$@"
