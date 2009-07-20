SUBDIRS = keybinder
ACLOCAL_AMFLAGS = -I m4

CPPFLAGS = \
	$(PYTHON_INCLUDES) 

hamster-applet: hamster-applet.py
	sed -e "s|\@PYTHONDIR\@|$(pyexecdir)|" $< > $@

hamsterbindir = $(libdir)/hamster-applet
hamsterbin_SCRIPTS = hamster-applet

hamsterdir = $(pyexecdir)/hamster
hamster_PYTHON = \
	defs.py \
	dispatcher.py \
	storage.py \
	db.py \
	eds.py \
	stats.py \
	reports.py \
	charting.py \
        widgets.py \
        graphics.py \
	configuration.py \
	KeyBinder.py \
	preferences.py \
	stuff.py \
	edit_activity.py \
	applet.py \
	about.py \
	hamsterdbus.py \
	idle.py \
        i18n.py \
	__init__.py

BUILT_SOURCES = \
	hamster-applet

CLEANFILES = \
	$(BUILT_SOURCES)

DISTCLEANFILES = \
	defs.py \
	$(CLEANFILES)

EXTRA_DIST = \
	defs.py.in \
	hamster-applet.py
