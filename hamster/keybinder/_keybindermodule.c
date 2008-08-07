# - coding: utf-8 -

# Copyright (C) 2005 Nigel Tao <nigeltao at cvs.gnome.org>

# This file is part of Project Hamster.

# Project Hamster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Project Hamster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Project Hamster.  If not, see <http://www.gnu.org/licenses/>.

#ifdef HAVE_CONFIG_H
#  include "config.h"
#endif

/* include this first, before NO_IMPORT_PYGOBJECT is defined */
#include <pygobject.h>

/* include any extra headers needed here */
#include <tomboykeybinder.h>

void py_keybinder_register_classes(PyObject *d);
extern PyMethodDef py_keybinder_functions[];

DL_EXPORT(void)
init_keybinder(void)
{
    PyObject *m, *d;

    /* perform any initialisation required by the library here */
	init_pygobject();
	tomboy_keybinder_init();
	
    m = Py_InitModule("_keybinder", py_keybinder_functions);
    d = PyModule_GetDict(m);
    
    /* add anything else to the module dictionary (such as constants) */
    py_keybinder_register_classes(d);
    
    if (PyErr_Occurred())
        Py_FatalError("could not initialise module _keybinder");
}
