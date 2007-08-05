SUBDIRS = art

serverdir = $(libdir)/bonobo/servers

server_DATA = Hamster_Applet.server

hamsterbindir = $(libdir)/hamster-applet

$(server_DATA): $(server_DATA:.server=.server.in)
	sed -e "s|\@LIBEXECDIR\@|$(hamsterbindir)|" $< > $@

resourcesdir = $(pkgdatadir)
resources_DATA = \
	activities.glade \
	overview.glade \
	Hamster_Applet.xml \
	hamster.db


DISTCLEANFILES = \
	$(server_in_files) \
	$(server_DATA)

EXTRA_DIST = \
	Hamster_Applet.server.in \
	$(resources_DATA) \
	$(server_DATA)


