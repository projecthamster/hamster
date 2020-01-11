import gi

from hamster.lib import default_logger


logger = default_logger(__name__)
gi.require_version('Gtk', '3.0')
gi.require_version('PangoCairo', '1.0')
