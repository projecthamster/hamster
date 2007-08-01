SUBDIRS =

hamster-applet: hamster-applet.py
	sed -e "s|\@PYTHONDIR\@|$(pythondir)/hamster|" $< > $@

hamsterbindir = $(libdir)/hamster-applet
hamsterbin_SCRIPTS = hamster-applet

hamsterdir = $(pythondir)/hamster
hamster_PYTHON = \
	defs.py \
	db.py \
	activities.py \
	overview.py \
	HamsterApplet.py \
	About.py \
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
