# ******************************************************************************
# Images and icon
# ******************************************************************************
artdir = $(pkgdatadir)/art
art_DATA = \
	stock_calendar-view-day.png \
	stock_calendar-view-month.png \
	stock_calendar-view-week.png \
    hamster-applet.png


16icondir = $(datadir)/icons/hicolor/16x16/apps
16icon_DATA = 16x16/hamster-applet.png

22icondir = $(datadir)/icons/hicolor/22x22/apps
22icon_DATA = 22x22/hamster-applet.png

32icondir = $(datadir)/icons/hicolor/32x32/apps
32icon_DATA = 32x32/hamster-applet.png

icondir = $(datadir)/icons/hicolor/48x48/apps
icon_DATA = scalable/hamster-applet.png

svgicondir = $(datadir)/icons/hicolor/scalable/apps
svgicon_DATA = scalable/hamster-applet.svg

gtk_update_icon_cache = gtk-update-icon-cache -f -t $(datadir)/icons/hicolor

install-data-hook: update-icon-cache
uninstall-hook: update-icon-cache
update-icon-cache:
	@-if test -z "$(DESTDIR)"; then \
		echo "Updating Gtk icon cache."; \
		$(gtk_update_icon_cache); \
	else \
		echo "*** Icon cache not updated.  After (un)install, run this:"; \
		echo "***   $(gtk_update_icon_cache)"; \
	fi

EXTRA_DIST = \
	$(art_DATA) \
	$(16icon_DATA) \
	$(22icon_DATA) \
	$(32icon_DATA) \
	$(icon_DATA) \
	$(svgicon_DATA)
    
