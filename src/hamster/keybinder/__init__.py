try:
    from ._keybinder import *
except ImportError:
    # running uninstalled?
    import os
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '.libs'))
    try:
        from _keybinder import *
    finally:
        sys.path.pop()
