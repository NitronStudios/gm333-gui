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

    def send_mode(self, led_type, speed=2, brightness=0, r=None, g=None, b=None):
        """
        Sends the 8-byte HID feature report to configure hardware lighting mode.
        If color (r, g, b) is supplied, sends color packets right after.
        """
        fd = self.open_device()
        if fd is None:
            return False, self.error_message

        try:
            speed = max(1, min(7, int(speed)))
            brightness = max(0, min(4, int(brightness)))
            led_type = int(led_type)

            b0 = 0x07
            b1 = 0x13
            b2 = 0x80
            b3 = ((1 << 7) + (led_type << 4) + (speed & 7)) & 0xff
            b4 = 0x1b
            b5 = brightness & 7
            b6 = (((led_type >> 3) << 7) + ((0x4002 >> 8) & 3)) & 0xff
            b7 = 0x4002 & 0xff
            pkt = bytes([b0, b1, b2, b3, b4, b5, b6, b7])
            fcntl.ioctl(fd, HIDIOCSFEATURE_8, pkt)

            # If color specified, send color packet
            if r is not None and g is not None and b is not None:
                time.sleep(0.04)
                r_nib = max(0, min(15, int(r)))
                g_nib = max(0, min(15, int(g)))
                b_nib = max(0, min(15, int(b)))
                for z in range(8):
                    cpkt = bytes([0x07, 0x14, (z << 5) | (r_nib & 0xf), ((g_nib & 0xf) << 4) | (b_nib & 0xf), 0, 0, 0, 0])
                    fcntl.ioctl(fd, HIDIOCSFEATURE_8, cpkt)

            return True, "Mode applied successfully"
        except Exception as e:
            return False, f"Failed sending HID report: {e}"
        finally:
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
