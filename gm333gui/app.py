#!/usr/bin/env python3
"""
Main GTK Application Window for Ant Esports GM333 Gaming Mouse.
"""

import os
import sys
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf

from .controller import GM333Controller
from .ui_lighting import LightingView
from .ui_music import MusicSyncView
from .ui_info import InfoView

class GM333App(Gtk.ApplicationWindow):
    def __init__(self, app=None):
        super().__init__(application=app, title="Ant Esports GM333 Control Panel")
        self.set_default_size(960, 680)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.get_style_context().add_class("main-window")

        # Hardware controller
        self.controller = GM333Controller()

        # Load App Icon & CSS
        self._load_icon()
        self._load_css()

        # Build UI
        self._build_headerbar()
        self._build_content()
        self._build_statusbar()

        # Connect window destroy
        self.connect("destroy", self._on_window_destroy)

        # Periodic hardware polling (detect plug/unplug)
        GLib.timeout_add_seconds(3, self._poll_device)

    def _load_icon(self):
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
        icon_path = os.path.join(assets_dir, "gm333.png")
        if os.path.exists(icon_path):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(icon_path, 128, 128, True)
                self.set_icon(pixbuf)
                Gtk.Window.set_default_icon(pixbuf)
            except Exception:
                pass

    def _load_css(self):
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
        css_path = os.path.join(assets_dir, "style.css")
        if os.path.exists(css_path):
            provider = Gtk.CssProvider()
            try:
                provider.load_from_path(css_path)
                screen = Gdk.Screen.get_default()
                Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            except Exception as e:
                print(f"Error loading CSS: {e}", file=sys.stderr)

    def _build_headerbar(self):
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title("Ant Esports GM333")
        header.set_subtitle("Lighting & Music Sync")

        # App Icon in header
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
        icon_path = os.path.join(assets_dir, "gm333-48.png")
        if os.path.exists(icon_path):
            try:
                pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(icon_path, 28, 28, True)
                img = Gtk.Image.new_from_pixbuf(pb)
                img.set_margin_start(4)
                img.set_margin_end(6)
                header.pack_start(img)
            except Exception:
                pass

        # Device connection status pill in HeaderBar
        self.lbl_head_status = Gtk.Label(label="Checking...")
        self._update_header_status_badge()
        header.pack_start(self.lbl_head_status)

        # Tabs stack switcher in center
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(180)

        switcher = Gtk.StackSwitcher()
        switcher.set_stack(self.stack)
        switcher.get_style_context().add_class("custom-stack-switcher")
        header.set_custom_title(switcher)

        # About button
        btn_about = Gtk.Button()
        btn_about.set_image(Gtk.Image.new_from_icon_name("help-about-symbolic", Gtk.IconSize.MENU))
        btn_about.set_tooltip_text("About Ant Esports GM333")
        btn_about.connect("clicked", self._show_about_dialog)
        header.pack_end(btn_about)

        self.set_titlebar(header)

    def switch_to_music_tab(self):
        self.stack.set_visible_child_name("music")
        if not self.view_music.engine.is_running:
            self.view_music.start_music_sync()

    def _build_content(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # 2. Music Sync View Tab (instantiated first for callback binding)
        self.view_music = MusicSyncView(self.controller, on_status_change=self.set_status_message)

        # 1. Lighting View Tab
        self.view_lighting = LightingView(
            self.controller,
            on_status_change=self.set_status_message,
            on_switch_to_music=self.switch_to_music_tab,
            on_lighting_applied=lambda: self.view_music.stop_music_sync(restore_neon=False)
        )

        self.stack.add_titled(self.view_lighting, "lighting", "🌈 Lighting Modes")
        self.stack.add_titled(self.view_music, "music", "🎵 Music Sync")

        # 3. Device Info & Udev Tab
        self.view_info = InfoView(self.controller, on_status_change=self.set_status_message)
        self.stack.add_titled(self.view_info, "info", "ℹ️ Device & Info")

        # Automatically start music sync when switching to music tab, and stop when leaving
        self.stack.connect("notify::visible-child-name", self._on_tab_changed)

        main_box.pack_start(self.stack, True, True, 0)
        self.add(main_box)

    def _on_tab_changed(self, stack, param):
        child_name = stack.get_visible_child_name()
        if child_name == "music":
            self.view_music.start_music_sync()
        elif child_name == "lighting":
            self.view_music.stop_music_sync(restore_neon=False)
            self.view_lighting.apply_current_settings()

    def _build_statusbar(self):
        bar_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        bar_box.get_style_context().add_class("glass-card")
        bar_box.set_margin_start(16)
        bar_box.set_margin_end(16)
        bar_box.set_margin_bottom(12)
        bar_box.set_margin_top(4)

        self.lbl_status = Gtk.Label(label="Ready • GM333 Hardware Controller Initialized")
        self.lbl_status.set_halign(Gtk.Align.START)
        self.lbl_status.get_style_context().add_class("mode-desc")
        bar_box.pack_start(self.lbl_status, True, True, 0)

        self.lbl_mode_indicator = Gtk.Label(label="Mode: Neon Wave")
        self.lbl_mode_indicator.get_style_context().add_class("mode-desc")
        bar_box.pack_end(self.lbl_mode_indicator, False, False, 0)

        # Pack into bottom of window
        child = self.get_child()
        if isinstance(child, Gtk.Box):
            child.pack_end(bar_box, False, False, 0)

    def set_status_message(self, text, is_ok=True):
        prefix = "✓ " if is_ok else "✗ "
        self.lbl_status.set_text(prefix + text)
        if "applied" in text:
            self.lbl_mode_indicator.set_text(text.split("(")[0].strip())

    def _update_header_status_badge(self):
        self.controller.detect_device()
        if self.controller.is_connected and self.controller.has_permission:
            self.lbl_head_status.set_text("GM333 Connected")
            self.lbl_head_status.get_style_context().remove_class("status-badge-disconnected")
            self.lbl_head_status.get_style_context().add_class("status-badge-connected")
        elif self.controller.is_connected and not self.controller.has_permission:
            self.lbl_head_status.set_text("Missing Permissions")
            self.lbl_head_status.get_style_context().remove_class("status-badge-connected")
            self.lbl_head_status.get_style_context().add_class("status-badge-disconnected")
        else:
            self.lbl_head_status.set_text("Disconnected")
            self.lbl_head_status.get_style_context().remove_class("status-badge-connected")
            self.lbl_head_status.get_style_context().add_class("status-badge-disconnected")

    def _poll_device(self):
        was_conn = self.controller.is_connected
        self._update_header_status_badge()
        if was_conn != self.controller.is_connected:
            self.view_info.refresh_info()
            if self.controller.is_connected:
                self.set_status_message("GM333 mouse reconnected!", True)
            else:
                self.set_status_message("GM333 mouse unplugged.", False)
        return True

    def _show_about_dialog(self, widget):
        about = Gtk.AboutDialog()
        about.set_transient_for(self)
        about.set_program_name("Ant Esports GM333 Controller")
        about.set_version("1.0.0")
        about.set_comments(
            "Native Linux GUI for Ant Esports GM333 Gaming Mouse.\n"
            "Control 16 onboard hardware lighting modes and live audio-reactive Music Sync.\n"
            "Compatible across Arch Linux, Ubuntu, Fedora, Debian, and openSUSE."
        )
        about.set_website("https://github.com")
        about.set_website_label("GitHub Project")
        about.set_authors(["Reverse-engineered & developed for Linux gaming"])

        assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
        icon_path = os.path.join(assets_dir, "gm333.png")
        if os.path.exists(icon_path):
            try:
                about.set_logo(GdkPixbuf.Pixbuf.new_from_file_at_scale(icon_path, 96, 96, True))
            except Exception:
                pass

        about.run()
        about.destroy()

    def _on_window_destroy(self, widget):
        # Stop music visualizer engine cleanly
        if hasattr(self, "view_music") and self.view_music.engine.is_running:
            self.view_music.engine.stop()
        Gtk.main_quit()
