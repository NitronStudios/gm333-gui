<div align="center">

# 🖱️ Detox Open Mouse Drivers

**Universal Open-Source Linux Hardware Driver & AI Music Sync Suite for Gaming Mice**

[![Release](https://img.shields.io/badge/release-v1.0.0-blue.svg?style=for-the-badge)](https://github.com/NitronStudios/detox-open-mouse-drivers/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Platform](https://img.shields.io/badge/platform-Linux-FCC624.svg?style=for-the-badge&logo=linux&logoColor=black)](https://kernel.org)
[![GTK3](https://img.shields.io/badge/UI-GTK%203%20%2B%20Cairo-4E9A06.svg?style=for-the-badge&logo=gnome&logoColor=white)](https://gtk.org)

<p align="center">
  <b>Firmware-Native Mode Control</b> • <b>AI Spectral Flux Beat Detection</b> • <b>Real-time PulseAudio / PipeWire Audio Reactive Lighting</b> • <b>Universal Cross-Distro Installer</b>
</p>

</div>

---

## 📖 Overview

**Detox Open Mouse Drivers** is a native, high-performance Linux driver and modern GTK3 control panel for gaming mice powered by Instant Microelectronics controllers (including the popular **Ant Esports GM333**, USB ID `30fa:1440`).

While proprietary vendor software is strictly locked to Windows, **Detox Open Mouse Drivers** delivers complete hardware control natively on Linux built entirely by reverse-engineering the onboard USB HID communication protocol.

It provides instant hardware register control, 16 onboard lighting modes, and an **AI-powered audio visualizer engine** that turns your mouse LEDs into a dynamic, music-reactive light show with zero perceptible latency.

---

## ✨ Features

### 🧠 AI Beat Detection & Rhythm Engine
- **FFT Spectral Flux Analysis**: Fast Fourier Transform on 512-point audio frames to identify rhythmic onset energy rates.
- **Adaptive Energy Thresholding**: Auto-scales sensitivity to match the volume and dynamics of any music genre.
- **BPM Grid Phase Locking**: Autocorrelation-based tempo prediction (60–180 BPM) that keeps pulse triggers locked to the beat.
- **Multi-Band Frequency Tinting**:
  - 💥 **Sub-Bass / Bass (< 250 Hz)**: Drives low-end impact & pulse brightness.
  - 🎸 **Midrange (250 Hz – 2.5 kHz)**: Modulates melodic presence and color warmth.
  - ✨ **Highs / Treble (> 2.5 kHz)**: Adds shimmer and dynamic sparkle highlights.
- **Live BPM Badge**: Real-time tempo estimation displayed in the interface.

### 🌈 16 Onboard Hardware Lighting Modes
Directly latches firmware registers across all 16 built-in lighting routines:
1. **Neon Wave** *(Default smooth multi-color vibrant rainbow wave)*
2. **Cycle Breathing** *(Smooth pulsing through all RGB spectrum colors)*
3. **Static Solid** *(Custom steady solid glow with 16-color palette or RGB picker)*
4. **Flowing Water** *(Continuous directional wave streaming through zones)*
5. **Mono Water** *(Single-color directional flowing wave pulse)*
6. **Comet Streak** *(High-speed light trail streaking across chassis)*
7. **Ambilight** *(Dynamic ambient glow subtly shifting hues)*
8. **Rhythmic Flicker** *(Dynamic rhythmic flickering strobe effect)*
9. **Star Trek** *(Moving warp stars pulsating across opposite zones)*
10. **Water Ripple** *(Expansive ripple radiating outwards)*
11. **Enraptured** *(Multi-phase wave dancing across opposite flanks)*
12. **Click Response** *(Illuminates dynamically on mouse clicks)*
13. **Turn LEDs Off** *(Full hardware power-down)*
14. **DPI Breathing** *(Breathes according to current hardware DPI preset level)*
15. **Color Stepper** *(Step-by-step chromatic cycle)*
16. **Music Sync Mode** *(Firmware-native audio reactive mode)*

### 🔇 Pitch-Black Silence & Audio Reactivity
- **Instant Silence Sleep**: Drops cleanly to 0% brightness (hardware sleep) during pauses or track transitions. Zero background white light leak, zero neon wave fallback.
- **Volume Scaling**: Smoothly scales brightness from 1 to 15 proportional to audio amplitude.
- **10 Curated Color Palettes**: *Cyberpunk Neon, Vivid Rainbow, Sunset Synthwave, Deep Ocean, Blazing Fire, Matrix Emerald, Vaporwave, Electric Purple, Toxic Lime, and Monochromatic Ice*.
- **Universal Audio Sink Monitor**: Listens directly to PipeWire / PulseAudio monitor streams. Fully compatible with **Bluetooth earbuds / headphones**, USB DACs, and internal laptop speakers.

### 🛡️ Non-Root Security (No Sudo Needed)
- Ships with an automated **udev rule** (`99-ant-esports-gm333.rules`) granting permission to interface 1 (`hidraw`) for non-root users.
- Never runs audio capture or GUI as root, protecting user session security and audio daemon sockets.

---

## 🚀 Quick Start

### Option 1: Universal Installer (Recommended)

Clone the repository and run the installer:

```bash
git clone https://github.com/NitronStudios/detox-open-mouse-drivers.git
cd detox-open-mouse-drivers
sudo ./install.sh
```

The installer automatically:
1. Detects your distribution (`Arch`, `Ubuntu`, `Debian`, `Fedora`, `openSUSE`) and installs required packages (`gtk3`, `python-gobject`, `numpy`, `libpulse`, `python-pillow`).
2. Configures the `/etc/udev/rules.d/` permissions.
3. Installs binaries to `/opt/gm333-gui` and symlinks `detox-mouse` and `gm333-gui` to `/usr/local/bin`.
4. Registers desktop menu entries and high-resolution icons.

Launch the app anytime from your application menu or by running:
```bash
detox-mouse
# or:
gm333-gui
```

### Option 2: Run Without Installing (Portable)

```bash
cd detox-open-mouse-drivers
./run-gui.sh
```

---

## 📦 Distribution Packages

If installing dependencies manually:

### Arch Linux / Manjaro / EndeavourOS
```bash
sudo pacman -S --needed python-gobject gtk3 libpulse python-pillow python-numpy
```

### Ubuntu / Debian / Linux Mint / Pop!_OS
```bash
sudo apt-get update
sudo apt-get install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 pulseaudio-utils python3-pil python3-numpy
```

### Fedora / RHEL
```bash
sudo dnf install -y python3-gobject gtk3 pulseaudio-utils python3-pillow python3-numpy
```

### openSUSE (Tumbleweed / Leap)
```bash
sudo zypper install -y python3-gobject python3-gobject-Gdk gtk3 pulseaudio-utils python3-Pillow python3-numpy
```

---

## 🔬 Protocol & Hardware Specifications

The GM333 features an **Instant Microelectronics (`30fa:1440`)** controller with two HID interfaces:
- `/dev/hidraw0` (Interface 0): Standard mouse pointer and button events.
- `/dev/hidraw1` (Interface 1): Vendor-defined Feature Report interface (Usage Page `0xff01`, Usage `0x01`).

### Reverse-Engineered USB HID Feature Reports (Report ID `0x07`)

All commands are 8-byte packets sent via `ioctl(fd, HIDIOCSFEATURE_8, packet)`:

| Command Byte | Function | Description |
|---|---|---|
| `0x10` | Key Mapping | Configures button assignments per profile |
| `0x11` | DPI Configuration | Configures DPI stages (800–7200) and indicator colors |
| `0x13` | Lighting Mode | Sets mode, animation speed (1–7), and brightness (0–4) |
| `0x14` | Zone RGB Streaming | Streams 4-bit nibble RGB colors to zones 0..7 |
| `0x17` | Checksum / CRC | Validates packet integrity |
| `0x18` | Hardware Latch | Two-step handshake (`0x10` strobe, `0x00` release) to latch settings |
| `0x20` | Factory Reset | Restores hardware defaults |

### Packet Formats

#### 1. Lighting Mode Packet (`0x13`)
```
[0x07, 0x13, type_flag, (0x80 | (mode_id & 0x07) << 4 | speed), 0x1b, brightness, ext_mode, 0x02]
```
- `type_flag`: `0x80` for single-color modes, `0xff` for 7-color cycling modes.
- `ext_mode`: `0x80` if `mode_id >= 8`, else `0x00`.

#### 2. Zone Color Packet (`0x14`)
```
[0x07, 0x14, (zone << 5) | (Green & 0x0f), ((Red & 0x0f) << 4) | (Blue & 0x0f), 0x00, 0x00, 0x00, 0x00]
```
- Zone index: `0` to `7`.
- Colors: 4-bit nibble per channel (`0` to `15`).

---

## 🗂️ Project Architecture

```
gm333-gui/
├── assets/                  # High-resolution icons & CSS stylesheets
├── gm333gui/                # Python core application package
│   ├── ai_beat.py           # 🧠 FFT spectral flux & BPM grid prediction engine
│   ├── app.py               # Main GTK3 window & tab controller
│   ├── controller.py        # USB HID device discovery & raw packet transmitter
│   ├── music_sync.py        # Real-time audio capture & LED renderer thread
│   ├── ui_lighting.py       # Hardware mode selection & color picker UI
│   ├── ui_music.py          # Music sync visualizer tab with live Cairo VU meter
│   ├── ui_info.py           # Hardware specs & diagnostics tab
│   └── utils.py             # Palette matrices, hex helpers, and constants
├── packaging/
│   ├── 99-ant-esports-gm333.rules # Linux udev rule (0666 permissions)
│   └── gm333-gui.desktop    # XDG Desktop Application entry
├── install.sh               # Universal distro auto-installer
├── uninstall.sh             # System clean removal script
├── run-gui.sh               # Local portable launch script
├── setup.py                 # Setuptools build configuration
└── pyproject.toml           # PEP 621 packaging metadata
```

---

## ❓ Troubleshooting

<details>
<summary><b>1. Mouse not detected or "Permission Denied" error</b></summary>

Make sure the udev rule is installed and your user account has access:
```bash
sudo cp packaging/99-ant-esports-gm333.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```
Unplug and replug the mouse USB cable. Verify `/dev/hidraw*` permissions show `crw-rw-rw-`.
</details>

<details>
<summary><b>2. Why should I never run `gm333-gui` or `gm333-music-sync` with `sudo`?</b></summary>

PulseAudio and PipeWire run within your unprivileged user session. Running an audio capture application with `sudo` can cause the audio daemon to re-assign socket ownership (`/run/user/1000/pulse`) to root, muting audio across your entire desktop session. Always run without `sudo` — the included udev rule handles all hardware permissions!
</details>

---

## 🤝 Contributing

Contributions, bug reports, and hardware testing feedback are welcome!
1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for more information.

---

<div align="center">
  Crafted with ❤️ by <b><a href="https://github.com/NitronStudios">NitronStudios</a></b> (<a href="https://github.com/xCaptaiN09">@xCaptaiN09</a>) & the open-source Linux community.
</div>
