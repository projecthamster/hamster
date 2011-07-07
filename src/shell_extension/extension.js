/*
 * Simple Hamster extension for gnome-shell
 * Copyright (c) 2011 Jerome Oufella <jerome@oufella.com>
 * Copyright (c) 2011 Toms Baugis <toms.baugis@gmail.com>
 * Portions originate from the gnome-shell source code, Copyright (c)
 * its respectives authors.
 * This project is released under the GNU GPL License.
 * See COPYING for details.
 *
 */

const DBus = imports.dbus;
const Lang = imports.lang;
const St = imports.gi.St;
const Shell = imports.gi.Shell;
const Main = imports.ui.main;
const PopupMenu = imports.ui.popupMenu;
const PanelMenu = imports.ui.panelMenu;
const Util = imports.misc.util;
const Gettext = imports.gettext;
const _ = Gettext.gettext;

/* We use keybindings provided by default in the metacity GConf tree, and which
 * are supported by default.
 * Most probably not the smartest choice, time will tell.
 */
const _hamsterKeyBinding = 'run_command_12';



const HamsterIface = {
    name: 'org.gnome.Hamster',
    methods: [
		{ name: 'GetTodaysFacts', inSignature: '', outSignature: 'a(iiissisasii)'},
		{ name: 'StopTracking', inSignature: 'i'},
    ],
    signals: [
        {name: 'TagsChanged', inSignature: ''},
        {name: 'FactsChanged', inSignature: ''},
        {name: 'ActivitiesChanged', inSignature: ''},
        {name: 'ToggleCalled', inSignature: ''},
    ]
};
let HamsterProxy = DBus.makeProxyClass(HamsterIface);


function fromDbusFact(fact) {
	// converts a fact coming from dbus into a usable object
	function UTCToLocal(timestamp) {
		// TODO - is this really the way?!
		let res = new Date(timestamp)
		return new Date(res.setUTCMinutes(res.getUTCMinutes() + res.getTimezoneOffset()));
	}

    return {
		name: fact[4],
		startTime: UTCToLocal(fact[1]*1000),
		endTime: fact[2] != 0 ? UTCToLocal(fact[2]*1000) : null,
		description: fact[3],
		activityId: fact[5],
		category: fact[6],
		tags: fact[7],
		date: UTCToLocal(fact[8] * 1000),
		delta: fact[9] / (60 * 60), // hours; TODO - want timedelta
		id: fact[0]
	}
};


/* Popup */
function HamsterPopupMenuEntry() {
	this._init.apply(this, arguments);
}

HamsterPopupMenuEntry.prototype = {
	__proto__: PopupMenu.PopupBaseMenuItem.prototype,

	_init: function(itemParams, entryParams) {
		PopupMenu.PopupBaseMenuItem.prototype._init.call(this, itemParams);
		this._textEntry = new St.Entry(entryParams);
		this._textEntry.clutter_text.connect('activate',
			Lang.bind(this, this._onEntryActivated));
		this.addActor(this._textEntry);
	},

	_onEntryActivated: function() {
		this.emit('activate');
		this._textEntry.set_text('');
	}
};

/* Panel button */
function HamsterButton() {
	this._init();
}

HamsterButton.prototype = {
	__proto__: PanelMenu.Button.prototype,

	_init: function() {
		PanelMenu.Button.prototype._init.call(this, 0.0);

		this._proxy = new HamsterProxy(DBus.session, 'org.gnome.Hamster', '/org/gnome/Hamster');

		this._proxy.connect('FactsChanged', Lang.bind(this, this.onFactsChanged));
		this._proxy.connect('ActivitiesChanged', Lang.bind(this, this.onActivitiesChanged));
		this._proxy.connect('TagsChanged', Lang.bind(this, this.onTagsChanged));

		this.panel_label = new St.Label({ style_class: 'hamster-label', text: _("Loading...") });
		this.actor.set_child(this.panel_label);
		Main.panel._centerBox.add(this.actor, { y_fill: true });

		this.facts = null;
		this.currentFact = null;

		this.refresh();


		/* Create all items in the dropdown menu: */
		let item;

		/* This one make the hamster applet appear */
		item = new PopupMenu.PopupMenuItem(_("Show Hamster"));
		item.connect('activate', function() {
			let app = Shell.AppSystem.get_default().get_app(
				'hamster-time-tracker.desktop');
			app.activate(-1);
		});
		this.menu.addMenuItem(item);

		/* To stop tracking the current activity */
		item = new PopupMenu.PopupMenuItem(_("Stop tracking"));
		item.connect('activate', Lang.bind(this, this._onStopTracking));
		this.menu.addMenuItem(item);

		/* The activity item has a text entry field to quickly log something */
		item = new HamsterPopupMenuEntry({ reactive: false }, {
			name: 'searchEntry',
			can_focus: true,
			track_hover: false,
			hint_text: _("Enter activity...")
		});
		item.connect('activate', Lang.bind(this, this._onActivityEntry));
		this._activityEntry = item;
		this.menu.addMenuItem(item);

		/* Integrate previously defined menu to panel */
		Main.panel._rightBox.insert_actor(this.actor, 0);
		Main.panel._menus.addMenu(this.menu);

 		/* Install global keybinding to log something */
		let shellwm = global.window_manager;
		shellwm.takeover_keybinding(_hamsterKeyBinding);
		shellwm.connect('keybinding::' + _hamsterKeyBinding,
			Lang.bind(this, this._onGlobalKeyBinding));
	},

	onTagsChanged: function() {
		this.refresh();
	},

	onFactsChanged: function() {
		this.refresh();
	},

	onActivitiesChanged: function() {
		this.refresh();
	},


	refresh: function() {
    	this._proxy.GetTodaysFactsRemote(Lang.bind(this, function(facts, err) {
			this.facts = facts;

    	    let fact = null;
    	    if (facts.length) {
    	        fact = fromDbusFact(facts[facts.length - 1]);
    	    }

    	    if (fact && !fact.endTime) {
				this.currentFact = fact;

        	    this.panel_label.text = fact.name + " " + Number(fact.delta).toPrecision(2) + "h";
    	    } else {
        	    this.panel_label.text = "No activity";
    	    }
    	}));
	},

	_onStopTracking: function() {
		let date = new Date()
		date = new Date(date.setUTCMinutes(date.getUTCMinutes() - date.getTimezoneOffset())); // getting back to UTC

		let epochSeconds = date.getTime() / 1000;
		this._proxy.StopTrackingRemote(epochSeconds);
	},

	_onActivityEntry: function() {
		let text = this._activityEntry._textEntry.get_text();
		let cmdline = 'hamster-cli start "' + text + '"';
		try {
			Util.trySpawnCommandLine(cmdline);
			this._activityLabel.set_text(' ' + text);
		} catch (e) {
			global.log('_onActivityEntry(): got exception: ' + e);
		}
	},

	_onGlobalKeyBinding: function() {
		this.menu.toggle();
		this._activityEntry._textEntry.grab_key_focus();
	}
};


function main(extensionMeta) {
	/* Localization stuff */
	let userExtensionLocalePath = extensionMeta.path + '/locale';
	Gettext.bindtextdomain("hamster-applet", userExtensionLocalePath);
	Gettext.textdomain("hamster-applet");

	/* Create our button */
	new HamsterButton();
}
