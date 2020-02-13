# -*- python -*-

# slight code duplication with hamster/__init__.py, but this is finally cleaner.
from subprocess import getstatusoutput
rc, output = getstatusoutput("git describe --tags --always --dirty=+")
VERSION = "3.0-beta" if rc else output

APPNAME = 'hamster'

top = '.'
out = 'build'

import os
from waflib import Logs, Utils


def configure(conf):
    conf.load('gnu_dirs')  # for DATADIR
    conf.load('glib2')  # for GSettings support
    conf.load('python')
    conf.check_python_version(minver=(3,4,0))

    conf.load('intltool')

    conf.env.ENABLE_NLS = 1
    conf.env.HAVE_BIND_TEXTDOMAIN_CODESET = 1

    conf.env.VERSION = VERSION
    conf.env.GETTEXT_PACKAGE = "hamster"
    conf.env.PACKAGE = "hamster"

    conf.env.build_i18n = conf.options.build_i18n
    conf.find_program('xgettext', var='XGETTEXT')
    conf.find_program('msgmerge', var='MSGMERGE')

    conf.recurse("help")


def options(opt):
    opt.load('gnu_dirs')

    # the waf default value is /usr/local, which causes issues (e.g. #309)
    # opt.parser.set_defaults(prefix='/usr') did not update the help string,
    # hence need to replace the whole option
    opt.parser.remove_option('--prefix')
    default_prefix = '/usr'
    opt.add_option('--prefix', dest='prefix', default=default_prefix,
                   help='installation prefix [default: {}]'.format(default_prefix))
    opt.add_option('--build-i18n', dest='build_i18n',
                   action='store_true', default=False,
                   help='rebuild .po template and files')


def build_i18n(bld):
    # 1. Generate the .pot template from the sources using xgettext
    #    We must prepend "../" to the paths in POTFILES.in to help
    #    xgettext find them
    p_in = bld.path.find_node('po/POTFILES.in')
    i18n_sources = [ p for p in p_in.read().split("\n")
                     if p != "" and not p.startswith('#') ]
    bld(rule='${XGETTEXT} -o ${TGT} --from-code=UTF-8 --add-comments %s'
        % ' '.join([ os.path.join("..", x) for x in i18n_sources]),
        source='po/POTFILES.in', target='po/hamster.pot')
    for f in i18n_sources:
        r = bld.path.find_resource(f)
        bld.add_manual_dependency(bld.path.find_resource('po/POTFILES.in'), r)

    # 2. Update the .po files with the new template using msgmerge
    #    Tell waf to build the template first (dependency is not enough)
    bld.add_group()
    for po in bld.path.ant_glob('po/*.po'):
        bld(rule='${MSGMERGE} --quiet -o ${TGT} ${SRC} po/hamster.pot',
            target=po.srcpath(), source=po.bldpath())
        # Tell waf that the generated .po files depend on the template
        bld.add_manual_dependency(po, bld.path.find_or_declare('po/hamster.pot'))
        # Tell waf to regenerate .mo files if .po files are changed
        bld.add_manual_dependency(po.change_ext('.mo'), po)

def build(bld):
    bld.install_as('${LIBEXECDIR}/hamster/hamster-service', "src/hamster-service.py", chmod=Utils.O755)
    bld.install_as('${LIBEXECDIR}/hamster/hamster-windows-service', "src/hamster-windows-service.py", chmod=Utils.O755)
    bld.install_as('${BINDIR}/hamster', "src/hamster-cli.py", chmod=Utils.O755)


    bld.install_files('${PREFIX}/share/bash-completion/completions',
                      'src/hamster.bash')

    if bld.env.build_i18n:
        build_i18n(bld)

    bld(features='py',
        source=bld.path.ant_glob('src/hamster/**/*.py'),
        install_from='src')

    # set correct flags in defs.py
    bld(features="subst",
        source="src/hamster/defs.py.in",
        target="src/hamster/defs.py",
        install_path="${PYTHONDIR}/hamster"
        )

    bld(features="subst",
        source= "org.gnome.Hamster.service.in",
        target= "org.gnome.Hamster.service",
        install_path="${DATADIR}/dbus-1/services",
        )

    bld(features="subst",
        source= "org.gnome.Hamster.GUI.service.in",
        target= "org.gnome.Hamster.GUI.service",
        install_path="${DATADIR}/dbus-1/services",
        )

    bld(features="subst",
        source= "org.gnome.Hamster.WindowServer.service.in",
        target= "org.gnome.Hamster.WindowServer.service",
        install_path="${DATADIR}/dbus-1/services",
        )

    bld.recurse("po data help")

    bld(features='glib2',
        settings_schema_files = ['data/org.gnome.hamster.gschema.xml'])

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


    bld.add_post_fun(update_icon_cache)
