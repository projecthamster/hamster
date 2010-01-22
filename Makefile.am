SUBDIRS = src data po help
ACLOCAL_AMFLAGS = -I m4

DISTCHECK_CONFIGURE_FLAGS = --disable-scrollkeeper

release: dist
	scp $(PACKAGE)-$(VERSION).tar.gz tbaugis@master.gnome.org:
	ssh tbaugis@master.gnome.org install-module $(PACKAGE)-$(VERSION).tar.gz

DISTCLEANFILES =		\
	intltool-extract	\
	intltool-merge		\
	intltool-update

EXTRA_DIST = \
	MAINTAINERS \
	TODO \
	intltool-extract.in	\
	intltool-merge.in	\
	intltool-update.in
	gnome-doc-utils.make
