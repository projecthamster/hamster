# -*- python -*-


from subprocess import getstatusoutput

from waflib import Utils


# slight code duplication with hamster/__init__.py, but this is finally cleaner.
rc, output = getstatusoutput("git describe --tags --always --dirty=+")
VERSION = "3.0.2" if rc else output

APPNAME = 'hamster'

top = '.'
out = 'build'


def options(ctx):
    ctx.load('gnu_dirs')

    # the waf default value is /usr/local, which causes issues (e.g. #309)
    # ctx.parser.set_defaults(prefix='/usr') did not update the help string,
    # hence need to replace the whole option
    ctx.parser.remove_option('--prefix')
    default_prefix = '/usr'
    
    ctx.add_option('--prefix', dest='prefix', default=default_prefix,
                   help='installation prefix [default: {}]'.format(default_prefix))
    
    ctx.add_option('--skip-gsettings', dest='skip_gsettings', action='store_true',
                   help='skip gsettings schemas build and installation (for packagers)')
    
    ctx.add_option('--skip-icon-cache-update', dest='skip_icon_cache_update', action='store_true',
                   help='skip icon cache update (for packagers)')


def configure(ctx):
    ctx.load('gnu_dirs')  # for DATADIR
    
    if not ctx.options.skip_gsettings:
        ctx.load('glib2')  # for GSettings support
    
    ctx.load('python')
    ctx.check_python_version(minver=(3,4,0))

    ctx.load('intltool')

    ctx.env.ENABLE_NLS = 1
    ctx.env.HAVE_BIND_TEXTDOMAIN_CODESET = 1

    ctx.env.VERSION = VERSION
    ctx.env.GETTEXT_PACKAGE = "hamster"
    ctx.env.PACKAGE = "hamster"
    
    ctx.recurse("help")
    
    # options are tied to a specific ./waf invocation (one terminal line),
    # and woud have to be given again at any other ./waf invocation
    # that is trouble when one wants to ./waf uninstall much later;
    # it can be hard to remember the exact options used at the install step.
    # So from now on, options have to be given at the configure step only.
    # copy the options to the persistent env:
    for name in ('prefix', 'skip_gsettings', 'skip_icon_cache_update'):
        value = getattr(ctx.options, name)
        setattr(ctx.env, name, value)
   

def build(ctx):
    ctx.install_as('${LIBEXECDIR}/hamster/hamster-service', "src/hamster-service.py", chmod=Utils.O755)
    ctx.install_as('${LIBEXECDIR}/hamster/hamster-windows-service', "src/hamster-windows-service.py", chmod=Utils.O755)
    ctx.install_as('${BINDIR}/hamster', "src/hamster-cli.py", chmod=Utils.O755)


    ctx.install_files('${PREFIX}/share/bash-completion/completions',
                      'src/hamster.bash')


    ctx(features='py',
        source=ctx.path.ant_glob('src/hamster/**/*.py'),
        install_from='src')

    # set correct flags in defs.py
    ctx(features="subst",
        source="src/hamster/defs.py.in",
        target="src/hamster/defs.py",
        install_path="${PYTHONDIR}/hamster"
        )

    ctx(features="subst",
        source= "org.gnome.Hamster.service.in",
        target= "org.gnome.Hamster.service",
        install_path="${DATADIR}/dbus-1/services",
        )

    ctx(features="subst",
        source= "org.gnome.Hamster.GUI.service.in",
        target= "org.gnome.Hamster.GUI.service",
        install_path="${DATADIR}/dbus-1/services",
        )

    ctx(features="subst",
        source= "org.gnome.Hamster.WindowServer.service.in",
        target= "org.gnome.Hamster.WindowServer.service",
        install_path="${DATADIR}/dbus-1/services",
        )

    # look for wscript into further directories
    ctx.recurse("po data help")
