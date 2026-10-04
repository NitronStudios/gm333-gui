#!/usr/bin/env python3
"""
Entry point when running python3 -m gm333gui.
"""

import sys
import signal
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from .app import GM333App

def main():
    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    win = GM333App()
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
