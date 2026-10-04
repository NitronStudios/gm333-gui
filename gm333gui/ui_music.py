#!/usr/bin/env python3
"""
Music Sync (Audio-Reactive Visualizer) View for GM333 GUI.
Includes real-time Cairo-rendered audio level meters, beat detector pulses,
palette selector with visual swatches, and sensitivity controls.
"""

import math
from gi.repository import Gtk, Gdk, GLib
import cairo

from .utils import PALETTES
from .music_sync import MusicSyncEngine

class MusicSyncView(Gtk.Box):
    def __init__(self, controller, on_status_change=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.controller = controller
        self.on_status_change = on_status_change

        self.engine = MusicSyncEngine(controller, on_update_callback=self._on_engine_update)

        # Visualization state
        self.rms = 0.0
        self.norm = 0.0
        self.is_beat = False
        self.beat_pulse = 0.0
        self.peak_norm = 0.0
        self.current_sink = "Detecting..."
        self.palette_buttons = {}

        self.set_margin_top(16)
        self.set_margin_bottom(16)
        self.set_margin_start(20)
        self.set_margin_end(20)

        self._build_ui()

        # UI Animation tick timer (runs at ~40 FPS for smooth rendering)
        GLib.timeout_add(25, self._on_anim_tick)

    def _build_ui(self):
        # 1. Hero Card: Status & Start/Stop
        hero_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        hero_card.get_style_context().add_class("hero-card")

        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)

        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        lbl_title = Gtk.Label(label="Audio Reactive Music Sync")
        lbl_title.get_style_context().add_class("title")
        lbl_title.set_halign(Gtk.Align.START)

        self.lbl_sink = Gtk.Label(label="Audio Source: Detecting desktop playback...")
        self.lbl_sink.set_halign(Gtk.Align.START)
        self.lbl_sink.get_style_context().add_class("mode-desc")

        title_box.pack_start(lbl_title, False, False, 0)
        title_box.pack_start(self.lbl_sink, False, False, 0)
        top_row.pack_start(title_box, True, True, 0)

        # Big Toggle Button
        self.btn_toggle = Gtk.Button(label="START MUSIC SYNC")
        self.btn_toggle.get_style_context().add_class("btn-accent")
        self.btn_toggle.connect("clicked", self._on_toggle_clicked)
        top_row.pack_end(self.btn_toggle, False, False, 0)

        hero_card.pack_start(top_row, False, False, 0)

        # 2. Real-time Cairo Visualizer Canvas
        self.canvas = Gtk.DrawingArea()
        self.canvas.set_size_request(-1, 100)
        self.canvas.connect("draw", self._on_draw_canvas)
        hero_card.pack_start(self.canvas, True, True, 4)

        # Telemetry Labels Row
        stat_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)

        self.lbl_rms = Gtk.Label(label="RMS Level: 0.0")
        self.lbl_rms.get_style_context().add_class("mode-desc")
        stat_row.pack_start(self.lbl_rms, False, False, 0)

        self.lbl_state = Gtk.Label(label="Status: Idle (Click Start to sync mouse with music)")
        self.lbl_state.get_style_context().add_class("mode-desc")
        stat_row.pack_start(self.lbl_state, False, False, 0)

        self.lbl_beat_badge = Gtk.Label(label="BEAT DETECTED")
        self.lbl_beat_badge.get_style_context().add_class("status-badge-active")
        self.lbl_beat_badge.set_visible(False)
        stat_row.pack_end(self.lbl_beat_badge, False, False, 0)

        hero_card.pack_start(stat_row, False, False, 0)
        self.pack_start(hero_card, False, False, 0)

        # 3. Settings Card: Sensitivity & FPS
        ctrl_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        ctrl_card.get_style_context().add_class("glass-card")

        card_title = Gtk.Label(label="Visualizer Sensitivity & Dynamics")
        card_title.set_halign(Gtk.Align.START)
        card_title.get_style_context().add_class("mode-title")
        ctrl_card.pack_start(card_title, False, False, 0)

        grid = Gtk.Grid()
        grid.set_column_spacing(20)
        grid.set_row_spacing(10)
        grid.set_hexpand(True)

        # Sensitivity Slider
        lbl_sens = Gtk.Label(label="Sensitivity Multiplier:")
        lbl_sens.set_halign(Gtk.Align.START)
        self.adj_sens = Gtk.Adjustment(value=1.0, lower=0.2, upper=3.5, step_increment=0.1, page_increment=0.5)
        self.scale_sens = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.adj_sens)
        self.scale_sens.set_digits(2)
        self.scale_sens.set_value_pos(Gtk.PositionType.RIGHT)
        self.scale_sens.set_hexpand(True)
        self.scale_sens.connect("value-changed", self._on_sens_changed)

        grid.attach(lbl_sens, 0, 0, 1, 1)
        grid.attach(self.scale_sens, 1, 0, 1, 1)

        # FPS Slider
        lbl_fps = Gtk.Label(label="LED Update Rate (FPS):")
        lbl_fps.set_halign(Gtk.Align.START)
        self.adj_fps = Gtk.Adjustment(value=25, lower=15, upper=40, step_increment=1, page_increment=5)
        self.scale_fps = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.adj_fps)
        self.scale_fps.set_digits(0)
        self.scale_fps.set_value_pos(Gtk.PositionType.RIGHT)
        self.scale_fps.set_hexpand(True)
        self.scale_fps.connect("value-changed", self._on_fps_changed)

        grid.attach(lbl_fps, 0, 1, 1, 1)
        grid.attach(self.scale_fps, 1, 1, 1, 1)

        ctrl_card.pack_start(grid, False, False, 0)
        self.pack_start(ctrl_card, False, False, 0)

        # 4. Color Palette Selection Card
        pal_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        pal_card.get_style_context().add_class("glass-card")

        pal_title = Gtk.Label(label="Music Rhythm Color Palettes")
        pal_title.set_halign(Gtk.Align.START)
        pal_title.get_style_context().add_class("mode-title")
        pal_card.pack_start(pal_title, False, False, 0)

        pal_grid = Gtk.Grid()
        pal_grid.set_column_spacing(10)
        pal_grid.set_row_spacing(10)
        pal_grid.set_hexpand(True)

        cols = 5
        for idx, (pkey, pdata) in enumerate(PALETTES.items()):
            row = idx // cols
            col = idx % cols

            btn = Gtk.Button()
            btn.get_style_context().add_class("mode-card")

            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            box.set_margin_top(6)
            box.set_margin_bottom(6)
            box.set_margin_start(8)
            box.set_margin_end(8)

            lbl = Gtk.Label(label=pdata["name"])
            lbl.get_style_context().add_class("mode-title")
            box.pack_start(lbl, False, False, 0)

            # Preview swatches bar
            swatch_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
            swatch_box.set_halign(Gtk.Align.CENTER)
            for c_hex in pdata["preview"][:6]:
                dot = Gtk.Box()
                css = f"box {{ background-color: {c_hex}; min-width: 14px; min-height: 14px; border-radius: 7px; }}"
                provider = Gtk.CssProvider()
                provider.load_from_data(css.encode())
                dot.get_style_context().add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
                swatch_box.pack_start(dot, False, False, 0)

            box.pack_start(swatch_box, False, False, 0)
            btn.add(box)
            btn.connect("clicked", self._on_palette_clicked, pkey)
            self.palette_buttons[pkey] = btn

            pal_grid.attach(btn, col, row, 1, 1)

        pal_card.pack_start(pal_grid, False, False, 0)
        self.pack_start(pal_card, False, False, 0)

        self._update_active_palette_ui("cyberpunk")

    def _on_toggle_clicked(self, widget):
        if self.engine.is_running:
            self.engine.stop()
            self.btn_toggle.set_label("START MUSIC SYNC")
            self.btn_toggle.get_style_context().remove_class("btn-stop")
            self.btn_toggle.get_style_context().add_class("btn-accent")
            self.lbl_state.set_text("Status: Stopped (Default Neon lighting restored)")
            if self.on_status_change:
                self.on_status_change("Music Sync stopped. Mouse lighting restored.", True)
        else:
            self.engine.start()
            self.btn_toggle.set_label("STOP MUSIC SYNC")
            self.btn_toggle.get_style_context().remove_class("btn-accent")
            self.btn_toggle.get_style_context().add_class("btn-stop")
            self.lbl_state.set_text("Status: Active (Streaming audio to mouse)")
            if self.on_status_change:
                self.on_status_change("Music Sync active! Visualizing audio to GM333 mouse LEDs.", True)

    def _on_sens_changed(self, widget):
        val = widget.get_value()
        self.engine.set_sensitivity(val)

    def _on_fps_changed(self, widget):
        val = widget.get_value()
        self.engine.set_fps(val)

    def _on_palette_clicked(self, widget, pkey):
        self.engine.set_palette(pkey)
        self._update_active_palette_ui(pkey)
        if self.on_status_change:
            pname = PALETTES[pkey]["name"]
            self.on_status_change(f"Switched rhythm color palette to: {pname}", True)

    def _update_active_palette_ui(self, active_key):
        for k, btn in self.palette_buttons.items():
            if k == active_key:
                btn.get_style_context().add_class("active-mode")
            else:
                btn.get_style_context().remove_class("active-mode")

    def _on_engine_update(self, rms, norm, is_beat, status, sink_name):
        self.rms = rms
        self.norm = norm
        if is_beat:
            self.is_beat = True
            self.beat_pulse = 1.0

        if norm > self.peak_norm:
            self.peak_norm = norm

        self.current_sink = sink_name
        self.lbl_sink.set_text(f"Audio Source: {sink_name}")
        self.lbl_rms.set_text(f"RMS Level: {rms:.0f} ({(norm * 100):.0f}%)")
        self.lbl_state.set_text(f"Status: {status}")
        self.lbl_beat_badge.set_visible(self.beat_pulse > 0.4)
        return False

    def _on_anim_tick(self):
        # Smooth decay of beat pulse and peak hold
        if self.beat_pulse > 0.05:
            self.beat_pulse *= 0.88
        else:
            self.beat_pulse = 0.0
            self.is_beat = False

        if self.peak_norm > 0.02:
            self.peak_norm *= 0.96

        self.canvas.queue_draw()
        return True

    def _on_draw_canvas(self, widget, cr):
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()

        # Background
        cr.set_source_rgb(0.05, 0.06, 0.09)
        cr.rectangle(0, 0, width, height)
        cr.fill()

        # Grid lines
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.04)
        cr.set_line_width(1)
        for y in range(20, height, 20):
            cr.move_to(0, y)
            cr.line_to(width, y)
            cr.stroke()

        # Meter dimensions
        margin_x = 24
        meter_w = width - (margin_x * 2) - 80
        meter_h = 24
        meter_y = (height - meter_h) / 2

        # 1. Base meter bar track
        cr.set_source_rgba(0.12, 0.14, 0.20, 0.8)
        cr.rectangle(margin_x, meter_y, meter_w, meter_h)
        cr.fill()

        # 2. Glowing level bar (Cyan -> Purple -> Magenta)
        fill_w = max(0.0, min(1.0, self.norm)) * meter_w
        if fill_w > 0:
            pat = cairo.LinearGradient(margin_x, 0, margin_x + meter_w, 0)
            pat.add_color_stop_rgb(0.0, 0.0, 0.9, 1.0)    # Neon cyan
            pat.add_color_stop_rgb(0.5, 0.47, 0.16, 0.79) # Purple
            pat.add_color_stop_rgb(1.0, 1.0, 0.0, 0.5)    # Magenta
            cr.set_source(pat)
            cr.rectangle(margin_x, meter_y, fill_w, meter_h)
            cr.fill()

        # 3. Peak hold marker
        peak_x = margin_x + (min(1.0, self.peak_norm) * meter_w)
        cr.set_source_rgba(1.0, 0.2, 0.4, 0.9)
        cr.set_line_width(3)
        cr.move_to(peak_x, meter_y - 2)
        cr.line_to(peak_x, meter_y + meter_h + 2)
        cr.stroke()

        # 4. Animated Beat Pulse Circle Indicator
        beat_center_x = width - margin_x - 30
        beat_center_y = height / 2
        base_radius = 16
        pulse_extra = self.beat_pulse * 14

        # Outer glowing halo
        if self.beat_pulse > 0.01:
            cr.set_source_rgba(1.0, 0.0, 0.5, 0.3 * self.beat_pulse)
            cr.arc(beat_center_x, beat_center_y, base_radius + pulse_extra, 0, 2 * math.pi)
            cr.fill()

        # Inner ring
        cr.set_source_rgba(0.0, 0.9, 1.0, 0.4 + 0.6 * self.beat_pulse)
        cr.set_line_width(2.5)
        cr.arc(beat_center_x, beat_center_y, base_radius, 0, 2 * math.pi)
        cr.stroke()

        # Center core
        if self.beat_pulse > 0.05:
            cr.set_source_rgba(1.0, 0.0, 0.5, self.beat_pulse)
            cr.arc(beat_center_x, beat_center_y, 7, 0, 2 * math.pi)
            cr.fill()

        return False
