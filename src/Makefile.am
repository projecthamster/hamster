SUBDIRS = hamster
ACLOCAL_AMFLAGS = -I m4

CPPFLAGS = \
	$(PYTHON_INCLUDES)

hamster-applet: hamster-applet.py
	$(AM_V_GEN)sed -e "s|\@PYTHONDIR\@|$(pyexecdir)|" $< > $@

hamster-client: hamster-client.py
	$(AM_V_GEN)sed -e "s|__DEBUG__ = True|__DEBUG__ = False|" \
				   -e "s|\@PYTHONDIR\@|$(pyexecdir)|" \
				   $< > $@

hamsterlibdir = $(libdir)/hamster-applet
hamsterlib_SCRIPTS = hamster-applet


hamsterbindir = $(bindir)
hamsterbin_SCRIPTS = \
	hamster-standalone \
	gnome-time-tracker \
	hamster-client

BUILT_SOURCES = \
	hamster-applet \
	hamster-client

CLEANFILES = \
	$(BUILT_SOURCES)

DISTCLEANFILES = \
	$(CLEANFILES)

EXTRA_DIST = \
	hamster-applet.py \
	hamster-standalone \
	gnome-time-tracker \
	hamster-client.py
