# Hamster - The Gnome Time Tracker

Hamster is time tracking for individuals. It helps you to keep track of how
much time you have spent during the day on activities you choose to track.

The [rewrite of hamster](https://github.com/projecthamster/hamster-gtk)
is progressing well, but it is still listed as alpha.

This is the legacy repo that still use the same old `hamster.db`,
but migrated to `Gtk3` and `python3`, and without python-gconf dependency.
This allowed to use hamster on platforms (such as openSUSE Leap-15)
where 1.04-based versions were completely broken.

With respect to 1.04, some of the gui ease of use has been lost, especially for tags handling,
and the stats display is minimal now.
So if you are happy with your hamster application, upgrade is not recommended yet.

But at least backward compatibility seems good.
It sounds usable enough to wait for the rewrite.

After a little tweaking, it works now,
but has not been thoroughly tested.
Backup `hamster.db` first,
and keep track of activities on a text file too for some days !


## Installation

You can use the usually stable `master` or [download stable releases](https://github.com/projecthamster/hamster/releases).

If you upgraded from an existing installation make sure to kill the running
daemons:

```bash
pkill -f hamster-service
pkill -f hamster-windows-service
# check (should be empty)
pgrep -af hamster
```

#### Dependencies


##### Debian-based

ubuntu-19.04:

```bash
sudo apt install gettext intltool gconf2 gir1.2-gconf-2.0 libdbus-glib-1-dev-bin python3-gi-cairo
sudo apt install gnome-doc-utils yelp
```

##### openSUSE
Leap-15.0: 
```bash
sudo zypper install intltool python3-pyxdg python3-cairo python3-gobject-Gdk
sudo zypper install gnome-doc-utils xml2po yelp
```

##### RPM-based

*RPM-based instructions below should be updated for python3 (issue [#369](https://github.com/projecthamster/hamster/issues/369)).*

`yum install gettext intltool gnome-python2-gconf dbus-python`

If the hamster help pages are not accessible ("unable to open `help:hamster-time-tracker`"),
then a [Mallard](https://en.wikipedia.org/wiki/Mallard_(documentation))-capable help reader is required,
such as [yelp](https://wiki.gnome.org/Apps/Yelp/).


#### Trying the development version

To use the development version (backup `hamster.db` first !):
```
# either
pgrep -af hamster
# and kill them one by one
# or be bold and kill all process with "hamster" in their command line
pkill -ef hamster
src/hamster-service &
src/hamster-windows-service &
src/hamster-cli
```


#### Building and installing

Main application
```bash
./waf configure build --prefix=/usr
sudo ./waf install
```
For the documentation, same commands, 
with the additional `--docs` option placed anywhere on the line.
```bash
./waf --docs configure build --prefix=/usr
sudo ./waf --docs install
```

Now restart your panels/docks and you should be able to add Hamster!

#### Migrating from hamster-applet

Previously Hamster was installed everywhere under `hamster-applet`. As
the applet is long gone, the paths and file names have changed to
`hamster-time-tracker`. To clean up previous installs follow these steps:

```bash
git checkout d140d45f105d4ca07d4e33bcec1fae30143959fe
./waf configure build --prefix=/usr
sudo ./waf uninstall
```

## Contributing

**IMPORTANT**
Project Hamster is undergoing a period of major transition.
The main effort should go to the rewrite (repositories: `hamster-lib/dbus/cli/gtk`).
[`hamster-gtk`](https://github.com/projecthamster/hamster-gtk) is a good starting point.

The legacy code is hard to maintain, so changes should be minimal and straightforward
to have a chance of being accepted.

1. [Fork](https://github.com/projecthamster/hamster/fork) this project
2. Create a topic branch - `git checkout -b my_branch`
3. Push to your branch - `git push origin my_branch`
4. Submit a [Pull Request](https://github.com/projecthamster/hamster/pulls) with your branch
5. That's it!
