import gi
gi.require_version('Gtk', '3.0')  # noqa: E402
gi.require_version('PangoCairo', '1.0')  # noqa: E402
# for some reason performance is improved by importing Gtk early
from gi.repository import Gtk as gtk

from hamster.lib import default_logger


logger = default_logger(__name__)

# cleanup namespace
del default_logger
del gtk  # performance is retained
