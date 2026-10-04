#!/usr/bin/env bash
#
# Ant Esports GM333 Linux GUI Uninstaller
#

set -e

RED="\033[1;31m"
GREEN="\033[1;32m"
CYAN="\033[1;36m"
BOLD="\033[1m"
RESET="\033[0m"

echo -e "${RED}================================================================${RESET}"
echo -e "${BOLD}       Ant Esports GM333 Linux GUI Uninstaller                  ${RESET}"
echo -e "${RED}================================================================${RESET}"

echo -e "${CYAN}[*] Removing installed files...${RESET}"

sudo rm -f /usr/local/bin/gm333-gui
sudo rm -rf /opt/gm333-gui
sudo rm -f /usr/share/applications/gm333-gui.desktop
sudo rm -f /usr/share/icons/hicolor/256x256/apps/gm333.png
sudo rm -f /usr/share/icons/hicolor/128x128/apps/gm333.png
sudo rm -f /usr/share/icons/hicolor/64x64/apps/gm333.png
sudo rm -f /usr/share/icons/hicolor/48x48/apps/gm333.png
sudo rm -f /usr/share/pixmaps/gm333.png
sudo rm -f /etc/udev/rules.d/99-ant-esports-gm333.rules

if command -v update-desktop-database >/dev/null 2>&1; then
    sudo update-desktop-database /usr/share/applications 2>/dev/null || true
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    sudo gtk-update-icon-cache -f /usr/share/icons/hicolor 2>/dev/null || true
fi

sudo udevadm control --reload-rules 2>/dev/null || true

echo -e "${GREEN}[✓] Ant Esports GM333 has been successfully uninstalled.${RESET}\n"
