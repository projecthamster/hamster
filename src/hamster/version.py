# Should not normally be used directly, use hamster.__version__ and
# hamster.installed instead

def get_installed_version():
    try:
        # defs.py is created by waf from defs.py.in
        from hamster import defs
        return defs.VERSION
    except ImportError:
        # if defs is not there, we are running from sources
        return None

def get_uninstalled_version():
    # If available, prefer the git version, otherwise fall back to
    # the VERSION file (which is meaningful only in released
    # versions)
    from subprocess import getstatusoutput
    rc, output = getstatusoutput("git describe --tags --always --dirty=+")
    if rc == 0:
        import re
        # Strip "v" prefix that is used in git tags
        return re.sub(r'^v', '', output.strip())
    else:
        from pathlib import Path
        with open(Path(__file__).parent / 'VERSION', 'r') as f:
            return f.read().strip()

def get_version():
    """
    Figure out the hamster version.

    Returns a tuple with the version string and wether we are installed or not.
    """

    version = get_installed_version()
    if version is not None:
        return (version, True)

    version = get_uninstalled_version()
    return ("{} (uninstalled)".format(version), False)


if __name__ == '__main__':
    import sys
    # Intended to be called by waf when installing, so only return
    # uninstalled version
    sys.stdout.write(get_uninstalled_version())
