#!/usr/bin/env python3
"""
Lighting Modes View for GM333 GUI.
Displays interactive cards for all 16 hardware lighting modes,
speed/brightness sliders, and RGB color chooser.
"""

from gi.repository import Gtk, Gdk, GLib
from .utils import MODES_INFO, PRESET_COLORS, hex_to_nibbles, nibbles_to_hex

class LightingView(Gtk.Box):
    def __init__(self, controller, on_status_change=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.controller = controller
        self.on_status_change = on_status_change

        self.current_mode_key = "neon"
        self.current_color = (0, 15, 15)  # Cyan
        self.current_speed = 2
        self.current_brightness = 0
        self.mode_buttons = {}

        self.set_margin_top(16)
        self.set_margin_bottom(16)
        self.set_margin_start(20)
        self.set_margin_end(20)

        self._build_ui()

    def _build_ui(self):
        # 1. Top Controls Bar: Adjustments Card
        controls_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        controls_card.get_style_context().add_class("glass-card")

        card_title = Gtk.Label(label="Lighting Adjustments")
        card_title.set_halign(Gtk.Align.START)
        card_title.get_style_context().add_class("mode-title")
        controls_card.pack_start(card_title, False, False, 0)

        # Grid of sliders and color picker
        ctrl_grid = Gtk.Grid()
        ctrl_grid.set_column_spacing(24)
        ctrl_grid.set_row_spacing(10)
        ctrl_grid.set_hexpand(True)

        # Speed Slider (1 to 7)
        lbl_speed = Gtk.Label(label="Effect Speed:")
        lbl_speed.set_halign(Gtk.Align.START)
        self.adj_speed = Gtk.Adjustment(value=self.current_speed, lower=1, upper=7, step_increment=1, page_increment=1)
        self.scale_speed = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.adj_speed)
        self.scale_speed.set_digits(0)
        self.scale_speed.set_value_pos(Gtk.PositionType.RIGHT)
        self.scale_speed.set_hexpand(True)
        self.scale_speed.connect("value-changed", self._on_speed_changed)

        ctrl_grid.attach(lbl_speed, 0, 0, 1, 1)
        ctrl_grid.attach(self.scale_speed, 1, 0, 1, 1)

        # Brightness Slider (0 to 4)
        lbl_bright = Gtk.Label(label="Brightness:")
        lbl_bright.set_halign(Gtk.Align.START)
        self.adj_bright = Gtk.Adjustment(value=self.current_brightness, lower=0, upper=4, step_increment=1, page_increment=1)
        self.scale_bright = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.adj_bright)
        self.scale_bright.set_digits(0)
        self.scale_bright.set_value_pos(Gtk.PositionType.RIGHT)
        self.scale_bright.set_hexpand(True)
        self.scale_bright.connect("value-changed", self._on_bright_changed)

        ctrl_grid.attach(lbl_bright, 0, 1, 1, 1)
        ctrl_grid.attach(self.scale_bright, 1, 1, 1, 1)

        # Color Selector Row
        lbl_color = Gtk.Label(label="Custom Color:")
        lbl_color.set_halign(Gtk.Align.START)

        color_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        # Color Presets Swatches
        for item in PRESET_COLORS:
            btn = Gtk.Button()
            btn.get_style_context().add_class("color-pill")
            # CSS styling for background color
            css = f"button {{ background-color: {item['hex']}; min-width: 24px; min-height: 24px; border-radius: 12px; }}"
            provider = Gtk.CssProvider()
            provider.load_from_data(css.encode())
            btn.get_style_context().add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            btn.set_tooltip_text(item["name"])
            btn.connect("clicked", self._on_preset_color_clicked, item["rgb"], item["hex"])
            color_box.pack_start(btn, False, False, 0)

        # Custom Color Chooser Button
        self.color_chooser = Gtk.ColorButton()
        init_rgba = Gdk.RGBA()
        init_rgba.parse("#00ffff")
        self.color_chooser.set_rgba(init_rgba)
        self.color_chooser.set_title("Select Custom Mouse LED Color")
        self.color_chooser.connect("color-set", self._on_custom_color_chosen)
        color_box.pack_start(self.color_chooser, False, False, 4)

        ctrl_grid.attach(lbl_color, 2, 0, 1, 1)
        ctrl_grid.attach(color_box, 3, 0, 1, 1)

        # Apply & Quick Action Buttons
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        actions_box.set_halign(Gtk.Align.END)

        btn_off = Gtk.Button(label="Turn LEDs Off")
        btn_off.connect("clicked", lambda w: self.apply_mode_by_key("off"))
        actions_box.pack_start(btn_off, False, False, 0)

        btn_default = Gtk.Button(label="Reset to Neon")
        btn_default.connect("clicked", lambda w: self.apply_mode_by_key("neon"))
        actions_box.pack_start(btn_default, False, False, 0)

        self.btn_apply = Gtk.Button(label="Apply Current Mode")
        self.btn_apply.get_style_context().add_class("btn-primary")
        self.btn_apply.connect("clicked", lambda w: self.apply_current_settings())
        actions_box.pack_start(self.btn_apply, False, False, 0)

        ctrl_grid.attach(actions_box, 2, 1, 2, 1)

        controls_card.pack_start(ctrl_grid, False, False, 0)
        self.pack_start(controls_card, False, False, 0)

        # 2. Section Title
        sec_title = Gtk.Label(label="Hardware Lighting Modes (Select to Activate)")
        sec_title.set_halign(Gtk.Align.START)
        sec_title.get_style_context().add_class("mode-title")
        self.pack_start(sec_title, False, False, 0)

        # 3. Scrolled Grid of 16 Mode Cards
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(12)
        grid.set_hexpand(True)
        grid.set_halign(Gtk.Align.FILL)

        columns = 4
        for idx, mode in enumerate(MODES_INFO):
            row = idx // columns
            col = idx % columns

            btn = Gtk.Button()
            btn.get_style_context().add_class("mode-card")
            btn.set_hexpand(True)

            card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            card_box.set_margin_top(8)
            card_box.set_margin_bottom(8)
            card_box.set_margin_start(10)
            card_box.set_margin_end(10)

            # Icon & Title row
            top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            icon = Gtk.Image.new_from_icon_name(mode["icon"], Gtk.IconSize.MENU)
            lbl_name = Gtk.Label(label=mode["name"])
            lbl_name.get_style_context().add_class("mode-title")
            lbl_name.set_halign(Gtk.Align.START)
            top_row.pack_start(icon, False, False, 0)
            top_row.pack_start(lbl_name, False, False, 0)

            badge = Gtk.Label(label=f"ID {mode['id']}")
            badge.get_style_context().add_class("mode-desc")
            badge.set_halign(Gtk.Align.END)
            top_row.pack_end(badge, False, False, 0)

            card_box.pack_start(top_row, False, False, 0)

            # Description
            lbl_desc = Gtk.Label(label=mode["desc"])
            lbl_desc.set_line_wrap(True)
            lbl_desc.set_max_width_chars(28)
            lbl_desc.set_xalign(0.0)
            lbl_desc.get_style_context().add_class("mode-desc")
            card_box.pack_start(lbl_desc, False, False, 0)

            btn.add(card_box)
            btn.connect("clicked", self._on_mode_clicked, mode["key"])
            self.mode_buttons[mode["key"]] = btn

            grid.attach(btn, col, row, 1, 1)

        scrolled.add(grid)
        self.pack_start(scrolled, True, True, 0)

        # Highlight default mode
        self._update_active_mode_ui("neon")

    def _on_mode_clicked(self, widget, mode_key):
        self.apply_mode_by_key(mode_key)

    def apply_mode_by_key(self, mode_key):
        self.current_mode_key = mode_key
        self._update_active_mode_ui(mode_key)
        self.apply_current_settings()

    def _update_active_mode_ui(self, active_key):
        for k, btn in self.mode_buttons.items():
            if k == active_key:
                btn.get_style_context().add_class("active-mode")
            else:
                btn.get_style_context().remove_class("active-mode")

    def _on_speed_changed(self, widget):
        self.current_speed = int(widget.get_value())
        self.apply_current_settings()

    def _on_bright_changed(self, widget):
        self.current_brightness = int(widget.get_value())
        self.apply_current_settings()

    def _on_preset_color_clicked(self, widget, rgb, hex_val):
        self.current_color = rgb
        rgba = Gdk.RGBA()
        rgba.parse(hex_val)
        self.color_chooser.set_rgba(rgba)
        self.apply_current_settings()

    def _on_custom_color_chosen(self, widget):
        rgba = widget.get_rgba()
        r = int(rgba.red * 15)
        g = int(rgba.green * 15)
        b = int(rgba.blue * 15)
        self.current_color = (r, g, b)
        self.apply_current_settings()

    def apply_current_settings(self):
        # Stop background music service if running so it doesn't overwrite
        if self.current_mode_key != "music":
            self.controller.stop_service()

        target_mode = next((m for m in MODES_INFO if m["key"] == self.current_mode_key), None)
        if not target_mode:
            return

        r, g, b = self.current_color if target_mode["supports_color"] else (None, None, None)
        success, msg = self.controller.send_mode(
            led_type=target_mode["id"],
            speed=self.current_speed,
            brightness=self.current_brightness,
            r=r, g=g, b=b
        )

        status_msg = f"{target_mode['name']} applied (Speed: {self.current_speed}, Brightness: {self.current_brightness})"
        if not success:
            status_msg = f"Error: {msg}"

        if self.on_status_change:
            self.on_status_change(status_msg, success)
