# -*- coding: utf-8 -*-

# Copyright (C) 2024 Hamster Contributors

# This file is part of Project Hamster.

# Project Hamster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Project Hamster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Project Hamster.  If not, see <http://www.gnu.org/licenses/>.

"""
Theme management for Hamster.

Provides semantic color palettes for light and dark themes,
with support for auto-detecting system theme preference.
"""

from dataclasses import dataclass, field
from typing import List

from gi.repository import Gio as gio
from gi.repository import GObject as gobject
from gi.repository import Gtk as gtk


@dataclass
class ThemePalette:
    """Semantic color palette for theming."""

    # Backgrounds
    bg_primary: str
    bg_secondary: str

    # Text colors
    fg_primary: str
    fg_secondary: str
    fg_muted: str

    # Tags
    tag_bg: str
    tag_fg: str = "#1e1e1e"

    # Current time indicator
    current_time: str = "#ff0000"

    # Bar chart colors
    bar_colors: List[str] = field(default_factory=list)


# Light theme palette
LIGHT_PALETTE = ThemePalette(
    bg_primary="#ffffff",
    bg_secondary="#eeeeee",
    fg_primary="#333333",
    fg_secondary="#666666",
    fg_muted="#aaaaaa",
    tag_bg="#F1EAAA",
    tag_fg="#1e1e1e",
    current_time="#ff0000",
    bar_colors=["#95CACF", "#A2CFB6", "#D1DEA1", "#E4C384", "#DE9F7B"],
)

# Dark theme palette
DARK_PALETTE = ThemePalette(
    bg_primary="#1e1e1e",
    bg_secondary="#2d2d2d",
    fg_primary="#e0e0e0",
    fg_secondary="#a0a0a0",
    fg_muted="#666666",
    tag_bg="#5C5830",
    tag_fg="#e0e0e0",
    current_time="#ff6b6b",
    bar_colors=["#4DB6BD", "#5DBF8A", "#B8C955", "#D4A84F", "#C87B5A"],
)


class ThemeManager(gobject.GObject):
    """
    Singleton manager for application theming.

    Reads theme preference from GSettings, detects system theme,
    and provides the appropriate color palette.

    Emits 'changed' signal when the theme changes.
    """

    __gsignals__ = {
        "changed": (gobject.SignalFlags.RUN_LAST, gobject.TYPE_NONE, ()),
    }

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        gobject.GObject.__init__(self)
        self._initialized = True

        self._settings = gio.Settings(schema_id='org.gnome.Hamster')
        self._settings.connect('changed::theme-mode', self._on_settings_changed)

        # Listen for system theme changes
        self._gtk_settings = gtk.Settings.get_default()
        if self._gtk_settings:
            self._gtk_settings.connect('notify::gtk-application-prefer-dark-theme',
                                       self._on_system_theme_changed)
            self._gtk_settings.connect('notify::gtk-theme-name',
                                       self._on_system_theme_changed)

        self._cached_is_dark = None
        # Apply initial theme
        self._apply_gtk_theme()

    @property
    def theme_mode(self) -> str:
        """Get the current theme mode setting ('auto', 'light', or 'dark')."""
        return self._settings.get_string('theme-mode')

    @theme_mode.setter
    def theme_mode(self, value: str):
        """Set the theme mode ('auto', 'light', or 'dark')."""
        if value not in ('auto', 'light', 'dark'):
            raise ValueError(f"Invalid theme mode: {value}")
        self._settings.set_string('theme-mode', value)

    @property
    def is_dark(self) -> bool:
        """Determine if dark theme should be used."""
        mode = self.theme_mode
        if mode == 'light':
            return False
        if mode == 'dark':
            return True
        # Auto mode - detect from system
        return self._detect_system_dark_theme()

    def _detect_system_dark_theme(self) -> bool:
        """Detect if the system prefers dark theme."""
        if not self._gtk_settings:
            return False

        # Check explicit dark theme preference
        if self._gtk_settings.get_property('gtk-application-prefer-dark-theme'):
            return True

        # Check theme name for common dark theme indicators
        theme_name = self._gtk_settings.get_property('gtk-theme-name') or ''
        theme_lower = theme_name.lower()
        dark_indicators = ['dark', 'noir', 'night', 'inverse']
        return any(indicator in theme_lower for indicator in dark_indicators)

    @property
    def colors(self) -> ThemePalette:
        """Get the current theme's color palette."""
        return DARK_PALETTE if self.is_dark else LIGHT_PALETTE

    def _apply_gtk_theme(self):
        """Apply the current theme to GTK settings."""
        if not self._gtk_settings:
            return

        mode = self.theme_mode
        if mode == 'auto':
            # In auto mode, don't override GTK's theme preference
            # (it will follow the system)
            return

        # For explicit light/dark, set GTK's preference
        prefer_dark = (mode == 'dark')
        self._gtk_settings.set_property('gtk-application-prefer-dark-theme', prefer_dark)

    def _on_settings_changed(self, settings, key):
        """Handle theme-mode GSettings change."""
        self._cached_is_dark = None
        self._apply_gtk_theme()
        self.emit('changed')

    def _on_system_theme_changed(self, settings, pspec):
        """Handle system theme change."""
        if self.theme_mode == 'auto':
            new_is_dark = self.is_dark
            if self._cached_is_dark != new_is_dark:
                self._cached_is_dark = new_is_dark
                self.emit('changed')


# Module-level singleton instance
_theme_manager = None


def get_theme_manager() -> ThemeManager:
    """Get the singleton ThemeManager instance."""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager


# Convenience alias
theme = get_theme_manager
