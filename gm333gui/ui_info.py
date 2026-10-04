#!/usr/bin/env python3
"""
Device Information, Udev Rules, and Diagnostics View for GM333 GUI.
"""

import os
import subprocess
from gi.repository import Gtk, GLib

class InfoView(Gtk.Box):
    def __init__(self, controller, on_status_change=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.controller = controller
        self.on_status_change = on_status_change

        self.set_margin_top(16)
        self.set_margin_bottom(16)
        self.set_margin_start(20)
        self.set_margin_end(20)

        self._build_ui()
        self.refresh_info()

    def _build_ui(self):
        # 1. Device Info Card
        card_dev = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card_dev.get_style_context().add_class("glass-card")

        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lbl_card = Gtk.Label(label="Hardware Device Information")
        lbl_card.get_style_context().add_class("mode-title")
        title_box.pack_start(lbl_card, False, False, 0)

        self.lbl_conn_status = Gtk.Label(label="Checking...")
        title_box.pack_end(self.lbl_conn_status, False, False, 0)
        card_dev.pack_start(title_box, False, False, 0)

        grid = Gtk.Grid()
        grid.set_column_spacing(20)
        grid.set_row_spacing(8)
        grid.set_hexpand(True)

        rows = [
            ("Mouse Model:", "Ant Esports GM333 RGB Programmable Gaming Mouse"),
            ("USB Vendor ID:", "0x30fa (Instant Microelectronics Corp.)"),
            ("USB Product ID:", "0x1440 (GM333 Controller)"),
            ("HID Interface:", "Interface 1 (Custom Vendor Feature Reports 0x07)"),
            ("Device Node Path:", "/dev/input/by-id/usb-INSTANT_USB_GAMING_MOUSE-if01-hidraw"),
            ("Permissions:", "Read / Write Access (User space accessible)"),
        ]

        self.info_labels = {}
        for idx, (label_text, default_val) in enumerate(rows):
            lbl_key = Gtk.Label(label=label_text)
            lbl_key.set_halign(Gtk.Align.START)
            lbl_val = Gtk.Label(label=default_val)
            lbl_val.set_halign(Gtk.Align.START)
            lbl_val.set_selectable(True)
            lbl_val.get_style_context().add_class("mode-desc")

            grid.attach(lbl_key, 0, idx, 1, 1)
            grid.attach(lbl_val, 1, idx, 1, 1)
            self.info_labels[label_text] = lbl_val

        card_dev.pack_start(grid, False, False, 0)

        # Refresh button
        btn_refresh = Gtk.Button(label="Re-scan USB & HID Devices")
        btn_refresh.set_halign(Gtk.Align.START)
        btn_refresh.connect("clicked", lambda w: self.refresh_info())
        card_dev.pack_start(btn_refresh, False, False, 4)

        self.pack_start(card_dev, False, False, 0)

        # 2. Udev Rules Management Card
        card_udev = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card_udev.get_style_context().add_class("glass-card")

        lbl_udev = Gtk.Label(label="Linux Permissions (udev rule)")
        lbl_udev.get_style_context().add_class("mode-title")
        lbl_udev.set_halign(Gtk.Align.START)
        card_udev.pack_start(lbl_udev, False, False, 0)

        desc_udev = Gtk.Label(
            label="In Linux, USB HID devices normally require root privileges unless a udev rule is installed. "
                  "With the rule installed, any non-root user can control the lighting and music sync without sudo."
        )
        desc_udev.set_line_wrap(True)
        desc_udev.set_xalign(0.0)
        desc_udev.get_style_context().add_class("mode-desc")
        card_udev.pack_start(desc_udev, False, False, 0)

        udev_action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        self.lbl_udev_state = Gtk.Label(label="Checking udev rule...")
        self.lbl_udev_state.set_halign(Gtk.Align.START)
        udev_action_box.pack_start(self.lbl_udev_state, True, True, 0)

        btn_install_rule = Gtk.Button(label="Install / Reload Udev Rule")
        btn_install_rule.connect("clicked", self._on_install_rule_clicked)
        udev_action_box.pack_end(btn_install_rule, False, False, 0)

        card_udev.pack_start(udev_action_box, False, False, 0)
        self.pack_start(card_udev, False, False, 0)

        # 3. Hardware Test Card
        card_test = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card_test.get_style_context().add_class("glass-card")

        lbl_test = Gtk.Label(label="Hardware Communication Test")
        lbl_test.get_style_context().add_class("mode-title")
        lbl_test.set_halign(Gtk.Align.START)
        card_test.pack_start(lbl_test, False, False, 0)

        test_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        btn_flash_green = Gtk.Button(label="Test Green Flash")
        btn_flash_green.connect("clicked", lambda w: self._test_flash(0, 15, 0))
        test_btn_box.pack_start(btn_flash_green, False, False, 0)

        btn_flash_cyan = Gtk.Button(label="Test Cyan Flash")
        btn_flash_cyan.connect("clicked", lambda w: self._test_flash(0, 15, 15))
        test_btn_box.pack_start(btn_flash_cyan, False, False, 0)

        btn_flash_magenta = Gtk.Button(label="Test Magenta Flash")
        btn_flash_magenta.connect("clicked", lambda w: self._test_flash(15, 0, 15))
        test_btn_box.pack_start(btn_flash_magenta, False, False, 0)

        card_test.pack_start(test_btn_box, False, False, 0)
        self.pack_start(card_test, False, False, 0)

    def refresh_info(self):
        self.controller.detect_device()
        is_conn = self.controller.is_connected
        has_perm = self.controller.has_permission

        if is_conn and has_perm:
            self.lbl_conn_status.set_text("● CONNECTED & READY")
            self.lbl_conn_status.get_style_context().remove_class("status-badge-disconnected")
            self.lbl_conn_status.get_style_context().add_class("status-badge-connected")
            self.info_labels["Permissions:"].set_text("Read/Write Granted (Fully functional)")
        elif is_conn and not has_perm:
            self.lbl_conn_status.set_text("● PERMISSION REQUIRED")
            self.lbl_conn_status.get_style_context().remove_class("status-badge-connected")
            self.lbl_conn_status.get_style_context().add_class("status-badge-disconnected")
            self.info_labels["Permissions:"].set_text("Missing Write Permission. Install udev rule.")
        else:
            self.lbl_conn_status.set_text("● DISCONNECTED")
            self.lbl_conn_status.get_style_context().remove_class("status-badge-connected")
            self.lbl_conn_status.get_style_context().add_class("status-badge-disconnected")
            self.info_labels["Permissions:"].set_text("N/A")

        node_path = self.controller.device_path or "Not found"
        self.info_labels["Device Node Path:"].set_text(node_path)

        # Check udev rule file
        rule_exists = os.path.exists("/etc/udev/rules.d/99-ant-esports.rules") or \
                      os.path.exists("/etc/udev/rules.d/99-ant-esports-gm333.rules")
        if rule_exists:
            self.lbl_udev_state.set_text("✓ Udev rule installed at /etc/udev/rules.d/ (active)")
        else:
            self.lbl_udev_state.set_text("✗ Udev rule not found in /etc/udev/rules.d/")

    def _test_flash(self, r, g, b):
        self.controller.send_mode(led_type=3, speed=1, brightness=0, r=r, g=g, b=b)
        if self.on_status_change:
            self.on_status_change(f"Sent hardware test color ({r}, {g}, {b})", True)

    def _on_install_rule_clicked(self, widget):
        rule_text = 'SUBSYSTEM=="hidraw", ATTRS{idVendor}=="30fa", ATTRS{idProduct}=="1440", MODE="0666", TAG+="uaccess"\n'
        cmd = f"echo '{rule_text}' | sudo tee /etc/udev/rules.d/99-ant-esports-gm333.rules && sudo udevadm control --reload-rules && sudo udevadm trigger"
        
        # Try pkexec or terminal
        try:
            subprocess.run(["pkexec", "sh", "-c", f"echo '{rule_text}' > /etc/udev/rules.d/99-ant-esports-gm333.rules && udevadm control --reload-rules && udevadm trigger"], check=True)
            self.refresh_info()
            if self.on_status_change:
                self.on_status_change("Udev rule installed and reloaded successfully!", True)
        except Exception as e:
            if self.on_status_change:
                self.on_status_change(f"Could not install automatically. Run in terminal: {cmd}", False)
