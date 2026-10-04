#!/usr/bin/env python3
"""
Threaded Audio Reactive Music Sync Engine for GM333.
Features:
- Pure direct software RGB lighting control with hardware off state machine
- In silence (loudness 0 / silence baseline 0): mouse uses Mode 14 (Completely OFF - ZERO LIGHT)
- When sound plays: mouse scales smoothly from level 1 (lowest sound) to level 15 (full sound)
- Automatic color cycling exclusively on musical beats with strict silence noise-gate
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

# Mode 3: Direct Static Color mode (active sound playback)
_B3_MODE3 = ((1 << 7) + (3 << 4) + 2) & 0xff
_B6_MODE3 = (((3 >> 3) << 7) + ((0x4002 >> 8) & 3)) & 0xff
PKT_INIT_DIRECT_SYNC = bytes([0x07, 0x13, 0x80, _B3_MODE3, 0x1b, 0, _B6_MODE3, 0x4002 & 0xff])

# Mode 14: Hardware LED OFF (true 0 brightness / zero light in silence)
_B3_MODE14 = ((1 << 7) + (14 << 4) + 2) & 0xff
_B6_MODE14 = (((14 >> 3) << 7) + ((0x4002 >> 8) & 3)) & 0xff
PKT_MODE_OFF = bytes([0x07, 0x13, 0x80, _B3_MODE14, 0x1b, 0, _B6_MODE14, 0x4002 & 0xff])

# Restore Mode 7: Neon Wave default
PKT_RESTORE_NEON = bytes([0x07, 0x13, 0x80, 0xf2, 0x1b, 0x00, 0x00, 0x02])

class MusicSyncEngine:
    def __init__(self, controller, on_update_callback=None):
        self.controller = controller
        self.on_update = on_update_callback
        self.is_running = False
        self.thread = None
        self.stop_event = threading.Event()

        # Configurable params
        self.palette_name = "cyberpunk"
        self.sensitivity = 1.0
        self.fps = 30
        self.min_brightness = 0.0  # 0.0 = completely dark/off in silence
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
            return
        self.stop_event.clear()
        self.is_running = True
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def stop(self):
        """Stops the audio reactive visualizer thread."""
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
            # Start in Mode 14 (Completely Off) if starting in silence
            is_hardware_off = True
            fcntl.ioctl(fd, HIDIOCSFEATURE_8, PKT_MODE_OFF)
            time.sleep(0.03)

            color_idx = 0
            noise_floor = 120.0
            peak_ceiling = 2500.0
            last_send_time = 0
            last_beat_time = 0
            prev_rms = 0.0
            smooth_norm = 0.0
            energy_fast = 0.0
            energy_slow = 0.0

            last_r, last_g, last_b = -1, -1, -1

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

                        # Silence Gate (Noise Floor Tracking)
                        if rms > 60:
                            noise_floor = (noise_floor * 0.98) + (min(rms, noise_floor) * 0.02)
                            if rms > peak_ceiling:
                                peak_ceiling = (peak_ceiling * 0.70) + (rms * 0.30)
                            else:
                                peak_ceiling = max(800.0, peak_ceiling * 0.999)
                        else:
                            noise_floor = 120.0

                        sens = self.sensitivity
                        eff_floor = max(80.0, noise_floor / sens)
                        eff_ceiling = max(eff_floor + 400.0, peak_ceiling / sens)

                        # True normalized audio volume (0.0 to 1.0)
                        if rms <= eff_floor:
                            norm = 0.0
                        else:
                            norm = max(0.0, min(1.0, (rms - eff_floor) / (eff_ceiling - eff_floor)))

                        # Advanced Beat Detection with STRICT Silence / Noise Gate
                        delta = rms - prev_rms
                        energy_fast = (energy_fast * 0.55) + (rms * 0.45)
                        energy_slow = (energy_slow * 0.95) + (rms * 0.05)

                        beat_thresh = 1.25 / sens
                        delta_thresh = 200.0 / sens
                        is_beat = False

                        # NEVER trigger beat if silent or low ambient level
                        if rms > 140.0 and norm > 0.30:
                            if (now - last_beat_time) > 0.18:
                                if (energy_fast > (energy_slow * beat_thresh) and delta > delta_thresh) or (norm > 0.82 and delta > 240.0):
                                    is_beat = True
                                    last_beat_time = now

                        prev_rms = rms

                        # Get current color palette
                        palette_info = PALETTES.get(self.palette_name, PALETTES["cyberpunk"])
                        palette_colors = palette_info["colors"]

                        # Cycle color ONLY when a genuine beat triggers and music is actively playing
                        if is_beat and self.color_on_beat and norm > 0.25:
                            color_idx = (color_idx + 1) % len(palette_colors)
                            # Instant beat burst
                            smooth_norm = max(smooth_norm, min(1.0, norm + 0.30))

                        # Loudness tracking for Brightness (fast attack, smooth musical decay)
                        if norm <= 0.01:
                            smooth_norm = smooth_norm * 0.75
                            if smooth_norm < 0.01:
                                smooth_norm = 0.0
                        elif norm > smooth_norm:
                            smooth_norm = (smooth_norm * 0.20) + (norm * 0.80)
                        else:
                            smooth_norm = (smooth_norm * 0.85) + (norm * 0.15)

                        # Effective brightness calculation
                        if smooth_norm <= 0.005:
                            brightness = self.min_brightness
                        else:
                            perceptual = smooth_norm ** 0.85
                            brightness = self.min_brightness + (1.0 - self.min_brightness) * perceptual
                        brightness = max(0.0, min(1.0, brightness))

                        # Silence check: when silence baseline is 0 and volume is 0
                        is_silent = (smooth_norm <= 0.005) and (self.min_brightness <= 0.01)

                        # Active palette color
                        r_base, g_base, b_base = palette_colors[color_idx % len(palette_colors)]

                        min_interval = 1.0 / max(15, min(self.fps, 45))
                        if (now - last_send_time) >= min_interval:
                            last_send_time = now

                            if is_silent:
                                # Switch to Mode 14 (Completely OFF - ZERO LIGHT, NO WHITE)
                                if not is_hardware_off:
                                    try:
                                        fcntl.ioctl(fd, HIDIOCSFEATURE_8, PKT_MODE_OFF)
                                    except Exception:
                                        pass
                                    is_hardware_off = True
                                    last_r, last_g, last_b = -1, -1, -1
                            else:
                                # Playing sound: ensure mouse is in Mode 3 (Direct Static RGB)
                                if is_hardware_off:
                                    try:
                                        fcntl.ioctl(fd, HIDIOCSFEATURE_8, PKT_INIT_DIRECT_SYNC)
                                    except Exception:
                                        pass
                                    is_hardware_off = False
                                    time.sleep(0.01)

                                # Scale color from 1 (lowest sound) to 15 (full sound)
                                r_out = max(1 if r_base > 0 else 0, min(15, int(round(r_base * brightness))))
                                g_out = max(1 if g_base > 0 else 0, min(15, int(round(g_base * brightness))))
                                b_out = max(1 if b_base > 0 else 0, min(15, int(round(b_base * brightness))))

                                if (r_out, g_out, b_out) != (last_r, last_g, last_b) or is_beat:
                                    last_r, last_g, last_b = r_out, g_out, b_out
                                    for zone in range(8):
                                        pkt_rgb = bytes([0x07, 0x14, (zone << 5) | (r_out & 0x0f), ((g_out & 0x0f) << 4) | (b_out & 0x0f), 0, 0, 0, 0])
                                        try:
                                            fcntl.ioctl(fd, HIDIOCSFEATURE_8, pkt_rgb)
                                        except Exception:
                                            pass

                        # Notify UI
                        base_hex = nibbles_to_hex(r_base, g_base, b_base)
                        self.current_rms = rms
                        self.current_norm = smooth_norm
                        self.current_brightness = 0.0 if is_silent else brightness
                        self.current_color = (r_base, g_base, b_base)
                        self.current_color_hex = base_hex
                        self.is_beat = is_beat

                        status_str = "Active (Syncing)" if not is_silent else "Active (Silent - Off)"
                        self._notify_gui(rms, smooth_norm, 0.0 if is_silent else brightness, is_beat, status_str, (r_base, g_base, b_base), base_hex)

                finally:
                    proc.terminate()
                    try:
                        proc.wait(timeout=0.5)
                    except Exception:
                        proc.kill()

        finally:
            # Restore default neon wave on exit
            try:
                fcntl.ioctl(fd, HIDIOCSFEATURE_8, PKT_RESTORE_NEON)
            except Exception:
                pass
            try:
                os.close(fd)
            except Exception:
                pass
            self.is_running = False
