try:
    from ._keybinder import *
except ImportError:
    # running uninstalled?
    import os
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '.libs'))
    print sys.path
    try:
        from _keybinder import *
    finally:
        sys.path.pop()
