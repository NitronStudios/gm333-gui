# Release v1.0.0 — Official Linux Driver & AI Music Sync Engine

We are excited to announce the first major production release of **`gm333-gui`**, the native Linux driver and control center for the **Ant Esports GM333 Gaming Mouse** (`30fa:1440`).

This release provides complete Linux support, reverse-engineered USB HID communication, 16 hardware lighting modes, and an industry-grade **AI-powered Music Sync Engine** featuring real-time spectral flux FFT beat tracking.

---

## 🚀 Key Highlights

### 🧠 AI Beat Detection & Rhythm Prediction Engine
- **Fast Fourier Transform (FFT) Analysis**: 512-point spectral flux engine running in real-time with sub-millisecond audio overhead.
- **Dynamic Onset Thresholding**: Automatically adapts to ambient track volume and peaks without clipping or false triggers.
- **BPM Grid Phase Locking**: Autocorrelation-based tempo estimator locking LED pulses to true rhythmic cadences (60–180 BPM).
- **3-Band Frequency Reactive Tinting**:
  - **Bass / Sub-bass (<250 Hz)**: Drives core pulse intensity and tactile lighting hits.
  - **Mid-range (250 Hz - 2.5 kHz)**: Dynamically blends melodic warmth.
  - **Highs (>2.5 kHz)**: Shimmer highlights that accent hi-hats and snares.
- **Interactive GUI Toggle**: Turn AI mode on or off on the fly with live BPM readout.

### 🌈 16 Hardware Lighting Modes
Directly sets and latches onboard hardware registers across all 16 microcontroller routines:
- *Neon Wave, Cycle Breathing, Static Solid, Flowing Water, Mono Water, Comet Streak, Ambilight, Rhythmic Flicker, Star Trek, Water Ripple, Enraptured, Click Response, DPI Breathing, Color Stepper, Firmware Music Sync, and Complete LED Off*.
- Live Speed control (Levels 1–7) and Brightness control (Levels 0–4).
- 16 custom color palette swatches plus full RGB color selection.

### 🔇 Perfect Zero-Leak Silence Handling
- Mode 14 hardware off state automatically activated during silence and pauses.
- Zero white light leak, zero neon wave reversion during music playback.
- Dynamic amplitude scaling from 1 to 15 on sound playback.

### 🛡️ Non-Root Security & Universal Distro Support
- Udev rule (`99-ant-esports-gm333.rules`) provides 0666 permissions for non-root users.
- Universal `install.sh` supporting **Arch Linux**, **Ubuntu/Debian**, **Fedora**, and **openSUSE**.
- Desktop application menu integration with high-resolution icons.

---

## 📦 What's Changed
- Initial production release with full GUI and headless CLI compatibility.
- Reverse-engineered Instant Microelectronics 8-byte Feature Report protocol (`0x07`).
- Implemented real-time Cairo spectrum audio visualizer and stereo VU meter in GTK3.
- Integrated AI Beat Detection with numpy acceleration.

---

## 📥 Installation

```bash
git clone https://github.com/NitronStudios/gm333-gui.git
cd gm333-gui
sudo ./install.sh
```

Or download the release tarball below and extract.
