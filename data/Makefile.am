SUBDIRS = art

# ******************************************************************************
# Panel applet bonobo stuff
# ******************************************************************************
serverdir = $(libdir)/bonobo/servers
server_in_files = Hamster_Applet.server.in
server_DATA = $(server_in_files:.server.in=.server)


# ******************************************************************************
# Misc data
# ******************************************************************************
resourcesdir = $(pkgdatadir)
resources_DATA = \
	Hamster_Applet.xml \
	preferences.ui \
	stats.ui \
	overview.ui \
	overview_totals.ui \
	edit_activity.ui \
        applet.ui \
	hamster.db

xml_in_files = 99-hamster-applet.xml

if CUSTOM_KEYBINDINGS
xmldir = $(KEYBINDINGS_DIR)
xml_DATA = $(xml_in_files)
endif

hamsterbindir = $(libdir)/hamster-applet

# ******************************************************************************
# Build rules
# ******************************************************************************
@INTLTOOL_DESKTOP_RULE@
@INTLTOOL_SERVER_RULE@

$(server_in_files): $(server_in_files:.server.in=.server.in.in)
	$(AM_V_GEN)sed -e "s|\@LIBEXECDIR\@|$(hamsterbindir)|" $< > $@

DISTCLEANFILES = \
	$(server_DATA) \
	$(server_in_files)

EXTRA_DIST = \
	$(xml_in_files) \
	Hamster_Applet.server.in.in \
	$(resources_DATA)
