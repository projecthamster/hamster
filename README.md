# Hamster - The Gnome Time Tracker

Hamster is time tracking for individuals. It helps you to keep track of how
much time you have spent during the day on activities you choose to track.

The [rewrite of hamster](https://github.com/projecthamster/hamster-gtk)
is progressing well, but it is still listed as alpha.

This is the legacy repo that still use the same old `hamster.db`,
but migrated to `Gtk3` and `python3`, and without python-gconf dependency.
This allowed to use hamster on platforms (such as openSUSE Leap-15)
where 1.04-based versions were completely broken.

With respect to 1.04, lots of the gui ease of use has been lost, especially for tags handling,
start/restart of activities, and the stats display is minimal now.
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
```

#### Dependencies

Debian-based: `apt-get install gettext intltool python-gconf python-xdg gir1.2-gconf-2.0 python-dbus`

RPM-based: `yum install gettext intltool gnome-python2-gconf dbus-python`

openSUSE Leap-15: `zypper install intltool python3-pyxdg python3-cairo python3-gobject-Gdk`


#### Trying the development version

To use the development version (backup `hamster.db` first !):
```
pkill -f hamster-service
pkill -f hamster-windows-service
src/hamster-service &
src/hamster-windows-service &
src/hamster-cli
```


#### Building and installing

To install, python2 is still necessary (for waf).
Adapt the paths below to your system,
`sudo rm/mv` commands, beware !
```
./waf configure build --prefix=/usr && sudo ./waf install
sudo rm -rf /usr/lib/python3.6/site-packages/hamster
sudo mv /usr/lib/python2.7/site-packages/hamster /usr/lib/python3.6/site-packages/
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
