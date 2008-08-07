/* tomboykeybinder.h
 * Copyright (C) 2008 Novell
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Library General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Library General Public License for more details.
 *
 * You should have received a copy of the GNU Library General Public
 * License along with this library; if not, write to the
 * Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110, USA 
 */
#ifndef __TOMBOY_KEY_BINDER_H__
#define __TOMBOY_KEY_BINDER_H__

#include <glib/gtypes.h>

G_BEGIN_DECLS

typedef void (* TomboyBindkeyHandler) (char *keystring, gpointer user_data);

void tomboy_keybinder_init   (void);

gboolean tomboy_keybinder_bind   (const char           *keystring,
			      TomboyBindkeyHandler  handler,
			      gpointer              user_data);

void tomboy_keybinder_unbind (const char           *keystring,
			      TomboyBindkeyHandler  handler);

gboolean tomboy_keybinder_is_modifier (guint keycode);

guint32 tomboy_keybinder_get_current_event_time (void);

G_END_DECLS

#endif /* __TOMBOY_KEY_BINDER_H__ */

