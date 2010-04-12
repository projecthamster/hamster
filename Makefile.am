SUBDIRS = src data po help
ACLOCAL_AMFLAGS = -I m4

DISTCHECK_CONFIGURE_FLAGS = --disable-scrollkeeper

# Dbus service file
servicedir = $(datadir)/dbus-1/services
nodist_service_DATA = org.gnome.hamster.service

org.gnome.hamster.service: org.gnome.hamster.service.in
	sed	-e s!\@prefix\@!$(prefix)! < $< > $@
org.gnome.hamster.service: Makefile


release: dist
	scp $(PACKAGE)-$(VERSION).tar.gz tbaugis@master.gnome.org:
	ssh tbaugis@master.gnome.org install-module $(PACKAGE)-$(VERSION).tar.gz

DISTCLEANFILES =		\
	intltool-extract	\
	intltool-merge		\
	intltool-update

CLEANFILES = org.gnome.hamster.service
EXTRA_DIST = \
	MAINTAINERS \
	TODO \
	intltool-extract.in	\
	intltool-merge.in	\
	intltool-update.in  \
	gnome-doc-utils.make    \
	org.gnome.hamster.service.in



all-local: org.gnome.hamster.service
