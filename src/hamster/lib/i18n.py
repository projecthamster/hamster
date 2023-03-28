# - coding: utf-8 -
import os
import locale, gettext

import hamster


def setup_i18n():
    #determine location of po files

    # to avoid confusion, we won't translate unless running installed
    # reason for that is that bindtextdomain is expecting
    # localedir/language/LC_MESSAGES/domain.mo format, but we have
    # localedir/language.mo at it's best (after build)
    # and there does not seem to be any way to run straight from sources
    if hamster.installed:
        from hamster import defs  # only available when running installed
        locale_dir = os.path.realpath(os.path.join(defs.DATA_DIR, "locale"))

        for module in (locale,gettext):
            module.bindtextdomain('hamster', locale_dir)
            module.textdomain('hamster')

        gettext.install("hamster", locale_dir)

    else:
        gettext.install("hamster-uninstalled")


def C_(ctx, s):
    """Provide qualified translatable strings via context.
        Taken from gnome-games.
    """
    translated = gettext.gettext('%s\x04%s' % (ctx, s))
    if '\x04' in translated:
        # no translation found, return input string
        return s
    return translated
