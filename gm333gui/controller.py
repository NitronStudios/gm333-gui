#!/usr/bin/env python3
"""
Hardware communication controller for Ant Esports GM333 Gaming Mouse.
Handles low-level HID feature reports via hidraw ioctl without external C libraries.
"""

import os
import sys
import glob
import time
import fcntl
import subprocess
from .utils import HID_DEVICE_LINK, HIDIOCSFEATURE_8, VENDOR_ID, PRODUCT_ID

class GM333Controller:
    def __init__(self):
        self.device_path = None
        self.is_connected = False
        self.has_permission = False
        self.error_message = ""
        self.detect_device()

    def detect_device(self):
        """Scans the system for the GM333 Interface 1 hidraw device."""
        self.device_path = None
        self.is_connected = False
        self.has_permission = False
        self.error_message = ""

        # 1. Primary check: by-id symlink
        if os.path.exists(HID_DEVICE_LINK):
            self.device_path = os.path.realpath(HID_DEVICE_LINK)
            self.is_connected = True
            if os.access(self.device_path, os.R_OK | os.W_OK):
                self.has_permission = True
                return True
            else:
                self.has_permission = False
                self.error_message = f"Found {self.device_path} but missing write permissions. Udev rule required."
                return True

        # 2. Secondary check: glob through /dev/hidraw* and inspect sysfs
        for hpath in sorted(glob.glob("/dev/hidraw*")):
            num = os.path.basename(hpath).replace("hidraw", "")
            uevent_path = f"/sys/class/hidraw/hidraw{num}/device/uevent"
            if os.path.exists(uevent_path):
                try:
                    with open(uevent_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read().upper()
                    if VENDOR_ID.upper() in content and PRODUCT_ID.upper() in content and "INPUT1" in content:
                        self.device_path = hpath
                        self.is_connected = True
                        if os.access(hpath, os.R_OK | os.W_OK):
                            self.has_permission = True
                            return True
                        else:
                            self.has_permission = False
                            self.error_message = f"Found {hpath} but write access denied."
                            return True
                except Exception as e:
                    pass

        self.error_message = "GM333 mouse not detected on USB. Please plug it in."
        return False

    def open_device(self):
        """Opens the hidraw device descriptor."""
        if not self.detect_device() or not self.device_path:
            return None
        try:
            return os.open(self.device_path, os.O_RDWR)
        except PermissionError:
            self.has_permission = False
            self.error_message = f"Permission denied opening {self.device_path}. Run with udev rule."
            return None
        except Exception as e:
            self.error_message = str(e)
            return None

    def send_mode(self, led_type, speed=2, brightness=4, r=None, g=None, b=None):
        """
        Sends the 8-byte HID feature report to configure hardware lighting mode.
        If color (r, g, b) is supplied, streams 4-bit nibbles for all 8 zones.
        """
        fd = self.open_device()
        if fd is None:
            return False, self.error_message

        try:
            speed = max(1, min(7, int(speed)))
            brightness = max(0, min(4, int(brightness)))
            led_type = int(led_type)

            # Official Instant Microelectronics packet structure:
            # Byte 0: 0x07 (Report ID)
            # Byte 1: 0x13 (Lighting Mode command)
            # Byte 2: 0x80 for single color (Static, Mono Water, Off) or 0xff for 7-color cycling
            # Byte 3: 0x80 | ((led_type & 0x07) << 4) | (speed & 0x07)
            # Byte 4: 0x1b (Direction: right 0x10 + 0x0b)
            # Byte 5: brightness & 7 (0 to 4)
            # Byte 6: 0x80 for modes >= 8 (bit 3 of led_type shifted to bit 7), else 0x00
            # Byte 7: 0x02
            is_single_color = led_type in [2, 4, 13]
            b0 = 0x07
            b1 = 0x13
            b2 = 0x80 if is_single_color else 0xff
            b3 = 0x80 | ((led_type & 0x07) << 4) | (speed & 0x07)
            b4 = 0x1b
            b5 = brightness & 7
            b6 = 0x80 if led_type >= 8 else 0x00
            b7 = 0x02
            pkt = bytes([b0, b1, b2, b3, b4, b5, b6, b7])

            # If mode uses single custom color (Static, Mono Water, Single Breath):
            if r is not None and g is not None and b is not None:
                r_nib = max(0, min(15, int(r)))
                g_nib = max(0, min(15, int(g)))
                b_nib = max(0, min(15, int(b)))
                for z in range(8):
                    cpkt = bytes([0x07, 0x14, (z << 5) | (g_nib & 0xf), ((r_nib & 0xf) << 4) | (b_nib & 0xf), 0, 0, 0, 0])
                    fcntl.ioctl(fd, HIDIOCSFEATURE_8, cpkt)

            fcntl.ioctl(fd, HIDIOCSFEATURE_8, pkt)

            if r is not None and g is not None and b is not None:
                for z in range(8):
                    cpkt = bytes([0x07, 0x14, (z << 5) | (g_nib & 0xf), ((r_nib & 0xf) << 4) | (b_nib & 0xf), 0, 0, 0, 0])
                    fcntl.ioctl(fd, HIDIOCSFEATURE_8, cpkt)

            # Mandatory commit handshake strobe
            time.sleep(0.005)
            fcntl.ioctl(fd, HIDIOCSFEATURE_8, bytes([0x07, 0x18, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00]))
            time.sleep(0.005)
            fcntl.ioctl(fd, HIDIOCSFEATURE_8, bytes([0x07, 0x18, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]))

            return True, "Mode applied successfully"
        except Exception as e:
            return False, f"Failed sending HID report: {e}"
        finally:
            try:
                os.close(fd)
            except Exception:
                pass

    def commit_config(self, fd=None):
        """Sends Report 0x18 hardware commit trigger to apply registers."""
        own_fd = False
        if fd is None:
            fd = self.open_device()
            own_fd = True
        if fd is None:
            return False
        try:
            fcntl.ioctl(fd, HIDIOCSFEATURE_8, bytes([0x07, 0x18, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00]))
            time.sleep(0.005)
            fcntl.ioctl(fd, HIDIOCSFEATURE_8, bytes([0x07, 0x18, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]))
            return True
        except Exception:
            return False
        finally:
            if own_fd:
                try:
                    os.close(fd)
                except Exception:
                    pass

    def send_feature_report(self, pkt):
        """Send raw 8-byte feature report."""
        fd = self.open_device()
        if fd is None:
            return False
        try:
            fcntl.ioctl(fd, HIDIOCSFEATURE_8, pkt)
            return True
        except Exception:
            return False
        finally:
            try:
                os.close(fd)
            except Exception:
                pass

    def is_service_running(self):
        """Checks if the background systemd music sync service is active."""
        try:
            res = subprocess.run(["systemctl", "--user", "is-active", "gm333-music-sync.service"],
                                 stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            return res.stdout.strip() == "active"
        except Exception:
            return False

    def stop_service(self):
        """Stops the background systemd service if running."""
        try:
            subprocess.run(["systemctl", "--user", "stop", "gm333-music-sync.service"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False
