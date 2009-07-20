# - coding: utf-8 -
import gettext

def C_(ctx, s):
    """Provide qualified translatable strings via context.
        Taken from gnome-games.
    """
    translated = gettext.gettext('%s\x04%s' % (ctx, s))
    if '\x04' in translated:
        # no translation found, return input string
        return s
    return translated
