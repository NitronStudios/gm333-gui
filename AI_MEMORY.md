# AI Memory — Ant Esports GM333 Linux Driver & Music Sync Project
> Last updated: 2026-10-04 | Maintained by Antigravity AI

---

## 👤 User & Environment Info
- **User**: prince
- **Machine**: Arch Linux (Kernel Linux 6.x), Wayland session
- **Sudo credentials**: `pplp`
- **Primary Audio Output**: Bluetooth earbuds / headphones (`bluez_output.35_B9_03_FC_4A_03.1`)
- **Target Mouse**: Ant Esports GM333 Gaming Mouse (`30fa:1440` Instant Microelectronics controller)
- **Projects**:
  - `/home/prince/Projects/gm333-gui` (GTK3 Python Desktop Application, installed to `/opt/gm333-gui`)
  - `/home/prince/Projects/gm333-music-sync` (Lightweight Python CLI visualizer & systemd service)

---

## 🖱️ Hardware & Protocol Specifications (Reverse-Engineered)

### USB HID Interfaces
- **Vendor ID**: `30fa` | **Product ID**: `1440`
- **/dev/hidraw0** (Interface 0): Mouse motion and standard buttons (66-byte descriptor).
- **/dev/hidraw1** (Interface 1): Vendor-defined Feature Report interface (Usage Page `0xff01`, Usage `0x01`, 140-byte descriptor).
- **Report ID**: `0x07` (8-byte feature reports via `HIDIOCSFEATURE_8 = 0xc0084806`).

### Protocol Subcommands (Report ID `0x07`)
### Protocol Subcommands (Report ID `0x07`)
| Subcommand | Function | Description |
|---|---|---|
| `0x10` | Key Mapping | Configures button assignments per profile |
| `0x11` | DPI Configuration | Configures DPI stages, sensitivity levels, and indicator colors |
| `0x13` | Lighting Mode | Sets active lighting mode, speed, and brightness |
| `0x14` | Color Streaming | Streams 4-bit nibble RGB colors to zones 0..7 |
| `0x17` | CRC / Checksum | Firmware checksum validation packet |
| `0x18` | Hardware Latch / Commit | **Mandatory** two-packet commit handshake to latch registers (`0x10` strobe then `0x00` clear) |
| `0x20` | Factory Reset | Restores hardware defaults |

### Hardware Lighting Mode IDs (0-Indexed Firmware Registers)
Reverse-engineered from `0x44d920` and `0x43cfe0` in `GM333 Setup.exe`:
| ID | Mode Name | Description | Color Support | Single/Cycle |
|---|---|---|---|---|
| `0` | DPI Breathing | Breathes according to current hardware DPI preset level | No | Cycle (`0xff`) |
| `1` | Cycle Breathing | Smoothly pulses through all RGB spectrum colors | No | Cycle (`0xff`) |
| `2` | Static Solid / Light On | Steady solid glow with custom 4-bit RGB color | Yes | Single (`0x80`) |
| `3` | Flowing Water | Continuous directional wave streaming through LED channels | No | Cycle (`0xff`) |
| `4` | Mono Water | Single-color directional flowing wave pulse | Yes | Single (`0x80`) |
| `5` | Comet Streak | High-speed light trail streaking across the chassis | No | Cycle (`0xff`) |
| `6` | Neon Wave | Default smooth multi-color vibrant rainbow wave | No | Cycle (`0xff`) |
| `7` | Ambilight | Dynamic ambient glow subtly changing hues | No | Cycle (`0xff`) |
| `8` | Rhythmic Flicker | Dynamic rhythmic flickering strobe effect | No | Cycle (`0xff`) |
| `9` | Star Trek | Moving warp stars pulsating across opposite zones | No | Cycle (`0xff`) |
| `10` | Water Ripple | Expansive ripple radiating like a water droplet | No | Cycle (`0xff`) |
| `11` | Enraptured | Multi-phase wave dancing across opposite flanks | No | Cycle (`0xff`) |
| `12` | Click Response | Illuminates dynamically in response to mouse clicks | No | Cycle (`0xff`) |
| `13` | Turn LEDs Off | Completely turns off all onboard LEDs | No | Single (`0x80`) |

### Report 0x13 Mode Packet Encoding (0x44a570 & 0x476c90)
- **Byte 0**: `0x07` (Report ID)
- **Byte 1**: `0x13` (Subcommand)
- **Byte 2**: `0x80` for single-color modes (`2, 4, 13`), `0xff` for 7-color cycling modes
- **Byte 3**: `0x80 | ((led_type & 0x07) << 4) | (speed & 0x07)`
- **Byte 4**: `0x1b` (Direction right: `0x10 | 0x0b`)
- **Byte 5**: `brightness & 0x07` (0 to 4, where 4 is maximum brightness)
- **Byte 6**: `0x80` if `led_type >= 8` (bit 3 of `led_type` shifted to bit 7), else `0x00`
- **Byte 7**: `0x02`

### Report 0x14 Color Packet Encoding (0x44a370)
- **Byte 0**: `0x07` (Report ID)
- **Byte 1**: `0x14` (Subcommand)
- **Byte 2**: `(zone << 5) | (Green & 0x0f)`
- **Byte 3**: `((Red & 0x0f) << 4) | (Blue & 0x0f)`
- **Bytes 4..7**: `0x00`

### Critical Music Sync Rules
1. **NEVER send Report 0x13 in the audio frame loop**:
   Sending Report `0x13` resets the hardware sequencer every frame, causing the microcontroller to flash its default DPI Stage 3 LED (Blue) and aborting Report `0x14` RGB rendering.
   Report `0x13` Mode 2 (`0x07, 0x13, 0x80, 0xa0, 0x1b, 0x04, 0x00, 0x02`) is sent **only once** at worker startup.
2. **Inside the 30 FPS audio loop**:
   Only send Report `0x14` (for zones 0..7) + Report `0x18` (Commit Handshake).
3. **Guaranteed 100% Pitch Black in Silence**:
   - At startup and when entering silence (`eff_norm <= 0.01` or `silent_ticks >= 3`): send `(0, 0, 0)` to zones 0..7 + Commit.
   - When silent, skip packet sending to eliminate CPU and USB bus overhead while keeping LEDs 100% off.
4. **Responsive Beat Color Transitions**:
   On rhythmic energy spikes, advance `color_idx` in active palette and apply a brightness boost.

---

## 📌 Preferences & Constraints
- **Strictly do NOT use phone camera / ADB**: Rely solely on direct user reports.
- **Music Reactive Dynamics**:
  - In silence / 0 volume: mouse light must cleanly turn completely off (0 brightness / pitch black).
  - On sound: smoothly scale brightness up to full on peak loudness.
  - On musical beats: advance color palette if color cycling is enabled.

