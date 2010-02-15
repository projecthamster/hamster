try:
    from _keybinder import tomboy_keybinder_bind as bind
    from _keybinder import tomboy_keybinder_unbind as unbind
except ImportError:
    # running uninstalled?
    import os
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '.libs'))
    try:
        from _keybinder import tomboy_keybinder_bind as bind
        from _keybinder import tomboy_keybinder_unbind as unbind
    finally:
        sys.path.pop()
