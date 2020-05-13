# Hamster - The Gnome Time Tracker

Hamster is time tracking for individuals. It helps you to keep track of how
much time you have spent during the day on activities you choose to track.

This is the main repo. It is standalone (single module).  
All other repositories -`hamster-lib/dbus/cli/gtk`- are part of the separate rewrite effort.  
More context is given in the history section below.

Some additional information is available in the
[wiki](https://github.com/projecthamster/hamster/wiki).

## Installation

### Backup database

This legacy hamster should be stable, and keep database compatibility with previous versions.  
It should be possible to try a new version and smoothly roll back to the previous version if preferred.  
Nevertheless, things can always go wrong. It is strongly advised to backup the database before any version change !

##### Locate the latest db

```bash
ls --reverse -clt ~/.local/share/hamster*/*.db
```
Backup the last file in the list. 


### Kill hamster daemons

When trying a different version, make sure to kill the running daemons:

```bash
# either step-by-step, totally safe
pkill -f hamster-service
pkill -f hamster-windows-service
# check (should be empty)
pgrep -af hamster

# or be bold and kill them all at once:
pkill -ef hamster
```

### Install from packages

##### OpenSUSE
https://software.opensuse.org/package/hamster-time-tracker

##### Fedora and EPEL

Package status: https://apps.fedoraproject.org/packages/hamster-time-tracker

Installation:
```sudo dnf install hamster-time-tracker```
(or graphical package installer).

##### Snap
Easy installation on any distribution supporting snap:  
https://snapcraft.io/hamster-snap

### Install from sources

#### Dependencies
Hamster needs python 3.5 or newer (not included in below install
commands). Older versions are not supported.

##### Debian-based

###### Ubuntu (tested in 19.04 and 18.04)

```bash
sudo apt install gettext intltool python3-gi python3-cairo python3-distutils python3-dbus python3-xdg libglib2.0-dev libglib2.0-bin gir1.2-gtk-3.0 gtk-update-icon-cache
# and for documentation
sudo apt install itstool yelp
```

##### openSUSE

Leap-15.0 and Leap-15.1:
```bash
sudo zypper install intltool python3-pyxdg python3-cairo python3-gobject-Gdk
sudo zypper install itstool yelp
```

##### RPM-based

*RPM-based instructions below should be updated for python3 (issue [#369](https://github.com/projecthamster/hamster/issues/369)).*

`yum install gettext intltool dbus-python`

##### Help reader
If the hamster help pages are not accessible ("unable to open `help:hamster-time-tracker`"),
then a [Mallard](https://en.wikipedia.org/wiki/Mallard_(documentation))-capable help reader is required,
such as [yelp](https://wiki.gnome.org/Apps/Yelp/).

#### Download source

##### Git clone

If familiar with github, just clone the repo and `cd` into it.

##### Download

Otherwise, to get the `master` development branch (intended to be quite stable):
```bash
wget https://github.com/projecthamster/hamster/archive/master.zip
cd hamster
```
or a specific [release](https://github.com/projecthamster/hamster/releases):
```bash
# replace 2.2.2 by the release version
wget https://github.com/projecthamster/hamster/archive/v2.2.2.zip
cd hamster-2.2.2
```

#### Build and install

```bash
./waf configure build
# thanks to the parentheses the umask of your shell will not be changed
( umask 0022 && sudo ./waf install; )
```
The `umask 0022` is safe for all, but important for users with more restrictive umask,
as discussed [here](https://github.com/projecthamster/hamster/pull/421#issuecomment-520167143).

Now restart your panels/docks and you should be able to add Hamster!


#### Uninstall

To undo the last install, just
```bash
sudo ./waf uninstall
```
Afterwards `find /usr -iname hamster` should only list unrelated files (if any).
Otherwise, please see the [wiki section](https://github.com/projecthamster/hamster/wiki/Tips-and-Tricks#uninstall)

#### Troubleshooting

[wiki section](https://github.com/projecthamster/hamster/wiki/Tips-and-Tricks#troubleshooting)

#### Development

During development (As explained above, backup `hamster.db` first !),
if only python files are changed 
(*deeper changes such as the migration to gsettings require a new install*)
the changes can be quickly tested by
```
# either
pgrep -af hamster
# and kill them one by one
# or be bold and kill all processes with "hamster" in their command line
pkill -ef hamster
python3 src/hamster-service.py &
python3 src/hamster-cli.py
```
Advantage: running uninstalled is detected, and windows are *not* called via
D-Bus, so that all the traces are visible.

Note: You'll need recent version of hamster installed on your system (or 
[this workaround](https://github.com/projecthamster/hamster/issues/552#issuecomment-585166000)).

#### Running tests

Hamster has a limited test suite, that can be run using Python's builtin
unittest module. From the top-level directory, just run:

    python3 -m unittest

This will let unittest automatically find all testcases in all files
called `test_*.py`, and runs them.

To run a subset of tests, specify the import path towards it. For
example, to run just a single test file, class or method respectively
run:

    python3 -m unittest tests.test_stuff
    python3 -m unittest tests.test_stuff.TestFactParsing
    python3 -m unittest tests.test_stuff.TestFactParsing.test_plain_name

#### Migrating from hamster-applet

Previously Hamster was installed everywhere under `hamster-applet`. As
the applet is long gone, the paths and file names have changed to
`hamster`. To clean up previous installs follow these steps:

```bash
git checkout d140d45f105d4ca07d4e33bcec1fae30143959fe
./waf configure build --prefix=/usr
sudo ./waf uninstall
```

## Contributing

1. [Fork](https://github.com/projecthamster/hamster/fork) this project
2. Create a topic branch - `git checkout -b my_branch`
3. Push to your branch - `git push origin my_branch`
4. Submit a [Pull Request](https://github.com/projecthamster/hamster/pulls) with your branch
5. That's it!

See [How to contribute](https://github.com/projecthamster/hamster/wiki/How-to-contribute) for more information.


## History

During the period 2015-2017 there was a major effort to
[rewrite hamster](https://github.com/projecthamster/hamster-gtk)
(repositories: `hamster-lib/dbus/cli/gtk`).
Unfortunately, after considerable initial progress the work has remained in alpha state
for some time now. Hopefully the effort will be renewed in the future.

In the meantime, this sub-project aims to pursue development of the "legacy" Hamster
code base, maintaining database compatibility with the widely installed
[v1.04](https://github.com/projecthamster/hamster/releases/tag/hamster-time-tracker-1.04),
but migrating to `Gtk3` and `python3`.  
This will allow package maintainers to provide
new packages for recent releases of mainstream Linux distributions for which the old
1.04-based versions are no longer provided.

With respect to 1.04, some of the GUI ease of use has been lost, especially for handling
tags, and the stats display is minimal now. So if you are happy with your hamster
application and it is still available for your distribution, upgrade is not recommended
yet.

In the meantime recent (v2.2+) releases have good backward data compatibility and are
reasonably usable. The aim is to provide a new stable v3.0 release in the coming
months (i.e. early 2020).
