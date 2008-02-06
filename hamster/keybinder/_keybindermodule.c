/* -*- Mode: C; c-basic-offset: 4 -*- */
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
