CPPFLAGS = $(PYTHON_INCLUDES) $(HAMSTER_CFLAGS)

_keybinderdir = $(pyexecdir)/hamster/keybinder
_keybinder_LTLIBRARIES = _keybinder.la
_keybinder_la_LDFLAGS = -module -avoid-version -export-symbols-regex init_keybinder
_keybinder_la_LIBADD = $(HAMSTER_LIBS)
_keybinder_la_SOURCES = \
	_keybindermodule.c \
	eggaccelerators.c \
	eggaccelerators.h \
	tomboykeybinder.c \
	tomboykeybinder.h

nodist__keybinder_la_SOURCES = _keybinder.c

_keybinder_PYTHON = \
	__init__.py

CLEANFILES = _keybinder.c
EXTRA_DIST = \
	_keybinder.defs \
	_keybinder.override \
	gen-defs.sh

_keybinder.c: _keybinder.defs _keybinder.override
.defs.c:
	$(AM_V_GEN)(cd $(srcdir) \
	 && $(PYGTK_CODEGEN) \
	    --override $*.override \
	    --register $(PYGTK_DEFSDIR)/gtk-types.defs \
	    --register $(PYGTK_DEFSDIR)/gdk-types.defs \
	    --prefix py$* $*.defs) > gen-$*.c \
	&& cp gen-$*.c $*.c \
	&& rm -f gen-$*.c

