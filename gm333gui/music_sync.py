#!/usr/bin/env python3
"""
Threaded Audio Reactive Music Sync Engine for GM333.
Streams live desktop audio (PipeWire/PulseAudio) to the GM333 controller
and posts real-time visualization data back to the GTK GUI.
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

from .utils import PALETTES, HIDIOCSFEATURE_8

PKT_INIT_MUSIC_SYNC = bytes([0x07, 0x13, 0x80, 0x42, 0x1b, 0x00, 0x80, 0x02])
PKT_RESTORE_NEON   = bytes([0x07, 0x13, 0x80, 0xf2, 0x1b, 0x00, 0x00, 0x02])
LEVEL_CODES        = [7, 5, 5, 4, 4, 3, 3, 2, 2, 0]

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
        self.fps = 25
        self.target_sink = None

        # Live telemetry
        self.current_sink_name = "Detecting..."
        self.current_rms = 0.0
        self.current_norm = 0.0
        self.is_beat = False
        self.status_text = "Idle"

    def set_palette(self, name):
        if name in PALETTES:
            self.palette_name = name

    def set_sensitivity(self, val):
        self.sensitivity = max(0.1, min(5.0, float(val)))

    def set_fps(self, val):
        self.fps = max(10, min(50, int(val)))

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
        self._notify_gui(0.0, 0.0, False, "Stopped")

    def _notify_gui(self, rms, norm, is_beat, status):
        if self.on_update:
            GLib.idle_add(self.on_update, rms, norm, is_beat, status, self.current_sink_name)

    def _worker(self):
        """Background streaming worker loop."""
        fd = self.controller.open_device()
        if fd is None:
            self.status_text = "Failed to open mouse device"
            self.is_running = False
            self._notify_gui(0.0, 0.0, False, self.status_text)
            return

        try:
            # 1. Initialize mouse into hardware Music Sync Mode
            fcntl.ioctl(fd, HIDIOCSFEATURE_8, PKT_INIT_MUSIC_SYNC)
            time.sleep(0.05)

            color_idx = 0
            noise_floor = 150.0
            peak_ceiling = 2500.0
            last_send_time = 0
            last_beat_time = 0
            prev_rms = 0.0

            while not self.stop_event.is_set():
                # Detect active audio sink
                monitor, sink_simple = self.get_default_monitor()
                if not monitor:
                    self.current_sink_name = "Waiting for audio device..."
                    self.status_text = "No active audio sink found"
                    self._notify_gui(0.0, 0.0, False, self.status_text)
                    time.sleep(1.0)
                    continue

                self.current_sink_name = sink_simple or monitor
                self.status_text = "Listening to audio..."

                # Start parec
                cmd = ["parec", "-d", monitor, "--format=s16le", "--channels=1", "--rate=22050", "--latency-msec=25"]
                try:
                    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                except Exception:
                    cmd = ["parec", "-d", monitor, "--format=s16le", "--channels=1", "--rate=22050"]
                    try:
                        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                    except Exception as e:
                        self.status_text = f"Audio capture error: {e}"
                        self._notify_gui(0.0, 0.0, False, self.status_text)
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

                        # AGC
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

                        delta = rms - prev_rms
                        is_beat = (norm > 0.45 and delta > 300.0) or (norm > 0.85)
                        prev_rms = rms

                        min_interval = 1.0 / max(10, min(self.fps, 45))
                        if (now - last_send_time) >= min_interval:
                            last_send_time = now

                            # Sound level packet
                            lvl_idx = min(9, int(norm * 9.99))
                            lvl_code = LEVEL_CODES[lvl_idx]
                            pkt_sound = bytes([0x07, 0x13, 0x80, 0xa1, 0x1b, lvl_code, 0x03, 0xff])
                            try:
                                fcntl.ioctl(fd, HIDIOCSFEATURE_8, pkt_sound)
                            except Exception:
                                pass

                            # Wave response packet
                            wave_lvl = min(5, int(norm * 5.99))
                            timing = 2 if wave_lvl <= 2 else (1 if wave_lvl <= 4 else 0)
                            pkt_wave = bytes([0x07, 0x13, 0xff, wave_lvl, 0x10, timing, 0x80, 0x00])
                            try:
                                fcntl.ioctl(fd, HIDIOCSFEATURE_8, pkt_wave)
                            except Exception:
                                pass

                            # Color pulse on beat
                            palette_info = PALETTES.get(self.palette_name, PALETTES["cyberpunk"])
                            palette_colors = palette_info["colors"]
                            if is_beat and (now - last_beat_time) > 0.11:
                                last_beat_time = now
                                r, g, b = palette_colors[color_idx % len(palette_colors)]
                                color_idx += 1
                                for zone in range(4):
                                    pkt_rgb = bytes([0x07, 0x14, (zone << 5) | (r & 0x0f), ((g & 0x0f) << 4) | (b & 0x0f), 0x00, 0x00, 0x00, 0x00])
                                    try:
                                        fcntl.ioctl(fd, HIDIOCSFEATURE_8, pkt_rgb)
                                    except Exception:
                                        pass

                        # Notify UI
                        self.current_rms = rms
                        self.current_norm = norm
                        self.is_beat = is_beat
                        self._notify_gui(rms, norm, is_beat, "Active (Syncing)")

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
