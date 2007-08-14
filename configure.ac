AC_INIT(hamster-applet, 0.1.2, toms.baugis@gmail.com)
AC_CONFIG_SRCDIR(hamster/__init__.py)
AC_CONFIG_HEADERS(config.h)
AC_CONFIG_MACRO_DIR([m4])

AM_INIT_AUTOMAKE
GNOME_COMMON_INIT

AM_MAINTAINER_MODE
AM_DISABLE_STATIC
AM_PROG_LIBTOOL
AC_SUBST(ACLOCAL_AMFLAGS, "$ACLOCAL_FLAGS -I m4")
AC_PROG_CC

dnl ****************************************************************************
dnl * Pkg-Config
dnl ****************************************************************************
AC_CHECK_PROG(HAVE_PKGCONFIG, pkg-config, yes, no)
if test "x$HAVE_PKGCONFIG" = "xno"; then
  AC_MSG_ERROR(you need to have pkgconfig installed !)
fi

dnl ****************************************************************************
dnl * Python 2.4
dnl ****************************************************************************
AM_PATH_PYTHON(2.4)
AM_CHECK_PYTHON_HEADERS(,[AC_MSG_ERROR(could not find Python headers)])

dnl ****************************************************************************
dnl * Write the values of various paths in defs.py
dnl ****************************************************************************
AC_SUBST(VERSION)
AC_SUBST(PACKAGE)

AS_AC_EXPAND(DATADIR, $datarootdir)
AC_SUBST(DATADIR)

AS_AC_EXPAND(LIBDIR, $libdir)
AC_SUBST(LIBDIR)

AS_AC_EXPAND(PYTHONDIR, $pythondir)
AC_SUBST(PYTHONDIR)

dnl ****************************************************************************
dnl * PyGTK & co for Gnome Streamer
dnl ****************************************************************************
PKG_CHECK_MODULES(HAMSTER,
    pygtk-2.0               >= 2.6
    pygobject-2.0           >= 2.6
)
AC_SUBST(HAMSTER_CFLAGS)
AC_SUBST(HAMSTER_LIBS)

AC_MSG_CHECKING([for gnomeapplet module])
if AC_RUN_LOG([DISPLAY= $PYTHON -c '
try:
    import gnomeapplet
except ImportError, e:
    if str(e).find("gnomeapplet") >= 0:
          raise
except:
    pass
']); then
  AC_MSG_RESULT([yes])
else
  AC_MSG_RESULT([no])
  AC_MSG_ERROR([gnomeapplet Python module required to build hamster])
fi

AC_MSG_CHECKING([for pysqlite2 module])
if AC_RUN_LOG([DISPLAY= $PYTHON -c '
try:
    import pysqlite2
except ImportError, e:
    if str(e).find("pysqlite2") >= 0:
          raise
except:
    pass
']); then
  AC_MSG_RESULT([yes])
else
  AC_MSG_RESULT([no])
  AC_MSG_ERROR([pysqlite2 Python module required to build hamster])
fi





dnl ****************************************************************************
dnl * --------------------------------------------------------------------------
dnl ****************************************************************************
AC_OUTPUT([
Makefile
hamster/Makefile
hamster/defs.py
data/Makefile
data/art/Makefile
])

echo
echo $PACKAGE v$VERSION
echo

echo Prefix............... : $prefix

echo "Now type make to compile"
echo "Then su to root and type: make install"
echo
