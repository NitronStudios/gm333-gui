#!/usr/bin/env python3
"""
Ant Esports GM333 Native Linux Music Sync Visualizer Engine.
Features:
- Firmware-native Mode 3 music sync engine
- Smooth brightness scaling: dim at low volume, bright at peak
- Beat-triggered color cycling across palette
- Hardware Mode 14 LED off during sustained silence
- Real-time visualization telemetry sent to GTK GUI
"""

import os
import sys
import time
import math
import struct
import fcntl
import threading
import subprocess
from gi.repository import GLib

from .utils import PALETTES, HIDIOCSFEATURE_8, nibbles_to_hex

# Mode 3 = Firmware-native Direct Sync mode (music sync engine)
# B3 = 0x80 | (3<<4) | 0 = 0xb2; B6 = 0x00 (mode 3 < 8)
PKT_INIT_SYNC    = bytes([0x07, 0x13, 0x80, 0xb2, 0x1b, 0x00, 0x00, 0x02])

# Mode 14 = Turn LEDs Off (hardware kill for silence)
# B3 = 0x62; B6 = 0x80 (mode 14 >= 8)
PKT_MODE_OFF     = bytes([0x07, 0x13, 0x80, 0x62, 0x1b, 0x00, 0x80, 0x02])

# Mode 6: Neon Wave (ambient restore on shutdown)
PKT_RESTORE_NEON = bytes([0x07, 0x13, 0xff, 0xe2, 0x1b, 0x04, 0x00, 0x02])

# Volume-to-firmware-level table: index 0=quiet, 9=loud → code 7=quiet, 0=loudest
LEVEL_CODES = [7, 5, 5, 4, 4, 3, 3, 2, 2, 0]


class MusicSyncEngine:
    def __init__(self, controller, on_update_callback=None):
        self.controller = controller
        self.on_update = on_update_callback
        self.is_running = False
        self.thread = None
        self.stop_event = threading.Event()

        # Configurable params
        self.palette_name = "cyberpunk"
        self.palette_changed = False
        self.sensitivity = 1.0
        self.fps = 30
        self.min_brightness = 0.0  # 0.0 = turn off in silence
        self.color_on_beat = True
        self.target_sink = None

        # Live telemetry
        self.current_sink_name = "Detecting..."
        self.current_rms = 0.0
        self.current_norm = 0.0
        self.current_brightness = 0.0
        self.current_color = (0, 15, 15)  # Cyan default
        self.current_color_hex = "#00ffff"
        self.is_beat = False
        self.status_text = "Idle"

    def set_palette(self, name):
        if name in PALETTES:
            self.palette_name = name
            self.palette_changed = True

    def set_sensitivity(self, val):
        self.sensitivity = max(0.1, min(5.0, float(val)))

    def set_fps(self, val):
        self.fps = max(15, min(45, int(val)))

    def set_min_brightness(self, val):
        self.min_brightness = max(0.0, min(0.5, float(val)))

    def set_color_on_beat(self, enabled):
        self.color_on_beat = bool(enabled)

    def get_audio_sinks(self):
        """Lists available audio output monitor sinks."""
        sinks = []
        try:
            out = subprocess.check_output(["pactl", "list", "short", "sinks"], stderr=subprocess.DEVNULL).decode()
            for line in out.strip().split("\n"):
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[1]
                    sinks.append(name)
        except Exception:
            pass
        return sinks

    def get_default_monitor(self):
        """Finds current default audio output monitor sink."""
        try:
            sink = subprocess.check_output(["pactl", "get-default-sink"], stderr=subprocess.DEVNULL).decode().strip()
            if sink:
                return f"{sink}.monitor", sink
        except Exception:
            pass
        return None, None

    def start(self):
        """Starts the audio reactive visualizer thread."""
        if self.is_running:
            self.stop()
        self.stop_event.clear()
        self.is_running = True
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def stop(self, restore_neon=True):
        """Stops the audio reactive visualizer thread."""
        self.restore_neon_on_stop = restore_neon
        if not self.is_running:
            return
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.5)
        self.is_running = False
        self.status_text = "Stopped"
        self._notify_gui(0.0, 0.0, 0.0, False, "Stopped", (0, 0, 0), "#000000")

    def _notify_gui(self, rms, norm, brightness, is_beat, status, color_rgb, color_hex):
        if self.on_update:
            GLib.idle_add(self.on_update, rms, norm, brightness, is_beat, status, self.current_sink_name, color_rgb, color_hex)

    def _worker(self):
        """Background streaming worker loop."""
        fd = self.controller.open_device()
        if fd is None:
            self.status_text = "Failed to open mouse device"
            self.is_running = False
            self._notify_gui(0.0, 0.0, 0.0, False, self.status_text, (0, 0, 0), "#000000")
            return

        try:
            # Enter Mode 3 (firmware-native music sync engine) — no commit needed
            fcntl.ioctl(fd, HIDIOCSFEATURE_8, PKT_INIT_SYNC)
            time.sleep(0.04)

            # Send initial palette color to all 8 zones
            palette_info = PALETTES.get(self.palette_name, PALETTES["cyberpunk"])
            palette_colors = palette_info["colors"]
            init_r, init_g, init_b = palette_colors[0]
            for z in range(8):
                fcntl.ioctl(fd, HIDIOCSFEATURE_8, bytes([0x07, 0x14,
                                                          (z << 5) | (init_r & 0x0f),
                                                          ((init_g & 0x0f) << 4) | (init_b & 0x0f),
                                                          0, 0, 0, 0]))

            color_idx = 0
            noise_floor = 150.0
            peak_ceiling = 12000.0
            last_send_time = 0
            last_beat_time = 0
            prev_rms = 0.0
            smooth_norm = 0.0
            no_sound_ticks = 0
            energy_fast = 0.0
            energy_slow = 0.0
            is_hardware_off = False

            while not self.stop_event.is_set():
                # Detect active audio sink
                monitor, sink_simple = self.get_default_monitor()
                if not monitor:
                    self.current_sink_name = "Waiting for audio device..."
                    self.status_text = "No active audio sink found"
                    self._notify_gui(0.0, 0.0, 0.0, False, self.status_text, (0, 0, 0), "#000000")
                    time.sleep(1.0)
                    continue

                self.current_sink_name = sink_simple or monitor
                self.status_text = "Listening to audio..."

                # Start low-latency parec process on monitor sink
                cmd = ["parec", "-d", monitor, "--format=s16le", "--channels=1", "--rate=22050", "--latency-msec=25"]
                try:
                    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                except Exception:
                    cmd = ["parec", "-d", monitor, "--format=s16le", "--channels=1", "--rate=22050"]
                    try:
                        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                    except Exception as e:
                        self.status_text = f"Audio capture error: {e}"
                        self._notify_gui(0.0, 0.0, 0.0, False, self.status_text, (0, 0, 0), "#000000")
                        time.sleep(2.0)
                        continue

                chunk_samples = 512
                chunk_bytes = chunk_samples * 2

                try:
                    while not self.stop_event.is_set():
                        raw = proc.stdout.read(chunk_bytes)
                        if not raw or len(raw) < chunk_bytes:
                            time.sleep(0.01)
                            new_mon, _ = self.get_default_monitor()
                            if new_mon != monitor:
                                break
                            continue

                        samples = struct.unpack(f"<{chunk_samples}h", raw)
                        sum_sq = sum(s * s for s in samples)
                        rms = math.sqrt(sum_sq / chunk_samples)

                        now = time.time()

                        # Sound / silence tracking
                        if rms > 50:
                            no_sound_ticks = 0
                        else:
                            no_sound_ticks += 1

                        # Dynamic Automatic Gain Control (AGC)
                        if rms > 50:
                            noise_floor = (noise_floor * 0.98) + (min(rms, noise_floor) * 0.02)
                            if rms > peak_ceiling:
                                peak_ceiling = (peak_ceiling * 0.70) + (rms * 0.30)
                            else:
                                peak_ceiling = max(800.0, peak_ceiling * 0.999)

                        sens = self.sensitivity
                        eff_floor = max(80.0, noise_floor / sens)
                        eff_ceiling = max(eff_floor + 400.0, peak_ceiling / sens)
                        norm = max(0.0, min(1.0, (rms - eff_floor) / (eff_ceiling - eff_floor)))

                        # Reload palette if user switched it in GUI
                        if self.palette_changed:
                            self.palette_changed = False
                            palette_info = PALETTES.get(self.palette_name, PALETTES["cyberpunk"])
                            palette_colors = palette_info["colors"]
                            color_idx = 0

                        # Beat detection — tight thresholds to avoid false triggers
                        delta = rms - prev_rms
                        energy_fast = (energy_fast * 0.55) + (rms * 0.45)
                        energy_slow = (energy_slow * 0.95) + (rms * 0.05)
                        is_beat = False

                        beat_thresh = 1.40 / sens
                        delta_thresh = 300.0 / sens

                        if rms > 200.0 and norm > 0.40 and (now - last_beat_time) > 0.25:
                            if (energy_fast > (energy_slow * beat_thresh) and delta > delta_thresh) or (norm > 0.85 and delta > 350.0):
                                is_beat = True
                                last_beat_time = now
                                if self.color_on_beat:
                                    color_idx = (color_idx + 1) % len(palette_colors)

                        prev_rms = rms

                        # Smooth loudness tracking
                        if norm <= 0.01:
                            smooth_norm = smooth_norm * 0.75
                            if smooth_norm < 0.01:
                                smooth_norm = 0.0
                        elif norm > smooth_norm:
                            smooth_norm = (smooth_norm * 0.20) + (norm * 0.80)
                        else:
                            smooth_norm = (smooth_norm * 0.85) + (norm * 0.15)

                        # Effective brightness (respect min_brightness setting)
                        if self.min_brightness > 0.01:
                            eff = self.min_brightness + (1.0 - self.min_brightness) * min(1.0, smooth_norm ** 0.75)
                        else:
                            eff = min(1.0, smooth_norm ** 0.75)

                        brightness = eff

                        # Throttled LED updates
                        min_interval = 1.0 / max(15, min(self.fps, 35))
                        if (now - last_send_time) >= min_interval:
                            last_send_time = now

                            try:
                                if no_sound_ticks > 40 and self.min_brightness <= 0.01:
                                    # SILENCE: Mode 14 hardware LED off (once on transition)
                                    if not is_hardware_off:
                                        fcntl.ioctl(fd, HIDIOCSFEATURE_8, PKT_MODE_OFF)
                                        is_hardware_off = True
                                else:
                                    # ACTIVE: brightness-scaled direct color streaming
                                    if is_hardware_off:
                                        # Wake up: re-enter Mode 3
                                        fcntl.ioctl(fd, HIDIOCSFEATURE_8, PKT_INIT_SYNC)
                                        time.sleep(0.03)
                                        is_hardware_off = False

                                    r_base, g_base, b_base = palette_colors[color_idx % len(palette_colors)]

                                    # Scale brightness 0..15 by eff (perceptual curve)
                                    r_s = max(0, min(15, int(round(r_base * eff))))
                                    g_s = max(0, min(15, int(round(g_base * eff))))
                                    b_s = max(0, min(15, int(round(b_base * eff))))
                                    if r_base > 0 and r_s == 0 and eff > 0.02: r_s = 1
                                    if g_base > 0 and g_s == 0 and eff > 0.02: g_s = 1
                                    if b_base > 0 and b_s == 0 and eff > 0.02: b_s = 1

                                    # Send scaled color to all 8 zones every frame
                                    for z in range(8):
                                        fcntl.ioctl(fd, HIDIOCSFEATURE_8, bytes([0x07, 0x14,
                                                                                  (z << 5) | (r_s & 0x0f),
                                                                                  ((g_s & 0x0f) << 4) | (b_s & 0x0f),
                                                                                  0, 0, 0, 0]))

                                    # Sound level hint to keep Mode 3 engine alive
                                    lvl_idx = min(9, int(smooth_norm * 9.99))
                                    lvl_code = LEVEL_CODES[lvl_idx]
                                    fcntl.ioctl(fd, HIDIOCSFEATURE_8,
                                                bytes([0x07, 0x13, 0x80, 0xa1, 0x1b, lvl_code, 0x03, 0xff]))

                            except Exception:
                                pass

                        # Update live telemetry for GUI
                        r_cur, g_cur, b_cur = palette_colors[color_idx % len(palette_colors)]
                        base_hex = nibbles_to_hex(r_cur, g_cur, b_cur)
                        self.current_rms = rms
                        self.current_norm = smooth_norm
                        self.current_brightness = brightness
                        self.current_color = (r_cur, g_cur, b_cur)
                        self.current_color_hex = base_hex
                        self.is_beat = is_beat

                        status_str = "Active (Syncing)" if brightness > 0.01 else "Active (Silent - Off)"
                        self._notify_gui(rms, smooth_norm, brightness, is_beat, status_str, (r_cur, g_cur, b_cur), base_hex)

                finally:
                    proc.terminate()
                    try:
                        proc.wait(timeout=0.5)
                    except Exception:
                        proc.kill()

        finally:
            # Restore default neon wave on exit only if requested
            if getattr(self, "restore_neon_on_stop", True):
                try:
                    fcntl.ioctl(fd, HIDIOCSFEATURE_8, PKT_RESTORE_NEON)
                    time.sleep(0.01)
                    self.controller.commit_config(fd)
                except Exception:
                    pass
            try:
                os.close(fd)
            except Exception:
                pass
            self.is_running = False
