SUBDIRS = hamster
ACLOCAL_AMFLAGS = -I m4

CPPFLAGS = \
	$(PYTHON_INCLUDES)

hamsterlibdir = $(libdir)/hamster-applet
hamsterlib_SCRIPTS = hamster-applet


hamsterbindir = $(bindir)
hamsterbin_SCRIPTS = \
	hamster-standalone \
	gnome-time-tracker \
	hamster-client \
        hamster-service

DISTCLEANFILES = \
	$(CLEANFILES)

EXTRA_DIST = \
	hamster-applet \
	hamster-standalone \
	gnome-time-tracker \
	hamster-client \
	hamster-service
