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

# Mode 12: Hardware Audio Reactive Music Sync ("眉飞色舞")
PKT_INIT_MUSIC_SYNC = bytes([0x07, 0x13, 0x80, 0x42, 0x1b, 0x00, 0x80, 0x02])

# Mode 14: Hardware LED OFF (true 0 brightness / zero light in silence)
PKT_MODE_OFF = bytes([0x07, 0x13, 0x80, 0x62, 0x1b, 0x00, 0x80, 0x02])

# Mode 7: Neon Wave default
PKT_RESTORE_NEON = bytes([0x07, 0x13, 0x80, 0xf2, 0x1b, 0x00, 0x00, 0x02])

# Volume-to-code mapping: quiet/silence = 7, loudest peak = 0
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
            # Put mouse into native Music Sync mode
            fcntl.ioctl(fd, HIDIOCSFEATURE_8, PKT_INIT_MUSIC_SYNC)
            time.sleep(0.05)

            # Send initial color
            palette_info = PALETTES.get(self.palette_name, PALETTES["cyberpunk"])
            init_c = palette_info["colors"][0]
            for z in range(8):
                pkt_rgb = bytes([0x07, 0x14, (z << 5) | (init_c[0] & 0x0f), ((init_c[1] & 0x0f) << 4) | (init_c[2] & 0x0f), 0, 0, 0, 0])
                fcntl.ioctl(fd, HIDIOCSFEATURE_8, pkt_rgb)

            color_idx = 0
            noise_floor = 150.0
            peak_ceiling = 12000.0
            last_send_time = 0
            last_beat_time = 0
            prev_rms = 0.0
            smooth_norm = 0.0
            silent_ticks = 0
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

                        # Silence Tracking (ticks count consecutive quiet audio frames)
                        if rms < 80.0:
                            silent_ticks += 1
                        else:
                            silent_ticks = 0

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

                        # Advanced Beat Detection
                        delta = rms - prev_rms
                        is_beat = False
                        if rms > 150.0 and norm > 0.35 and (now - last_beat_time) > 0.18:
                            if (delta > 800.0 / sens and norm > 0.45) or (norm > 0.85):
                                is_beat = True
                                last_beat_time = now

                        prev_rms = rms

                        # Get current color palette
                        palette_info = PALETTES.get(self.palette_name, PALETTES["cyberpunk"])
                        palette_colors = palette_info["colors"]

                        # Check if user switched palette in GUI
                        if self.palette_changed:
                            self.palette_changed = False
                            color_idx = 0
                            r, g, b = palette_colors[0]
                            for z in range(8):
                                pkt_rgb = bytes([0x07, 0x14, (z << 5) | (r & 0x0f), ((g & 0x0f) << 4) | (b & 0x0f), 0, 0, 0, 0])
                                try:
                                    fcntl.ioctl(fd, HIDIOCSFEATURE_8, pkt_rgb)
                                except Exception:
                                    pass

                        # Color cycle on beat
                        if is_beat and self.color_on_beat:
                            color_idx = (color_idx + 1) % len(palette_colors)
                            r, g, b = palette_colors[color_idx]
                            for z in range(8):
                                pkt_rgb = bytes([0x07, 0x14, (z << 5) | (r & 0x0f), ((g & 0x0f) << 4) | (b & 0x0f), 0, 0, 0, 0])
                                try:
                                    fcntl.ioctl(fd, HIDIOCSFEATURE_8, pkt_rgb)
                                except Exception:
                                    pass

                        # Smooth loudness tracking for Brightness / VU meter
                        if norm > smooth_norm:
                            smooth_norm = (smooth_norm * 0.25) + (norm * 0.75)
                        else:
                            smooth_norm = (smooth_norm * 0.86) + (norm * 0.14)

                        perceptual = smooth_norm ** 0.85
                        brightness = max(0.0, min(1.0, perceptual))

                        # Hardware packet throttle (30 FPS)
                        min_interval = 1.0 / max(15, min(self.fps, 45))
                        if (now - last_send_time) >= min_interval:
                            last_send_time = now

                            # If music is paused / silent for > 1.2 seconds and silence baseline is 0
                            if silent_ticks > 40 and self.min_brightness <= 0.01:
                                if not is_hardware_off:
                                    try:
                                        fcntl.ioctl(fd, HIDIOCSFEATURE_8, PKT_MODE_OFF)
                                    except Exception:
                                        pass
                                    is_hardware_off = True
                            else:
                                # Sound is playing: ensure mouse is awake in Mode 12
                                if is_hardware_off:
                                    try:
                                        fcntl.ioctl(fd, HIDIOCSFEATURE_8, PKT_INIT_MUSIC_SYNC)
                                        time.sleep(0.03)
                                        r, g, b = palette_colors[color_idx % len(palette_colors)]
                                        for z in range(8):
                                            pkt_rgb = bytes([0x07, 0x14, (z << 5) | (r & 0x0f), ((g & 0x0f) << 4) | (b & 0x0f), 0, 0, 0, 0])
                                            fcntl.ioctl(fd, HIDIOCSFEATURE_8, pkt_rgb)
                                    except Exception:
                                        pass
                                    is_hardware_off = False

                                # Effective volume factoring in silence baseline brightness
                                eff_norm = self.min_brightness + (1.0 - self.min_brightness) * smooth_norm

                                # 1. Send native hardware audio level code (0 = loudest peak, 7 = quietest)
                                lvl_idx = min(9, int(eff_norm * 9.99))
                                lvl_code = LEVEL_CODES[lvl_idx]
                                pkt_sound = bytes([0x07, 0x13, 0x80, 0xa1, 0x1b, lvl_code, 0x03, 0xff])
                                try:
                                    fcntl.ioctl(fd, HIDIOCSFEATURE_8, pkt_sound)
                                except Exception:
                                    pass

                                # 2. Send native hardware wave response
                                wave_lvl = min(5, int(eff_norm * 5.99))
                                timing = 2 if wave_lvl <= 2 else (1 if wave_lvl <= 4 else 0)
                                pkt_wave = bytes([0x07, 0x13, 0xff, wave_lvl, 0x10, timing, 0x80, 0x00])
                                try:
                                    fcntl.ioctl(fd, HIDIOCSFEATURE_8, pkt_wave)
                                except Exception:
                                    pass

                        # Notify UI
                        r_cur, g_cur, b_cur = palette_colors[color_idx % len(palette_colors)]
                        base_hex = nibbles_to_hex(r_cur, g_cur, b_cur)
                        self.current_rms = rms
                        self.current_norm = smooth_norm
                        self.current_brightness = 0.0 if is_hardware_off else brightness
                        self.current_color = (r_cur, g_cur, b_cur)
                        self.current_color_hex = base_hex
                        self.is_beat = is_beat

                        status_str = "Active (Syncing)" if not is_hardware_off else "Active (Silent - Off)"
                        self._notify_gui(rms, smooth_norm, 0.0 if is_hardware_off else brightness, is_beat, status_str, (r_cur, g_cur, b_cur), base_hex)

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
