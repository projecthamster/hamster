SUBDIRS = art

if GCONF_SCHEMAS_INSTALL
install-data-local:
	GCONF_CONFIG_SOURCE=$(GCONF_SCHEMA_CONFIG_SOURCE) \
	$(GCONFTOOL) --makefile-install-rule $(schema_DATA)
endif

serverdir = $(libdir)/bonobo/servers

server_DATA = Hamster_Applet.server

hamsterbindir = $(libdir)/hamster-applet

schemadir       = $(GCONF_SCHEMA_FILE_DIR)
schema_in_files = Hamster_Applet.schemas
schema_DATA = Hamster_Applet.schemas

$(server_DATA): $(server_DATA:.server=.server.in)
	sed -e "s|\@LIBEXECDIR\@|$(hamsterbindir)|" $< > $@

resourcesdir = $(pkgdatadir)
resources_DATA = \
	activities.glade \
	overview.glade \
	add_custom_fact.glade \
        menu.glade \
	Hamster_Applet.xml \
	hamster.db


DISTCLEANFILES = \
	$(schema_DATA)		\
	$(server_in_files) \
	$(server_DATA)

EXTRA_DIST = \
	Hamster_Applet.server.in \
	$(resources_DATA) \
	$(schema_in_files)
	
	
