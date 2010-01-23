SUBDIRS = hamster
ACLOCAL_AMFLAGS = -I m4

CPPFLAGS = \
	$(PYTHON_INCLUDES)

hamster-applet: hamster-applet.py
	$(AM_V_GEN)sed -e "s|\@PYTHONDIR\@|$(pyexecdir)|" $< > $@

hamsterlibdir = $(libdir)/hamster-applet
hamsterlib_SCRIPTS = hamster-applet


hamsterbindir = $(bindir)
hamsterbin_SCRIPTS = \
	hamster-standalone \
	gnome-time-tracker

BUILT_SOURCES = \
	hamster-applet

CLEANFILES = \
	$(BUILT_SOURCES)

DISTCLEANFILES = \
	$(CLEANFILES)

EXTRA_DIST = \
	hamster-applet.py \
	hamster-standalone \
	gnome-time-tracker
