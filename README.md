# 🖱️ Ant Esports GM333 Linux GUI Control Panel

A native, high-performance Linux desktop application for the **Ant Esports GM333 Gaming Mouse** (Instant Microelectronics `30fa:1440` controller).

Designed to run seamlessly across **any Linux distribution** (**Arch Linux**, **Ubuntu**, **Debian**, **Fedora**, **Linux Mint**, **Pop!_OS**, **openSUSE**, etc.).

---

## ✨ Features

- 🌈 **16 Onboard Hardware Lighting Modes**:
  - Direct control over all hardware lighting modes stored on the mouse microcontroller: *Neon Wave, Cycle Breathing, Static Solid, Flowing Water, Mono Water, Comet Streak, Ambilight, Rhythmic Flicker, Star Trek, Water Ripple, Click Response, Single Breath, Color Stepper, DPI Breathing, Music Sync, and LED Off*.
- 🎛️ **Lighting Customizer**:
  - Live speed adjustment slider (Levels 1–7)
  - Live brightness adjustment slider (Levels 0–4)
  - RGB Color Picker with quick cyber preset swatches + full system color wheel for static & breathing modes.
- 🎵 **Integrated Audio-Reactive Music Sync**:
  - Streams real-time desktop audio via PipeWire / PulseAudio monitor sink directly to mouse LEDs.
  - Works with **Bluetooth earbuds**, wired headphones, and external speakers.
  - Live animated stereo **VU meter** & **Cairo audio spectrum visualizer**.
  - **Dynamic Beat Detection** with neon pulse indicator.
  - 10 custom rhythm color palettes (*Cyberpunk Neon, Vivid Rainbow, Sunset Synthwave, Deep Ocean, Blazing Fire, Matrix Emerald, etc.*).
  - Configurable sensitivity multiplier and LED frame rate (15–40 FPS).
- 🔌 **Plug & Play / Auto-Detection**:
  - Automatic detection of GM333 mouse on USB interface 1.
  - Dynamic device polling (detects disconnect / reconnect).
  - Permission status checker.
- 📦 **Cross-Distro Universal Packaging**:
  - One-click installer with automatic package manager detection (`pacman`, `apt`, `dnf`, `zypper`).
  - Udev rule installer so non-root users never need `sudo`.
  - Native `.desktop` application menu integration and hi-res app icons.

---

## 🚀 Quick Start (Run Without Installing)

You can launch the GUI immediately without installing anything to system directories:

```bash
cd ~/Projects/gm333-gui
./run-gui.sh
```

---

## 📥 Installation on Any Linux Distro

Run the universal installer script:

```bash
cd ~/Projects/gm333-gui
sudo ./install.sh
```

### What `install.sh` does automatically:
1. **Detects your Linux distribution** and installs any missing runtime packages:
   - **Arch Linux**: `sudo pacman -S --needed python-gobject gtk3 libpulse python-pillow`
   - **Ubuntu / Debian / Mint / Pop!_OS**: `sudo apt-get install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 pulseaudio-utils python3-pil`
   - **Fedora / RHEL**: `sudo dnf install -y python3-gobject gtk3 pulseaudio-utils python3-pillow`
   - **openSUSE**: `sudo zypper install -y python3-gobject python3-gobject-Gdk gtk3 pulseaudio-utils python3-Pillow`
2. **Installs udev rule** (`/etc/udev/rules.d/99-ant-esports-gm333.rules`) for non-root hardware access and reloads `udevadm`.
3. **Installs application files** to `/opt/gm333-gui`.
4. **Installs global command** `gm333-gui` to `/usr/local/bin/gm333-gui`.
5. **Registers Desktop Entry** and high-resolution icons so you can search for **"Ant Esports GM333"** in your application launcher (GNOME, KDE Plasma, XFCE, Cinnamon, etc.).

---

## 🗑️ Uninstallation

To completely remove the app from your system:

```bash
cd ~/Projects/gm333-gui
sudo ./uninstall.sh
```

---

## 🛠️ CLI Tools Included

The companion command-line tools in `~/Projects/gm333-music-sync` remain fully functional for scripting or headless use:

```bash
# List all 16 hardware lighting modes
gm333-ctl list

# Set mode with custom speed, brightness, and color
gm333-ctl mode neon
gm333-ctl mode static --color '#00ffff'
gm333-ctl mode breathing --speed 3

# Run interactive terminal audio visualizer
gm333-ctl music -p cyberpunk -s 1.2
```

---

## 🔍 Hardware Specifications

| Property | Value |
|---|---|
| **Product** | Ant Esports GM333 Gaming Mouse |
| **USB Vendor ID** | `0x30fa` (Instant Microelectronics Corp.) |
| **USB Product ID** | `0x1440` |
| **HID Interface** | Interface 1 (`hidraw`) |
| **Feature Report ID** | `0x07` (8-byte control packets) |
| **Ioctl Code** | `HIDIOCSFEATURE_8` (`0xc0084806`) |
| **Audio Capture** | PulseAudio / PipeWire `parec` monitor sink stream |
