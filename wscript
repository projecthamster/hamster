# -*- python -*-
VERSION = '2.0'
APPNAME = 'hamster-time-tracker'
top = '.'
out = 'build'

import os
from waflib import Logs, Utils


def configure(conf):
    conf.load('gnu_dirs')  # for DATADIR
    
    if conf.options.docs:
        conf.recurse("help")
        return
    
    conf.load('python')
    conf.check_python_version(minver=(3,4,0))

    conf.load('intltool')

    conf.env.ENABLE_NLS = 1
    conf.env.HAVE_BIND_TEXTDOMAIN_CODESET = 1

    conf.env.VERSION = VERSION
    conf.env.GETTEXT_PACKAGE = "hamster-time-tracker"
    conf.env.PACKAGE = "hamster-time-tracker"
    
    # gconf_dir is defined in options
    conf.env.schemas_destination = '{}/schemas'.format(conf.options.gconf_dir)


def options(opt):
    opt.add_option('--gconf-dir', action='store', default='/etc/gconf', dest='gconf_dir',
                   help='gconf base directory [default: /etc/gconf]')
    
    opt.add_option('--docs', action='store_true', default=False, dest='docs',
                   help='build or install documentation instead of the main application')
    
    # the waf default value is /usr/local, which causes issues (e.g. #309)
    # opt.parser.set_defaults(prefix='/usr') did not update the help string,
    # hence need to replace the whole option
    opt.parser.remove_option('--prefix')
    default_prefix = '/usr'
    opt.add_option('--prefix', dest='prefix', default=default_prefix, 
                   help='installation prefix [default: {}]'.format(default_prefix))


def build(bld):
    if bld.options.docs:
        bld.recurse("help")
        return
    
    bld.install_files('${LIBDIR}/hamster-time-tracker',
                      """src/hamster-service
                         src/hamster-windows-service
                      """,
                      chmod=Utils.O755)
    
    bld.install_as('${BINDIR}/hamster', "src/hamster-cli", chmod=Utils.O755)


    bld.install_files('${PREFIX}/share/bash-completion/completion',
                      'src/hamster.bash')


    bld(features='py',
        source=bld.path.ant_glob('src/**/*.py'),
        install_from='src')

    # set correct flags in defs.py
    bld(features="subst",
        source="src/hamster/defs.py.in",
        target="src/hamster/defs.py",
        install_path="${PYTHONDIR}/hamster"
        )

    bld(features="subst",
        source= "org.gnome.hamster.service.in",
        target= "org.gnome.hamster.service",
        install_path="${DATADIR}/dbus-1/services",
        )

    bld(features="subst",
        source= "org.gnome.hamster.Windows.service.in",
        target= "org.gnome.hamster.Windows.service",
        install_path="${DATADIR}/dbus-1/services",
        )
    
    #bld.add_subdirs("po help data")
    bld.recurse("po data")


    def manage_gconf_schemas(ctx, action):
        """Install or uninstall hamster gconf schemas.

        Requires the stored hamster-time-tracker.schemas
        (usually in /etc/gconf/schemas/) to be present.

        Hence install should be a post-fun,
        and uninstall a pre-fun.
        """


        # for some reason the post_fun keep being registered for other builds
        # bypassing the schemas management if the --docs options was given
        if ctx.options.docs:
            return
        
        assert action in ("install", "uninstall")
        if ctx.cmd == action:
            schemas_file = "{}/hamster-time-tracker.schemas".format(ctx.env.schemas_destination)
            cmd = 'GCONF_CONFIG_SOURCE=$(gconftool-2 --get-default-source) gconftool-2 --makefile-{}-rule {} 1> /dev/null'.format(action, schemas_file)
            err = ctx.exec_command(cmd)
            if err:
                Logs.warn('The following  command failed:\n{}'.format(cmd))
            else:
                Logs.pprint('YELLOW', 'Successfully {}ed gconf schemas'.format(action))


    def update_icon_cache(ctx):
        """Update the gtk icon cache."""
        if ctx.cmd == "install":
            # adapted from the previous waf gnome.py
            icon_dir = os.path.join(ctx.env.DATADIR, 'icons/hicolor')
            cmd = 'gtk-update-icon-cache -q -f -t {}'.format(icon_dir)
            err = ctx.exec_command(cmd)
            if err:
                Logs.warn('The following  command failed:\n{}'.format(cmd))
            else:
                Logs.pprint('YELLOW', 'Successfully updated GTK icon cache')


    bld.add_post_fun(lambda bld: manage_gconf_schemas(bld, "install"))
    bld.add_post_fun(update_icon_cache)
    bld.add_pre_fun(lambda bld: manage_gconf_schemas(bld, "uninstall"))
