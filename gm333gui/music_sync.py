#!/usr/bin/env python3
"""
Ant Esports GM333 Native Linux Music Sync Visualizer Engine.
Features:
- Native Hardware Music Sync (Mode 12) with full audio reactivity
- Hardware audio level packets mapping loudness directly to LED intensity (Level 7 quiet to Level 0 peak)
- Dynamic wave response packets mapping loudness to wave amplitude (0 to 5)
- Color cycling on transient musical beats
- Automatic silence sleep: turns off LEDs completely (Mode 14) during sustained silence/pause (no white glitch)
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

# Mode 2: Hardware Static Direct Control Mode (Allows 100% pitch black in silence and direct 0..15 RGB scaling)
PKT_INIT_MUSIC_SYNC = bytes([0x07, 0x13, 0x80, 0xa0, 0x1b, 0x04, 0x00, 0x02])

# Mode 6: Neon Wave default (ambient restore)
PKT_RESTORE_NEON = bytes([0x07, 0x13, 0xff, 0xe2, 0x1b, 0x04, 0x00, 0x02])

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
            # Put mouse into native Direct Static mode (Mode 3)
            fcntl.ioctl(fd, HIDIOCSFEATURE_8, PKT_INIT_MUSIC_SYNC)
            time.sleep(0.01)
            self.controller.commit_config(fd)
            time.sleep(0.01)

            # Turn off all 8 zones initially (completely off / pitch black in silence)
            for z in range(8):
                pkt_black = bytes([0x07, 0x14, (z << 5) | 0, 0, 0, 0, 0, 0])
                fcntl.ioctl(fd, HIDIOCSFEATURE_8, pkt_black)
            time.sleep(0.005)
            self.controller.commit_config(fd)
            time.sleep(0.005)

            color_idx = 0
            last_sent_rgb = (0, 0, 0)
            noise_floor = 150.0
            peak_ceiling = 12000.0
            last_send_time = 0
            last_beat_time = 0
            prev_rms = 0.0
            smooth_norm = 0.0
            silent_ticks = 0
            energy_fast = 0.0
            energy_slow = 0.0

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

                        # Silence Tracking (ticks count consecutive quiet audio frames)
                        if rms < 80.0:
                            silent_ticks += 1
                        else:
                            silent_ticks = 0

                        # When entering silence (at tick 3), reinforce turning off all 8 zones (pitch black)
                        if silent_ticks == 3 and self.min_brightness <= 0.01:
                            try:
                                for z in range(8):
                                    pkt_black = bytes([0x07, 0x14, (z << 5) | 0, 0, 0, 0, 0, 0])
                                    fcntl.ioctl(fd, HIDIOCSFEATURE_8, pkt_black)
                                self.controller.commit_config(fd)
                                last_sent_rgb = (0, 0, 0)
                            except Exception:
                                pass

                        # Dynamic Automatic Gain Control (AGC)
                        if rms > 100.0:
                            noise_floor = (noise_floor * 0.98) + (min(rms, noise_floor) * 0.02)
                            if rms > peak_ceiling:
                                peak_ceiling = (peak_ceiling * 0.75) + (rms * 0.25)
                            else:
                                peak_ceiling = max(1000.0, peak_ceiling * 0.998)

                        sens = self.sensitivity
                        eff_floor = max(80.0, noise_floor / sens)
                        eff_ceiling = max(eff_floor + 400.0, peak_ceiling / sens)

                        # True normalized audio volume (0.0 to 1.0)
                        if rms <= eff_floor:
                            norm = 0.0
                        else:
                            norm = max(0.0, min(1.0, (rms - eff_floor) / (eff_ceiling - eff_floor)))

                        # Get current color palette
                        palette_info = PALETTES.get(self.palette_name, PALETTES["cyberpunk"])
                        palette_colors = palette_info["colors"]

                        # Check if user switched palette in GUI
                        if self.palette_changed:
                            self.palette_changed = False
                            color_idx = 0
                            last_sent_rgb = None

                        # Energy Tracking for Beat Detection
                        energy_fast = (energy_fast * 0.55) + (rms * 0.45)
                        energy_slow = (energy_slow * 0.95) + (rms * 0.05)
                        delta = rms - prev_rms
                        is_beat = False

                        beat_thresh = 1.15 / sens
                        delta_thresh = 110.0 / sens

                        if rms > 70.0 and norm > 0.12 and (now - last_beat_time) > 0.15:
                            if (energy_fast > (energy_slow * beat_thresh) and delta > delta_thresh) or (norm > 0.55 and delta > 120.0):
                                is_beat = True
                                last_beat_time = now
                                if self.color_on_beat:
                                    color_idx = (color_idx + 1) % len(palette_colors)
                                smooth_norm = max(smooth_norm, min(1.0, norm + 0.35))

                        prev_rms = rms

                        # Smooth loudness tracking for Brightness / VU meter
                        if silent_ticks > 5 or norm <= 0.005:
                            smooth_norm *= 0.65
                            if smooth_norm < 0.015:
                                smooth_norm = 0.0
                        elif norm > smooth_norm:
                            smooth_norm = (smooth_norm * 0.20) + (norm * 0.80)
                        else:
                            smooth_norm = (smooth_norm * 0.84) + (norm * 0.16)

                        # Effective volume factoring in silence baseline brightness
                        if self.min_brightness <= 0.01:
                            if smooth_norm <= 0.015:
                                eff_norm = 0.0
                            else:
                                eff_norm = min(1.0, max(0.0, smooth_norm ** 0.85))
                        else:
                            eff_norm = self.min_brightness + (1.0 - self.min_brightness) * (smooth_norm ** 0.85)

                        brightness = eff_norm

                        # Hardware packet throttle (25-30 FPS)
                        min_interval = 1.0 / max(15, min(self.fps, 35))
                        if (now - last_send_time) >= min_interval:
                            last_send_time = now

                            r_base, g_base, b_base = palette_colors[color_idx % len(palette_colors)]

                            if eff_norm <= 0.01 or silent_ticks >= 3:
                                # COMPLETELY OFF / PITCH BLACK IN SILENCE
                                r_scaled = 0
                                g_scaled = 0
                                b_scaled = 0
                            else:
                                # Scale directly from 1 to 15 based on eff_norm
                                r_scaled = max(0, min(15, int(round(r_base * eff_norm))))
                                g_scaled = max(0, min(15, int(round(g_base * eff_norm))))
                                b_scaled = max(0, min(15, int(round(b_base * eff_norm))))
                                if r_base > 0 and r_scaled == 0:
                                    r_scaled = 1
                                if g_base > 0 and g_scaled == 0:
                                    g_scaled = 1
                                if b_base > 0 and b_scaled == 0:
                                    b_scaled = 1

                            current_tuple = (r_scaled, g_scaled, b_scaled)
                            if current_tuple != last_sent_rgb:
                                try:
                                    # ONLY stream Report 0x14 (8 zones RGB) + Report 0x18 (Commit)!
                                    # Report 0x13 is NEVER sent in the frame loop to prevent blue mode-reset flickers!
                                    for z in range(8):
                                        pkt_rgb = bytes([0x07, 0x14, (z << 5) | (g_scaled & 0x0f), ((r_scaled & 0x0f) << 4) | (b_scaled & 0x0f), 0, 0, 0, 0])
                                        fcntl.ioctl(fd, HIDIOCSFEATURE_8, pkt_rgb)
                                    self.controller.commit_config(fd)
                                    last_sent_rgb = current_tuple
                                except Exception:
                                    pass

                        # Notify UI
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
