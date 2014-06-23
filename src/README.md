
When working on hamster, use hamster-cli to launch all the windows - it will
detected that you are running uninstalled and will not call the windows via
D-Bus so that you can see all the traces.

For data retreaval bits, ```killall hamster-service; ./hamster-service``` should
do the trick.
