/*      common/idle.c
 *
 * Gajim Team:
 *      - Yann Le Boulanger <asterix@lagaule.org>
 *
 * Copyright (C) 2003-2004 Yann Le Boulanger <asterix@lagaule.org>
 *                         Vincent Hanquez <tab@snarc.org>
 * Copyright (C) 2005-2006 Yann Le Boulanger <asterix@lagaule.org>
 *                    Nikos Kouremenos <nkour@jabber.org>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published
 * by the Free Software Foundation; version 2 only.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
*/

#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <X11/extensions/scrnsaver.h>
#include <Python.h>

Display *display;


static PyObject * idle_init(PyObject *self, PyObject *args)
{
	display = XOpenDisplay(NULL);
	Py_INCREF(Py_None);
	return Py_None;
}

static PyObject * idle_getIdleSec(PyObject *self, PyObject *args)
{
	static XScreenSaverInfo *mit_info = NULL;
	int idle_time, event_base, error_base;

	if (XScreenSaverQueryExtension(display, &event_base, &error_base))
	{
		if (mit_info == NULL)
			mit_info = XScreenSaverAllocInfo();
		XScreenSaverQueryInfo(display, RootWindow(display, 0), mit_info);
		idle_time = (mit_info->idle) / 1000;
	}
	else
		idle_time = 0;

	return Py_BuildValue("i", idle_time);
}

static PyObject * idle_close(PyObject *self, PyObject *args)
{
	XCloseDisplay(display);
	Py_INCREF(Py_None);
	return Py_None;
}

static PyMethodDef idleMethods[] =
{
	{"init",  idle_init, METH_VARARGS, "init idle"},
	{"getIdleSec",  idle_getIdleSec, METH_VARARGS, "Give the idle time in secondes"},
	{"close",  idle_close, METH_VARARGS, "close idle"},
	{NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
initidle(void)
{
	    (void) Py_InitModule("idle", idleMethods);
}
