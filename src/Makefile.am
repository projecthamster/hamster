SUBDIRS = hamster
ACLOCAL_AMFLAGS = -I m4

CPPFLAGS = \
	$(PYTHON_INCLUDES)

hamster-applet: hamster-applet.py
	$(AM_V_GEN)sed -e "s|\@PYTHONDIR\@|$(pyexecdir)|" $< > $@

hamsterbindir = $(libdir)/hamster-applet
hamsterbin_SCRIPTS = hamster-applet

BUILT_SOURCES = \
	hamster-applet

CLEANFILES = \
	$(BUILT_SOURCES)

DISTCLEANFILES = \
	$(CLEANFILES)

EXTRA_DIST = \
	hamster-applet.py
