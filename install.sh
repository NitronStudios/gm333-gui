#!/usr/bin/env bash
#
# Ant Esports GM333 Linux GUI Universal Installer
# Compatible with: Arch Linux, Ubuntu, Debian, Linux Mint, Pop!_OS, Fedora, openSUSE, etc.
#

set -e

GREEN="\033[1;32m"
CYAN="\033[1;36m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
BOLD="\033[1m"
RESET="\033[0m"

echo -e "${CYAN}================================================================${RESET}"
echo -e "${BOLD}       Ant Esports GM333 Linux GUI Universal Installer          ${RESET}"
echo -e "${CYAN}================================================================${RESET}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detect Distro
DISTRO="unknown"
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO="$ID"
fi

echo -e "${CYAN}[*]${RESET} Detected Linux Distribution: ${BOLD}${PRETTY_NAME:-$DISTRO}${RESET}"

# Function to check if a command exists
has_cmd() {
    command -v "$1" >/dev/null 2>&1
}

# Install Dependencies
echo -e "\n${CYAN}[1/5] Checking and installing system dependencies...${RESET}"

install_deps() {
    if has_cmd pacman; then
        echo -e "${YELLOW}[*] Installing dependencies via pacman (Arch Linux)...${RESET}"
        sudo pacman -S --needed --noconfirm python-gobject gtk3 libpulse python-pillow python-numpy
    elif has_cmd apt-get; then
        echo -e "${YELLOW}[*] Installing dependencies via apt (Debian/Ubuntu/Mint)...${RESET}"
        sudo apt-get update -qq
        sudo apt-get install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 pulseaudio-utils python3-pil python3-numpy
    elif has_cmd dnf; then
        echo -e "${YELLOW}[*] Installing dependencies via dnf (Fedora)...${RESET}"
        sudo dnf install -y python3-gobject gtk3 pulseaudio-utils python3-pillow python3-numpy
    elif has_cmd zypper; then
        echo -e "${YELLOW}[*] Installing dependencies via zypper (openSUSE)...${RESET}"
        sudo zypper install -y python3-gobject python3-gobject-Gdk gtk3 pulseaudio-utils python3-Pillow python3-numpy
    else
        echo -e "${YELLOW}[!] Unknown package manager. Please ensure python3-gobject, gtk3, numpy, and pulseaudio-utils are installed.${RESET}"
    fi
}

if [ "$1" != "--no-deps" ]; then
    install_deps
fi

# Install Udev Rule
echo -e "\n${CYAN}[2/5] Installing udev rule for GM333 non-root hardware access...${RESET}"
UDEV_RULE_SRC="$SCRIPT_DIR/packaging/99-ant-esports-gm333.rules"
UDEV_RULE_DST="/etc/udev/rules.d/99-ant-esports-gm333.rules"

if [ -f "$UDEV_RULE_SRC" ]; then
    sudo cp "$UDEV_RULE_SRC" "$UDEV_RULE_DST"
    sudo chmod 644 "$UDEV_RULE_DST"
    echo -e "${GREEN}[✓]${RESET} Installed $UDEV_RULE_DST"
    sudo udevadm control --reload-rules && sudo udevadm trigger || true
    echo -e "${GREEN}[✓]${RESET} Reloaded udev rules and triggered device permissions"
fi

# Install Application Files to /opt/gm333-gui
echo -e "\n${CYAN}[3/5] Installing application files to /opt/gm333-gui...${RESET}"
sudo mkdir -p /opt/gm333-gui
sudo cp -r "$SCRIPT_DIR/gm333gui" /opt/gm333-gui/
sudo cp -r "$SCRIPT_DIR/assets" /opt/gm333-gui/
sudo cp "$SCRIPT_DIR/gm333-gui" /opt/gm333-gui/
sudo chmod +x /opt/gm333-gui/gm333-gui

# Create symlink in /usr/local/bin
sudo ln -sf /opt/gm333-gui/gm333-gui /usr/local/bin/gm333-gui
echo -e "${GREEN}[✓]${RESET} Created binary symlink /usr/local/bin/gm333-gui"

# Install Icons
echo -e "\n${CYAN}[4/5] Installing application icons...${RESET}"
sudo mkdir -p /usr/share/icons/hicolor/256x256/apps
sudo mkdir -p /usr/share/icons/hicolor/128x128/apps
sudo mkdir -p /usr/share/icons/hicolor/64x64/apps
sudo mkdir -p /usr/share/icons/hicolor/48x48/apps
sudo mkdir -p /usr/share/pixmaps

[ -f "$SCRIPT_DIR/assets/gm333-256.png" ] && sudo cp "$SCRIPT_DIR/assets/gm333-256.png" /usr/share/icons/hicolor/256x256/apps/gm333.png
[ -f "$SCRIPT_DIR/assets/gm333-128.png" ] && sudo cp "$SCRIPT_DIR/assets/gm333-128.png" /usr/share/icons/hicolor/128x128/apps/gm333.png
[ -f "$SCRIPT_DIR/assets/gm333-64.png" ] && sudo cp "$SCRIPT_DIR/assets/gm333-64.png" /usr/share/icons/hicolor/64x64/apps/gm333.png
[ -f "$SCRIPT_DIR/assets/gm333-48.png" ] && sudo cp "$SCRIPT_DIR/assets/gm333-48.png" /usr/share/icons/hicolor/48x48/apps/gm333.png
[ -f "$SCRIPT_DIR/assets/gm333.png" ] && sudo cp "$SCRIPT_DIR/assets/gm333.png" /usr/share/pixmaps/gm333.png

if has_cmd gtk-update-icon-cache; then
    sudo gtk-update-icon-cache -f /usr/share/icons/hicolor 2>/dev/null || true
fi
echo -e "${GREEN}[✓]${RESET} App icons installed into system icon theme"

# Install Desktop Entry
echo -e "\n${CYAN}[5/5] Installing desktop application shortcut...${RESET}"
sudo mkdir -p /usr/share/applications
sudo cp "$SCRIPT_DIR/packaging/gm333-gui.desktop" /usr/share/applications/gm333-gui.desktop
if has_cmd update-desktop-database; then
    sudo update-desktop-database /usr/share/applications 2>/dev/null || true
fi
echo -e "${GREEN}[✓]${RESET} Desktop entry registered: Ant Esports GM333"

echo -e "\n${GREEN}================================================================${RESET}"
echo -e "${GREEN}${BOLD}       Installation Completed Successfully!                     ${RESET}"
echo -e "${GREEN}================================================================${RESET}"
echo -e "You can now launch the application in two ways:"
echo -e "  1. Search for ${BOLD}'Ant Esports GM333'${RESET} in your Application Menu / Dash"
echo -e "  2. Or run command: ${BOLD}gm333-gui${RESET} in any terminal"
echo ""
