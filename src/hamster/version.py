# Should not normally be used directly, use hamster.__version__ and
# hamster.installed instead

def get_version():
    """
    Figure out the hamster version.

    Returns a tuple with the version string and wether we are installed or not.
    """

    try:
        # defs.py is created by waf from defs.py.in
        from hamster import defs
        version = defs.VERSION
        installed = True
    except ImportError:
        # if defs is not there, we are running from sources
        installed = False

        # If available, prefer the git version, otherwise fall back to
        # the VERSION file (which is meaningful only in released
        # versions)
        from subprocess import getstatusoutput
        rc, output = getstatusoutput("git describe --tags --always --dirty=+")
        if rc == 0:
            version = "{} (uninstalled)".format(output)
        else:
            from pathlib import Path
            with open(Path(__file__).parent / 'VERSION', 'r') as f:
                version = f.read()
    return (version, installed)
