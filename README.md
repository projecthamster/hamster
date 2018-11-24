# Hamster - The Gnome Time Tracker

Hamster is time tracking for individuals. It helps you to keep track of how
much time you have spent during the day on activities you choose to track.



hamster-time-tracker v1.04 was not usable under openSUSE Leap-15,
where python2-gconf is not available any longer.
The [rewrite of hamster](https://github.com/projecthamster/hamster-gtk)
is progressing well, but it is still listed as alpha.

This repo is a fork from
[hamster](https://github.com/projecthamster/hamster) project,
that still used hamster.db, already migrated to Gtk3 and did not
depend on python-gconf.

Lots of the gui ease of use has been lost, especially for tags handling,
start/restart of activities, and the stats display is minimal now.
But at least backward compatibility seems good.
Seems enough to wait for the rewrite.

The fork base commit is [the latest one from master branch](https://github.com/projecthamster/hamster/commit/c3e5fb761c88fdecfd1566cac8b6836228a27cce).

After a little tweaking, it works now,
but has not been thouroughly tested.
Backup `hamster.db` first,
and keep track of activities on a text file too for some days !

To use the development version:
```
pkill -f hamster-service
pkill -f hamster-windows-service
src/hamster-service &
src/hamster-windows-service &
src/hamster-cli
```

To install, python2 is still necessary (for waf).
Adapt the paths below to your system,
`sudo rm/mv` commands, beware !
```
./waf configure build --prefix=/usr && sudo ./waf install
sudo rm -rf /usr/lib/python3.6/site-packages/hamster
sudo mv /usr/lib/python2.7/site-packages/hamster /usr/lib/python3.6/site-packages/
```


*[README from the original repo below]*

**IMPORTANT**
Project Hamster is undergoing a period of major transition. Unless someone
steps up to the task, this repository will remain unmaintained as the
majority of our resources are directed to a rewrite (repositories: 
``hamster-lib/dbus/cli/gtk``). Whilst you may leave bug reports and feature
request with the issue tracker, please be warned that fixes at the current
codebase will most likely stay unfixed and PR unmerged. Feature request will
be reevaluated once the new codebase takes though.

## Installation

You can use the usually stable `master` or [download stable releases](https://github.com/projecthamster/hamster/releases).

#### Dependencies

Debian-based: `apt-get install gettext intltool python-gconf python-xdg gir1.2-gconf-2.0 python-dbus`

RPM-based: `yum install gettext intltool gnome-python2-gconf dbus-python`

#### Building

```bash
./waf configure build --prefix=/usr
sudo ./waf install
```

If you upgraded from an existing installation make sure to kill the running
daemons:

```bash
pkill -f hamster-service
pkill -f hamster-windows-service
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

1. [Fork](https://github.com/projecthamster/hamster/fork) this project
2. Create a topic branch - `git checkout -b my_branch`
3. Push to your branch - `git push origin my_branch`
4. Submit a [Pull Request](https://github.com/projecthamster/hamster/pulls) with your branch
5. That's it!

Also check out our [mailing list](http://lists.denkeninechtzeit.net/listinfo.cgi/hamster-dev-denkeninechtzeit.net) for technical discussions.
