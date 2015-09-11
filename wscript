# -*- python -*-
VERSION = '2.0'
APPNAME = 'hamster-time-tracker'
top = '.'
out = 'build'

import intltool, gnome
import os

def configure(conf):
    conf.check_tool('python')
    conf.check_tool('misc')
    conf.check_python_version((2,4,2))

    conf.check_tool('gnome intltool dbus')

    conf.define('ENABLE_NLS', 1)
    conf.define('HAVE_BIND_TEXTDOMAIN_CODESET', 1)

    conf.define('VERSION', VERSION)
    conf.define('GETTEXT_PACKAGE', "hamster-time-tracker")
    conf.define('PACKAGE', "hamster-time-tracker")
    conf.define('PYEXECDIR', conf.env["PYTHONDIR"]) # i don't know the difference

    # avoid case when we want to install globally (prefix=/usr) but sysconfdir
    # was not specified
    if conf.env['SYSCONFDIR'] == '/usr/etc':
        conf.define('SYSCONFDIR', '/etc')
    else:
        conf.define('SYSCONFDIR', conf.env['SYSCONFDIR'])

    conf.define('prefix', conf.env["PREFIX"]) # to keep compatibility for now

    conf.sub_config("help")


def set_options(opt):
    # options for disabling pyc or pyo compilation
    opt.tool_options("python")
    opt.tool_options("misc")
    opt.tool_options("gnu_dirs")


def build(bld):
    bld.install_files('${LIBDIR}/hamster-time-tracker',
                      """src/hamster-service
                         src/hamster-windows-service
                      """,
                      chmod = 0755)

    bld.install_as('${BINDIR}/hamster', "src/hamster-cli", chmod = 0755)


    bld.install_files('${SYSCONFDIR}/bash_completion.d','src/hamster.bash')


    # set correct flags in defs.py
    bld.new_task_gen("subst",
                     source= "src/hamster/defs.py.in",
                     target= "src/hamster/defs.py",
                     install_path="${PYTHONDIR}/hamster",
                     dict = bld.env
                    )

    bld.install_files('${PYTHONDIR}/hamster', 'src/hamster/*.py')
    for folder in ("lib", "storage", "widgets"):
        bld.install_files('${PYTHONDIR}/hamster/%s' % folder,
                          'src/hamster/%s/*.py' % folder)

    bld.new_task_gen("subst",
                     source= "org.gnome.hamster.service.in",
                     target= "org.gnome.hamster.service",
                     install_path="${DATADIR}/dbus-1/services",
                     dict = bld.env
                    )
    bld.new_task_gen("subst",
                     source= "org.gnome.hamster.Windows.service.in",
                     target= "org.gnome.hamster.Windows.service",
                     install_path="${DATADIR}/dbus-1/services",
                     dict = bld.env
                    )

    bld.add_subdirs("po help data")


    def post(ctx):
        # Postinstall tasks:
        # gnome.postinstall_scrollkeeper('hamster-time-tracker') # Installing the user docs
        gnome.postinstall_schemas('hamster-time-tracker') # Installing GConf schemas
        gnome.postinstall_icons() # Updating the icon cache


    bld.add_post_fun(post)
