# Fork at will (Aug 18, 2014)

My priorities have shifted quite a bit and hamster is not on the list, sorry.
While there might be spurious spontaneous commits ever now and then, that would
scratch my personal itch, it's safe to assume that the project is dead.
[Advertise your fork here](https://github.com/projecthamster/hamster/wiki)


# Bleeding edge warning

Project Hamster right now is undergoing bit of reshuffling and might not be fit
for everyday use. For stable versions check out [releases](https://github.com/projecthamster/hamster/releases)

# Requires most recent stable gtk3 (3.10)

Version of gtk required is 3.10 because of the use of HeaderBar and other bits. 
Sorry and get up to date!



# Dependencies

Debian-based: `apt-get install git-core gettext intltool python-gconf python-xdg`
RPM-based: `yum install git-core gettext intltool gnome-python2-gconf`

# Installing

```
./waf configure build --prefix=/usr
sudo ./waf install
```

After that make sure that the old daemons aren't roaming around:

```
killall hamster-service && killall hamster-windows-service
```

Now restart your panels/dockies and you should be able to add hamster to your panel!


# hamster-applet -> hamster-time-tracker clean up

Previously hamster was installed everywhere under `hamster-applet`. As
the applet is long gone, the paths and file names have changed to
`hamster-time-tracker`. To clean up previous install follow these steps:

```
git checkout d140d45f105d4ca07d4e33bcec1fae30143959fe
./waf configure build --prefix=/usr
sudo ./waf uninstall
```
