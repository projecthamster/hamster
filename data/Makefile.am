SUBDIRS = art

# ******************************************************************************
# Panel applet bonobo stuff
# ******************************************************************************
serverdir = $(libdir)/bonobo/servers
server_in_files = Hamster_Applet.server.in
server_DATA = $(server_in_files:.server.in=.server)

# ******************************************************************************
# GConf Schemas
# ******************************************************************************
# GConf Preference Schemas
schemadir = $(GCONF_SCHEMA_FILE_DIR)
schema_in_files = hamster-applet.schemas.in
schema_DATA = $(schema_in_files:.schemas.in=.schemas)

# ******************************************************************************
# Misc data
# ******************************************************************************
resourcesdir = $(pkgdatadir)
resources_DATA = \
	Hamster_Applet.xml \
	preferences.glade \
	stats.glade \
	add_custom_fact.glade \
    menu.glade \
	hamster.db

xmldir       = $(KEYBINDINGS_DIR)
xml_in_files = 99-hamster-applet.xml.in
xml_DATA     = $(xml_in_files:.xml.in=.xml)

hamsterbindir = $(libdir)/hamster-applet

# ******************************************************************************
# Build rules
# ******************************************************************************
@INTLTOOL_DESKTOP_RULE@
@INTLTOOL_SERVER_RULE@
@INTLTOOL_SCHEMAS_RULE@
@INTLTOOL_XML_RULE@

$(server_in_files): $(server_in_files:.server.in=.server.in.in)
	sed -e "s|\@LIBEXECDIR\@|$(hamsterbindir)|" $< > $@

if GCONF_SCHEMAS_INSTALL
install-data-local: install-schemas
install-schemas:
	GCONF_CONFIG_SOURCE=$(GCONF_SCHEMA_CONFIG_SOURCE) \
		$(GCONFTOOL) --makefile-install-rule $(schema_DATA)
endif

DISTCLEANFILES = \
	$(schema_DATA) \
	$(server_DATA) \
	$(xml_DATA) \
	$(server_in_files)

EXTRA_DIST = \
	$(schema_in_files) \
	$(xml_in_files) \
	Hamster_Applet.server.in.in \
	$(resources_DATA)
