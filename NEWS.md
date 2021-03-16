## Changes in 3.0.3 (unreleased)

* A number changes to the overview screen:
  - Add daily total rows. (PR 596)
  - Remove lines previously shown for days without activity. (PR 650)
  - Refactor the range selection dropdown, preventing a problem where it
    would not be shown on systems using Wayland and some other systems.
    (issue 639 and 645, PR 647)
  - Do not periodically scroll to the top, only when displaying a new
    set of facts.(issue 594, PR 648)
* On Wayland, fix the popup below the tag field when editing activities
  and the time field in the preferences window. (PR 652)
* In addition to source downloads, packaged builds using the Flatpak
  format are now available as well. (PR 610)
* Fix exception in all calls to the dbus UpdateJSON method (issue 671,
  PR 672).
* Fix the start date picker in the update/add activity window. (issue
  590, PR 674)

## Changes in 3.0.2

* Switch from deprecated xml2po to itstool for translating help files
  (issue 583).
* Fix off-by-one-day error in CSV exports (issue 576).
* Support Python3.5 again, this was >= 3.6 (issue 582).

## Changes in 3.0.1

* Fixed a rare crash in hamster-window-server (issue 571).


## Changes in 3.0

* Fixed dialogs placement (PR 549):
  - dialogs appear above their parent (the overview, if opened).
  - the window manager/compositer chooses the dialog position.
* Fixed gnome window/application association (issue 242)
* Fixed numpad Enter now works in the GUI cmdline (PR 540).
* Fixed popups position in wayland (issue 339)
* Fixed permissions in the source tree.
* Fixed "Unsorted": no category (PR 502).
* Fixed removal of tags from autocomplete (issue 238)
* Fixed hamster-cli windows calls (PR 480)
* Fixed font sizes on high DPI screens (PR 426)
* Fixed installation process (PR 421)
  - Updated waf to 2.0.17.
    No longer need python2.
  - Default to --prefix=/usr.
  - Removed binary footer, to ease debian packaging (PR 569)
* Fixed category color and tags spillout (PR 414)
* Fixed multiline description height (PR 412)
* Fixed adding overlapping activity (PR 410)
* Fixed update activity window to be resizable (PR 403)
* Fixed database file monitoring (PR 401).
* Fixed dark theme colors (PR 391).
* Fixed hamster-service failure when there is no hamster.db (issue 394).
* New options for packagers (PR 565)
* New 'version' or 'Version' command/methods available (PR 528).
* New Gui is a Gtk.Application (PR 516)
* New `*JSON` dbus methods to pass facts verbatim (PR 514).
* New hamster.lib.datetime, customized replacement for python datetime (PR 510).
* New `CheckFact` and `check_fact` methods available (PR 500).
  Check a fact validity, with detailed error messages.
* New AddFact accepts -1 as start or end, to mean explicit None (PR 492).
* Moved Fact to new fact.py
* Changed basenames from hamster to org.gnome.Hamster.GUI (issue 547)
  - metainfo.xml (PR 558)
  - hamster.png icons (PR 542)
* Changed i18n from from intltools to pure gettext (PR 497).
* Changed from GConf to GSettings (PR 470)
* Changed directory names from hamster-time-tracker to hamster (PR 485).
* Changed parser:
  - Use Fact.parse()
  - Accept activity starting with hash '#' (issue ?)
  - Accept comma in activity (issue ?)
  - Breaking (sorry, really needed):
    Description delimiter is a double comma ',,' instead of a single comma.
  - Comma is forbidden in category (instead of silently swallowed)
  - Same parser for terminal, gui and D-Bus interface.
    Range is still searched at tail (terminal) or head position (gui, D-Bus).
  - Fact.range start/end are always datetimes
    any time given without date is attributed to a default hamster day.
    The default hamster day is usually today.
    In the gui, the default day is the day selected in the timeline.
  - start/end can be entered as +mmm or -mmm (<sign><1-3 digits>),
    relative to a reference. The reference is usually now.
  - The fact duration can be given as mmm (<1-3 digits>, no sign),
    instead of the end.
  - hour/minutes separator can be colon, comma, dot, e.g. 9.30.
    No separator is allowed, but only with 4 digits: hhmm.
* Changed install bash completion to /usr/share (PR 417)
* Changed preselect time instead of activity (PR 415)
* Removed trophies code (PR 408)
* Used GLib.MainLoop instead of GObject.MainLoop (PR 404)
* Added stop tracking button to header bar (PR 427)
* Brought back the help system (PR 393).
* Improved Add/Update activity window
  - fixed description input (PR 430)
* Improved consistency in date/time handling (PR 429) by
    - switching to ISO date format (%Y-%m-%d) in `lib/*`
      to be consistent with hamster-cli usage
    - rounding (i.e. truncating) all activity start/end timestamps
      to the minute
    ** note that this only affects new and/or edited activities in the database
* Improved keyboard handling:
  - Ctrl+Space to stop tracking.
  - Left/Right arrows change date.
  - Resume: start now a clone of the selected activity.
    Ctrl-+: clone or fallback to new if none selected.
            (same as pressing the + button)
    Ctrl-R: only Resume (clone) an existing fact.
    Ctrl-N: only new.
  - Up, down, Home, End, Page-Up, Page-Down, Return
    work straight from the overview (no need to click).
  - More info on PR #387.
* Removed non-working stuff that will be developed elsewhere (issue 493):
  external, idle, ...


## Changes in 2.2.2

* Restore python3 < 3.6 compatibility.
* Remove a PangoCairo warning.


## Changes in 2.2.1

* Activity can contain decimal numbers.
* Add total duration to the `hamster list` output.
* Base Fact comparison on main attributes.
* Small improvements to suggestions.
* A selected fact can be resumed (start now a clone)
  by pressing the `+` button.
* Facts can be deselected by mouse click.
* Still ongoing activities are shown,
  even if they started on a previous day.
* Several export (reports) fixes.
* Fact.delta (duration of the fact, as a timedelta)
  is a read-only property.
* Tag list keeps the input order.
* Better format of the stats area.

Thanks to all contributors (either code or feedback) !
More information by looking for milestone:2.2 or by
cloning and using the following command:
gitk v2.1.1...v2.2.1


## Changes in 2.1.1

Migration to python3
and minor usability fixes

More details by cloning and using the following command:
gitk --no-merges v2.0-rc1...v2.1.1


## Changes in 2.0

 This release marks the transition to Gtk3, and includes all the other
 feature additions and bugfixes that have been submitted since then and
 are too countless to list here. Thanks to all the contributors!

 Please check README.md for the current dependencies.


## Changes in 1.04

 This version just packs all the contributed bugfixes of last 12 month (there
 were just a few)

 * bugfixes around talking to the notifications daemon
 * updating tags list in prefs wasn't doing anything
 * in some cases activity updates were failing when tags where provided



## Changes in 1.03.3

 * fix exporting entries to file


## Changes in 1.03.2

 * fix bug when trying to enter an activity with tags (mea culpa)


## Changes in 1.03.1

 * fix silly bug with path


## Changes in 1.03

 * fix issue #61 - installation was missing initial database for fresh installs
 * loosen backend dependencies so that hamster.client can be used outside the
   project see http://pypi.python.org/pypi/hamster-sqlite/ for details
 * desktop notification now once again correctly notifies of "No activity"

 * updated Bulgarian translation


## Changes in 1.02.1

 * Drop gnome-keybindings as a dependency - not used anymore


## Changes in 1.02

 This is the first release targetting GNOME v3+. The applet has been removed
 and recommended hamster remote is the shell extension, available on
 extensions.gnome.org (also ).

 * Project Hamster has detached from Gnome and thus we are resetting the
   versioning. The program name also has changed from hamster-applet to
   a more generic hamster-time-tracker
 * Improvements in the command line. hamster-cli has been renamed to
   simply "hamster" and without parameters launches the day view. Run
   "hamster --help" to get help on available commands. The executable also
   supports tab-completion to suggest actions as well as to look up activities
   and categories
 * desktop notifications are back
 * the notification tray interaction has been slightly improved (click to toggle)
 * ~20 bug fixes https://github.com/projecthamster/hamster/issues?state=closed


## Changes in 2.91.2

  * experimental trophy support (to try out need to install the achievement
    service from https://github.com/tbaugis/gnome-achievements)
  * improvements in HTML reports

  Updated translations:
    * ar (Khaled Hosny)
    * bq (Damyan Ivanov)
    * ca (Gil Forcada)
    * ca@valencia (Gil Forcada)
    * cs (Adrian Guniš)
    * da (Kenneth Nielsen)
    * de (Christian Kirbach)
    * el (Michael Kotsarinis)
    * en_GB (Bruce Cowan)
    * es (Jorge González)
    * et (Ivar Smolin)
    * fr (Bruno Brouard)
    * gl (Fran Dieguez)
    * he (Yaron Shahrabani)
    * hu (Gabor Kelemen)
    * it (Milo Casagrande)
    * ja (Takayuki KUSANO)
    * ko (Changwoo Ryu)
    * lt (Žygimantas Beručka)
    * pl (Piotr Drąg)
    * pt_BR (Og Maciel)
    * pt (Duarte Loreto)
    * sl (Andrej Žnidaršič)
    * sr (Милош Поповић)


## Changes in 2.31.90

  * maintaining selection on refresh in a more sane manner
  * self-monitor the database not only for updates but also for remove/create
    (solves problems with some synchronization tools)
  * documentation updates
  * fixed the global hotkey. require gnome-keybindings (gnome-control-center-dev)
    package as the hotkey is part of expected functionality

  Updated translations:
    * es (Jorge González)
    * nb (Kjartan Maraas)
    * ro (Lucian Adrian Grijincu)


## Changes in 2.31.6

  * the top graph in overview is now interactive and allows zooming in and out
  * sqlite utf-8 case sensitivity workarounds for queries
  * hamster's docky helper installed together with hamster
  * using full text search in the overview window now
  * hopefully activity trees now behave better on refresh

  Updated translations:
    * de (Mario Blättermann)
    * es (Jorge González)
    * sl (Matej Urbančič)
    * ta (Dr.T.Vasudevan)
    * zh_CN (Tao Wang)
    * gl (Fran Diéguez)
    * he (Yaron Shahrabani)
    * zh_TW (Cheng-Chia Tseng)
    * zh_HK (Cheng-Chia Tseng)
    * nb (Kjartan Maraas)



## Changes in 2.31.5

  * adjustments for custom widgets to better work with themes
  * if dialog windows are called from commandline, make sure they shut down
    properly

  Update translation
    * ee (Ivar Smolin)
    * es (Jorge González)
    * fr (Jean-Philippe Fleury)
    * gl (Fran Diéguez)

  Updated documentation translations
    * zh_CN (TeliuTe)


## Changes in 2.31.4

  * overview gets a menu, drops toolbars and now supports date range browsing
  * adjustments to starts and ends graph in statistics (should be more accurate)
  * performance updates in graphics
  * html report was looking in the wrong place for the template

  Updated translations
    * es (Jorge González)
    * et (Ivar Smolin)
    * gl (Fran Diéguez)
    * he (Yaron Shahrabani)
    * lv (Anita Reitere)
    * nb (Kjartan Maraas)


## Changes in 2.31.3.2

  * respecting SYSCONFDIR environment variable to determine where to store
    gconf schema (bug 620965)


## Changes in 2.31.3.1

  * including generated help pages in the tarball so that they appear in
    library.gnome.org


## Changes in 2.31.3

  * dropped in-house global hotkey management in favour to Gnome's global
    hotkeys
  * HTML report template now can be overridden from $HOME folder. instructions
    can be found in the report footer
  * remembering path of last saved report
  * moved build system from autotools to waf

  Updated translations
    * cs (Adrian Guniš)
    * es (Jorge González)
    * et (Ivar Smolin)
    * gl (Fran Diéguez)
    * he (Yair Hershkovitz)
    * nb (Kjartan Maraas)
    * sl (Matej Urbančič)
    * zh_CN (Ray Wang)


## Changes in 2.31.2

  * optional integration with gtg (via preferences)
  * all kinds of bugfixes

  Updated translations
    * ee (Ivar Smolin)
    * en@shaw (Thomas Thurman)
    * es (Jorge González)


## Changes in 2.31.1.2

  * hamster-service had not been packed in the tarball


## Changes in 2.31.1.1

  * forgot to pull in translations


## Changes in 2.31.1

  * application has been split up in back-end d-bus daemon and clients
  * edit activity preview widget got some love
  * minor bugfixes from 2.30 release

  Updated translations
    * es (Jorge González)
    * sl (Matej Urbančič)
    * gl (Fran Diéguez)



## Changes in 2.30.0

  Updated translations
    * ca (Gil Forcada)
    * da (Kenneth Nielsen)
    * et (Mattias Põldaru)
    * eu (Iñaki Larrañaga Murgoitio)
    * fi (Tommi Vainikainen)
    * hu (Gabor Kelemen)
    * lt (Gintautas Miliauskas)
    * lv (Toms Bauģis)
    * pa (A S Alam)
    * pt (Duarte Loreto)
    * ru (Alexander Saprykin)
    * sv (Daniel Nylander)
    * uk (Maxim Dziumanenko)

  Updated documentation translations
    * el (Marios Zindilis)
    * fr (Claude Paroz)
    * zh_HK (Chao-Hsiung Liao)
    * zh_TW (Chao-Hsiung Liao)



## Changes in 2.29.92

  Bug fixes
    * depend on gnome-python-desktop to fulfill wnck-python dependency
    * minor bug with screen refresh after deletion

  Updated translations
    * bg (Alexander Shopov)
    * de (Mario Blättermann)
    * el (Kostas Papadimas)
    * en_GB (Bruce Cowan)
    * es (Jorge González)
    * it (Milo Casagrande)
    * nb (Kjartan Maraas)
    * pl (Piotr Drąg)

  Updated documentation translations
    * en (Bruce Cowan, Milo Casagrande)
    * es (Jorge González)


## Changes in 2.29.91

  * bug fixes - avoiding blank entries, not reusing fact ids; other details

  Updated translations
    * bg (Alexander Shopov)
    * cs (Adrian Guniš)
    * de (Mario Blättermann)
    * et (Ivar Smolin)
    * fr (Bernard Opic)
    * gl (Fran Diéguez)
    * pt_BR (Rodrigo Flores)
    * ro (Lucian Adrian Grijincu)
    * ta (Dr,T,Vasudevan)
    * zh_HK (Chao-Hsiung Liao)
    * zh_TW (Chao-Hsiung Liao)

  Updated documentation translations
    * cs (Adrian Guniš)
    * de (Christian Kirbach)



## Changes in 2.29.90

  Updated translations
    * bn (Israt Jahan)
    * es (Jorge González)
    * sl (Matej Urbančič)
    * zh_CN (Ray Wang)

  Updated documentation translations
    * es (Jorge González)


## Changes in 2.29.6

  * workspace tracking - switch activity, when switching desktops
    (Ludwig Ortmann, Toms Baugis, Patryk Zawadzki)
  * chart improvements - theme friendly and less noisier
  * for those without GNOME panel there is now a standalone version, accessible
    via Applications -> Accessories -> Time Tracker
  * overview window remembers position
  * maintaining cursor on the selected row after edits / refreshes
    (unimportant, but very convenient)
  * descriptions once again in the main input field, delimited by comma
  * activity suggestion box now sorts items by recency (Patryk Zawadzki)

  Updated translations
    * es (Jorge González)
    * eu (Iñaki Larrañaga Murgoitio)
    * nb (Kjartan Maraas)
    * sv (Daniel Nylander)
    * zh_CN (Tao Wei)



## Changes in 2.29.5

  * searching
  * simplified save report dialog, thanks to the what you see is what you report
    revamp
  * overview/stats replaced with activities / totals and stats accessible from
    totals
  * interactive graphs to drill down in totals
  * miscellaneous performance improvements
  * pixel-perfect graphs


  Updated translations
   * es (Jorge González)
   * et (Ivar Smolin)
   * sl (Matej Urbančič)
   * sv (Daniel Nylander)
   * uk (Maxim V. Dziumanenko)


## Changes in 2.29.4

  * overview window overhaul(still in progress)
  * more progress on tag front (now showing in lists)

  Updated translations
   * es (Jorge González)
   * et (Ivar Smolin)
   * he (Yair Hershkovitz)
   * sl (Matej Urbančič)
   * zh_CN (Funda Wang)


## Changes in 2.29.3

  * partial tag support (adding to a fact and editing autocomplete list,
    no reports yet)
  * fixed glitches when editing ongoing task
  * improved save report dialog
  * better autocomplete for the entries

 Updated translations
  * en@shaw (Thomas Thurman)
  * es (Jorge González)
  * et (Ivar Smolin)
  * sl (Matej Urbančič)
  * zh_CN (Ray Wang)


## Changes in 2.29.2

  * fixed bug 599343 - the charts are now back again (for those who had lost them)
  * hamster midnight is now a preference
  * when in panel, printing uncaugt errors to .xsession-errors
  * when looking for ongoing task, don't look into the future
    (causes some mad durations and is generally impractical)
  * new dbus method getCurrentActivity that returns just the name and category
  * fixed problems with hamster interfering with screensaver hibernation code
  * database MOVED to the xdg home (~/.local)
  * in reports inlude also activities without category
  * set start time to the end of the last activity if adding previous activity
    for today
  * fixes to the dropdown in compiz (not spanning over virtual desktops anymore)
  * in dropdown added end time and dropped the stripes (too much noise already)

 Updated translations:
  * ca (Gil Forcada)
  * en_GB (Bruce Cowan)
  * es (Jorge González)
  * et (Mattias Põldaru)
  * it (Milo Casagrande)
  * pl (Tomasz Dominikowski)
  * ro (Mișu Moldovan)
  * sl (Matej Urbančič)
  * sv (Daniel Nylander)
  * ta (Dr.T.Vasudevan )
  * zh_CN (Ray Wang)



## Changes in 2.28.0

 Updated translations:
  * as (Amitakhya Phukan)
  * bg (Alexander Shopov)
  * bn_IN (Runa Bhattacharjee)
  * da (Ask Hjorth Larsen)
  * de (Hendrik Richter)
  * en_GB (Bruce Cowan)
  * fi (Tommi Vainikainen)
  * gl (Antón Méixome)
  * gu (Ankit Patel)
  * hi (Rajesh Ranjan)
  * hu (Gabor Kelemen)
  * it (Milo Casagrande)
  * ja (Takeshi AIHANA)
  * kn (Shankar Prasad)
  * ko (Changwoo Ryu)
  * lt (Gintautas Miliauskas)
  * lv (Pēteris Caune)
  * mai (Sangeeta Kumari)
  * ml (പ്രവീണ്‍ അരിമ്പ്രത്തൊടിയില്‍)
  * mr (Sandeep Shedmake)
  * or (Manoj Kumar Giri)
  * pa (A S Alam)
  * pl (Tomasz Dominikowski)
  * sl (Matej Urbančič)
  * sr (Горан Ракић)
  * ta (I. Felix)
  * te (Krishna Babu K)
  * uk (Maxim Dziumanenko)
  * zh_HK (Chao-Hsiung Liao)


## Changes in 2.27.92

 Updated translations:
  * ar (Khaled Hosny)
  * be (Alexander Nyakhaychyk)
  * bg (Alexander Shopov)
  * bn (Maruf Ovee)
  * bn_IN (Runa Bhattacharjee)
  * cs (Adrian Guniš)
  * en_GB (Philip Withnall)
  * es (Jorge González)
  * et (Mattias Põldaru)
  * eu (Iñaki Larrañaga Murgoitio)
  * fi (Tommi Vainikainen)
  * fr (Claude Paroz)
  * gl (Antón Méixome)
  * gu (Sweta Kothari)
  * kn (Shankar Prasad)
  * nb (Kjartan Maraas)
  * or (Manoj Kumar Giri)
  * pl (Tomasz Dominikowski)
  * pt (Duarte Loreto)
  * pt_BR (Fábio Nogueira)
  * sv (Daniel Nylander)
  * ta (I. Felix)
  * te (Krishna Babu K)
  * zh_HK (Chao-Hsiung Liao)



## Changes in 2.27.90

  * Fixes to idle detection (now works with gnome screensaver 2.27+)
  * return of the day view
  * UI layout fixes to match HIG
  * now it is possible to add more than one applet to panel without crashing

  Updated translations:
    * ee (Ivar Smolin)
    * gl (Antón Méixome)
    * es (Jorge González)
    * hu (Gabor Kelemen)
    * zh_HK (Chao-Hsiung Liao)
    * sv (Daniel Nylander)



## Changes in 2.27.5

  * Better autocomplete
  * More skeptic on parsing time
  * Legend in overview is sized proportionally to screen size,
    allowing larger labels

  Updated translations:
    * be (Alexander Nyakhaychyk)
    * es (Jorge González)
    * pa (Amanpreet Singh Alam)


## Changes in 2.27.4

  * Now it is possible to copy/paste activities in the overview
  * mostly polishing and bug fixing the new stuff brought in in 2.27 cycle

  Updated translations:
    * bn_IN (Runa Bhattacharjee)
    * es (Jorge González)
    * et (Ivar Smolin)
    * fr (Claude Paroz)
    * sv (Daniel Nylander)
    * uk (Maxim V. Dziumanenko)


## Changes in 2.27.3

  * A much better DBUS support (Felix Ontanon)
  * Switch days at 5am because humans tend to work late. Overlapping activities
    fall in day where the largest part of it is (Patryk Zawadski)
  * Now you can enter negatives minutes to start an activity in past.
    Example "-30 cookies" will start activity "cookies" 30 minutes before now
  * TSV, XML and iCal export
  * Ability to filter task by date and category
  * Overview has been improved by adding some nifty statistics for your pleasure

  Updated translations:
    * ta.po (Dr.T.Vasudevan)


## Changes in 2.27.2

  * Now a reminder is displayed every configured amount of time also when no
    activity is being tracked. (Can be disabled in preferences)
  * Allow to switch to same task if description differs
  * Activity edit icon in dropdown is now keyboard accessible
  * Start time and end time can be specified when typing in task.
       Example: 00:04 Hamster
  * slightly smarter autocomplete with category suggestions when after @ symbol
  * fixes to edit activity dialog's end time field

  Updated translations:
    * el.po (Jennie Petoumenou)
    * et.po (Ivar Smolin)
    * ta.po (Dr.T.vasudevan)
    * uk.po (Maxim V. Dziumanenko)
    * ca@valencia.po (Gil Forcada/Miquel Esplà)



## Changes in 2.27.1

  * Overview window graphs have been redone and now are less noisy
  * Tasks now can span over midnight, showing correct per-day totals in overview
  * Add earlier activity / edit activity has been overhauled and now is much
    easier to use. An experimental preview has been added
  * In preferences UI buttons have been added for editing and deletion
  * Glade files have been migrated to gtkbuilder format
  * now it is possible to start overview and other windows straight from command
    line using "-s [stats|edit|prefs]" switch

  Updated translations:
    * ca.po (David Planella)
    * cs.po (Petr Kovář)
    * da.po (Ask Hjorth Larsen)
    * de.po (Hendrik Richter)
    * el.po (Kostas Papadimas)
    * en_GB.po (Philip Withnall)
    * et.po (Ivar Smolin)
    * fi.po (Ilkka Tuohela)
    * fr.po (Claude Paroz)
    * gl.po (Ignacio Casal Quinteiro)
    * he.po (Yair Hershkovitz)
    * kn.po (Shankar Prasad)
    * lt.po (Gintautas Miliauskas)
    * lv.po (Toms Bauģis)
    * nl.po (Wouter Bolsterlee)
    * or.po (Manoj Kuamr Giri)
    * pl.po (Łukasz Jernaś)
    * pt_BR.po (Vladimir Melo)
    * ro.po (Mișu Moldovan)
    * ru.po (Nickolay V. Shmyrev)
    * si.po (Danishka Navin)
    * sl.po (Matej Urban)
    * sv.po (Daniel Nylander)
    * tr.po (Baris Cicek)
    * zh_CN.po (Aron Xu)



## Changes in 2.25.3

  We were late for 2.25.1 and 2.25.2, so here we go - changes since 2.24.0!

  Applet - changes
    * Now it is possible to add description after activity, delimiting with
      comma: "watering flowers, begonias" will add activity "watering flowers"
      with description "begonias". Likewise you can go for cacti, and
      forgetmenots
    * Task category can be seen in dropdown and can be specified on fly to
      autocreate: working@new project - will create category "new project"
      and add activity "working" to it
    * Hamster now can remind of itself every once in a while, interval is set
      in preferences (George Logiotatidis)
    * Sending dbus signals on activity change (Juanje Croissier)

  Applet - love
    * Applet now again can be found in applet list by searching for 'hamster'
    * Get instant totals per category for today, in applet dropdown
    * Improvements in report - somewhat nicer look and there are also totals
      (Giorgos Logiotatidis)
    * Use vertical space if we have some on panel and show applet in two lines

  Updated translations
    * bg.po (Alexander Shopov)
    * el (Nick Agianniotis)
    * he (Yair Hershkovitz)
    * ku (Erdal Ronahi)
    * lv (Toms Bauģis)
    * sv (Daniel Nylander)
    * zh_CN (Ray Wang)




## Changes in 2.24.0

  Applet
    * some more strings available for translation, but the main changes are
      the updated translations

  Updated translations
    * ar (Djihed Afifi)
    * bg (Alexander Shopov)
    * bn_IN (Runa Bhattacharjee)
    * ca (Gil Forcada)
    * cs (Petr Kovar)
    * da (Ask Hjorth Larsen)
    * de (Hendrik Richter)
    * el (Nikos Charonitakis)
    * en_GB (Philip Withnall)
    * es (Jorge González)
    * et (Ivar Smolin)
    * eu (Iñaki Larrañaga Murgoitio)
    * fi (Timo Jyrinki)
    * fr (Claude Paroz)
    * gl (Ignacio Casal Quinteiro)
    * gu (Sweta Kothari)
    * he (Yair Hershkovitz)
    * hi (Rajesh Ranjan)
    * hu (Gabor Kelemen)
    * it (Milo Casagrande)
    * kn (Shankar Prasad)
    * ko (Changwoo Ryu)
    * lt (Gintautas Miliauskas)
    * lv (Toms Baugis)
    * mk (Jovan Naumovski)
    * ml (പ്രവീണ്‍ അരിമ്പ്രത്തൊടിയില്‍ )
    * mr (Sandeep Shedmake)
    * nb (Kjartan Maraas)
    * nl (Wouter Bolsterlee)
    * pa (Amanpreet Singh Alam)
    * pl (Tomasz Dominikowski)
    * pt (Duarte Loreto)
    * pt_BR (Vladimir Melo)
    * ru (Alexandre Prokoudine)
    * sl (Matej Urbančič)
    * sq (Laurent Dhima)
    * sr (Горан Ракић)
    * sr@latin (Goran Rakić)
    * sv (Daniel Nylander)
    * ta (Kannan Subramanian)
    * th (Theppitak Karoonboonyanan)
    * tr (Baris Cicek)
    * zh_HK (Chao-Hsiung Liao)
    * zh_TW (Chao-Hsiung Liao)


## Changes in 2.23.92

  Applet
    * fixed code so that it works also with Python 2.4
    * Fixed bug with tasks falling into unsorted category (bug #548914)
    * Fixed error when switching tasks with doubleclick


  Translations
    * ar (Anas Afif Emad)
    * bg (Alexander Shopov)
    * bn_IN (Runa Bhattacharjee)
    * ca (Gil Forcada)
    * cs (Adrian Guniš)
    * de (Matthias Mailänder)
    * en_GB (Philip Withnall)
    * es (Juanje Ojeda Croissier)
    * et (Ivar Smolin)
    * eu (Iñaki Larrañaga Murgoitio)
    * fi (Timo Jyrinki)
    * fr (Claude Paroz)
    * gl (Ignacio Casal Quinteiro)
    * gu (Sweta Kothari)
    * he (Yair Hershkovitz)
    * it (Stefano Pedretti)
    * lt (Gintautas Miliauskas)
    * lv (Toms Baugis)
    * mk (Jovan Naumovski)
    * mr (Sandeep Shedmake)
    * nb (Kjartan Maraas)
    * nl (Wouter Bolsterlee)
    * pl (Tomasz Dominikowski)
    * pt (Duarte Loreto)
    * pt_BR (Vladimir Melo)
    * ru (Sasha Shveik)
    * sl (Matej Urbančič)
    * sv (Daniel Nylander)
    * zh_HK (Chao-Hsiung Liao)
    * zh_TW (Chao-Hsiung Liao)


## Changes in 2.23.91

  Applet
	* When adding earlier activity in current day, set default end time to now
	* In overview start week with monday/sunday depending on locale (bug 548102)
    * Respect theme colors for graph labels
      (bug 548840) patch by CJ van den Berg
    * Fixed fail on exit when there is no last activity


  Translations
    * ar (Anas Afif Emad)
    * ca (Gil Forcada)
	* de (Matthias Mailänder)
	* es (Juanje Ojeda Croissier)
	* et (Ivar Smolin)
    * fi (Timo Jyrinki)
	* fr (Claude Paroz)
	* gl (Ignacio Casal Quinteiro)
    * gu (Sweta Kothari)
	* he (Yair Hershkovitz)
	* it (Stefano Pedretti)
	* lv (Toms Baugis)
    * mk (Jovan Naumovski)
    * mr (Sandeep Shedmake)
	* nb (Kjartan Maraas)
	* nl (Wouter Bolsterlee)
    * pl (Tomasz Dominikowski)
	* pt (Duarte Loreto)
    * pt_BR (Vladimir Melo)
	* ru (Sasha Shveik)
	* sv (Daniel Nylander)
    * zh_HK (Chao-Hsiung Liao)
    * zh_TW (Chao-Hsiung Liao)


## Changes in 2.23.90

  Applet
	* Changing name from "Hamster" to "Time Tracker"
	* Information on when computer becomes idle is now determined from
	  screensaver
	* Fixes to focusing issues when calling applet with hotkey


  Translations
	* de (Matthias Mailänder)
	* es (Juanje Ojeda Croissier)
	* et (Ivar Smolin)
	* fr (Stéphane Raimbault)
	* gl (Ignacio Casal Quinteiro)
	* he (Yair Hershkovitz)
	* it (Stefano Pedretti)
	* lv (Toms Baugis)
	* nb (Kjartan Maraas)
	* nl (Wouter Bolsterlee)
	* pt (Duarte Loreto)
	* ru (Sasha Shveik)
	* sv (Daniel Nylander)



## Changes in 2.23.6

  Applet
	* Follow GNOME version scheme
	* Properly integrate with Keyboard Shortcuts in gnome-control-center

  Translations
	* de (Matthias Mailänder)
	* es (Juanje Ojeda Croissier)
	* fr (Stéphane Raimbault)
	* it (Stefano Pedretti)
	* lv (Toms Baugis)
	* nl (Wouter Bolsterlee)
	* ru (Sasha Shveik)
	* sv (Kalle Persson)


## Changes in 0.6.2

  Applet
	* Fixed the header info and updated the Spanish translations
	* Updated the Dutch translation by Wouter Bolsterlee (#544975)
	* Disable keybindings if not supported by g-c-c
	* Properly integrate with GNOME's keyboard binding dialog
	* Fixed problems with simple report
	* Now you can edit facts in overview by double clicking
	* Updated French translation (Stephane Raimbaul)
	* Put icons back in overview window
	* Stock buttons for add / update fact
	* Fixed potential popup window positioning issue

  Translations
	* de (Matthias Mailänder)
	* es (Juanje Ojeda Croissier)
	* fr (Stéphane Raimbault)
	* it (Stefano Pedretti)
	* lv (Toms Baugis)
	* nl (Wouter Bolsterlee)
	* ru (Sasha Shveik)
	* sv (Kalle Persson)


## Changes in 0.6.1

  Applet
	* Do not eat up middle-click
	* Fixed fact pushing on overlap
	* Correct orientation on vertical applets

  Translations
	* de (Matthias Mailänder)
	* es (Juanje Ojeda Croissier)
	* fr (Pierre-Luc Beaudoin)
	* it (Stefano Pedretti)
	* lv (Toms Baugis)
	* sv (Kalle Persson)


## Changes in 0.6

  Applet
	* Simple reporting via Overview dialog

  Translations
	* de (Matthias Mailänder)
	* es (Juanje Ojeda Croissier)
	* fr (Pierre-Luc Beaudoin)
	* it (Stefano Pedretti)
	* lv (Toms Baugis)
	* sv (Kalle Persson)


## Changes in 0.5

  Applet
	* Preferences are now editable via user interface
	* Added option to stop tracking on shutdown
	* Current activity is now showing up in totals

  Translations
	* es (Juanje Ojeda Croissier)
	* it (Stefano Pedretti)
	* lv (Toms Baugis)
	* sv (Kalle Persson)


## Changes in 0.4.1

  Applet
	* Fixed lintian warnings, mentioned in bug 531965. Also, got rid of rest of them :)
	* Fixed rules as per bug 532711. Patch by Juanje Ojeda.

  Translations
	* es (Juanje Ojeda Croissier)
	* it (Stefano Pedretti)
	* lv (Toms Baugis)
	* sv (Kalle Persson)


## Changes in 0.4.1

  Miscellanous
	* Fixed usage of spanish and italian translations

  Translations
	* es (Juanje Ojeda Croissier)
	* it (Stefano Pedretti)
	* lv (Toms Baugis)
	* sv (Kalle Persson)


## Changes in 0.4

  Applet
	* Fact editing!

  Translations
	* es (Juanje Ojeda Croissier)
	* it (Stefano Pedretti)
	* lv (Toms Baugis)
	* sv (Kalle Persson)


## Changes in 0.3

  Applet
	* Many small fixes to activity editing window (setting, focus, F2 for
	  renames and others you would expect)

  Translations
	* es (Juanje Ojeda Croissier)
	* it (Stefano Pedretti)
	* lv (Toms Baugis)
	* sv (Kalle Persson)


## Changes in 0.2

  Applet
	* change days on midnight also when there is no current activity
	* option to stop tracking after certain minutes of idle
	* simplified versioning to three numbers

  Translations
	* es (Juanje Ojeda Croissier)
	* lv (Toms Baugis)
	* sv (Kalle Persson)


## Changes in 0.1.7.5

  Applet
	* Fixed midnight crasher

  Translations
	* es (Juanje Ojeda Croissier)
	* lv (Toms Baugis)
	* sv (Kalle Persson)


## Changes in 0.1.7.4

  Applet
	* Fixed licensing issues

  Debian
	* Packaging is back to per arch

  Translations
	* es (Juanje Ojeda Croissier)
	* lv (Toms Baugis)
	* sv (Kalle Persson)


## Changes in 0.1.7.3

  Applet
	* In stats the top caption shows what can be actually seen
	  (day / week / month) - geekout
	* remove hamster killname, since it breaks x86_64
	* switching tasks on doubleclick in applet main window
	* some more thinking on accidental facts (forth and back to previous task
	  within minute)
	* graphs now have fixed offset from left, long labels get ellipsized

  Debian
	* attempt to package with arch = all

  Translations
	* es (Juanje Ojeda Croissier)
	* lv (Toms Baugis)
	* sv (Kalle Persson)


## Changes in 0.1.7.2

  Applet
	* Fixed focus issues with global hotkeys

  Translations
	* lv (Toms Baugis)
	* sv (Kalle Persson)


## Changes in 0.1.7.1

  Applet
	* Fixed regression with keys ignored in applet window

  Translations
	* lv (Toms Baugis)
	* sv (Kalle Persson)


## Changes in 0.1.7

  Applet
	* Fixed applet vertical sizing issues
	* Showing Evolution's active TODO's in activity lists
	* Drop down window now doesn't have double shadow on top of it
	* Fixed bug with situation, when activities get moved to newly created
	  category

  Translations
	* lv (Toms Baugis)
	* sv (Kalle Persson)


## Changes in 0.1.6.2

  Applet
	* Stop at 12 different activities a day, 12th being total of others
	* Give more space to activity stats
	* Put back resize to both sizes, since we are now ellipsizing

  Translations
	* lv (Toms Baugis)
	* sv (Kalle Persson)


## Changes in 0.1.6.1

  Applet
	* Kind of fixed problem with gconf schema not appearing

  Translations
	* lv (Toms Baugis)
	* sv (Kalle Persson)


## Changes in 0.1.6

  Applet
	* Enhanced drag and drop behaviour in edit activities window
	* Added labels, tooltips, spacings, and other flags to enhance experience

  Translations
	* lv (Toms Baugis)
	* sv (Kalle Persson)


## Changes in 0.1.5.5

  Applet
	* Fixed pysqlite dependency
	* Fixed area chart color

  Translations
	* lv (Toms Baugis)
	* sv (Kalle Persson)


## Changes in 0.1.5.4

  Applet
	* Hamster now has a process name for killall, which enables us to
	  kill it on install!

  Translations
	* lv (Toms Baugis)
	* sv (Kalle Persson)


## Changes in 0.1.5.3

  Applet
	* Fixed antialiasing problems in bar chart

  Translations
	* lv (Toms Baugis)
	* sv (Kalle Persson)


## Changes in 0.1.5.2

  Applet
	* Minor changes and slight adjustments to Swedish translation

  Translations
	* lv (Toms Baugis)
	* sv (Kalle Persson)


## Changes in 0.1.5.1

  Applet
	* Fixed window icons

  Translations
	* lv (Toms Baugis)
	* sv (Kalle Persson)


## Changes in 0.1.5

  Applet
	* Initial release
