SUBDIRS = keybinder

hamster-applet: hamster-applet.py
	sed -e "s|\@PYTHONDIR\@|$(pythondir)/hamster|" $< > $@

hamsterbindir = $(libdir)/hamster-applet
hamsterbin_SCRIPTS = hamster-applet

hamsterdir = $(pythondir)/hamster
hamster_PYTHON = \
	defs.py \
	dispatcher.py \
	storage.py \
	db.py \
	eds.py \
	stats.py \
	charting.py \
	Configuration.py \
	KeyBinder.py \
	activities.py \
	stuff.py \
	add_custom_fact.py \
	applet.py \
	about.py \
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
