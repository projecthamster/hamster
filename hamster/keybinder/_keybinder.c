/* -- THIS FILE IS GENERATED - DO NOT EDIT *//* -*- Mode: C; c-basic-offset: 4 -*- */

#include <Python.h>



#line 4 "_keybinder.override"
#include <Python.h>

#define NO_IMPORT_PYGOBJECT
#include "pygobject.h"

#include <tomboykeybinder.h>

typedef struct _Handler_and_Args {
	PyObject *handler;
	PyObject *args;
	char *keystring;
} Handler_and_Args;

static GSList *HA_List = NULL;

void handler_c_func (char *keystring, gpointer user_data)
{
	PyGILState_STATE gstate;
	Handler_and_Args *ha = (Handler_and_Args *) user_data;
	
	gstate = PyGILState_Ensure();
	
	PyObject *result = PyEval_CallObject(ha->handler, ha->args);
	if (result == NULL) {
		if (PyErr_Occurred()) {
			PyErr_Print();
		}
	} else {
		Py_DECREF(result);
	}
	
	PyGILState_Release(gstate);
}

#line 43 "_keybinder.c"


/* ---------- types from other modules ---------- */


/* ---------- forward type declarations ---------- */

#line 51 "_keybinder.c"



/* ----------- functions ----------- */

#line 47 "_keybinder.override"
static PyObject*
_wrap_tomboy_keybinder_bind (PyGObject *self, PyObject *args, PyObject *kwargs) 
{
	guint len;
	PyObject *first;
	char *keystring = NULL;
	PyObject *handler;
	PyObject *extra_args;
	GSList *iter;
	Handler_and_Args *ha;
	
	len = PyTuple_Size(args);
	if (len < 2) {
		PyErr_SetString(PyExc_TypeError, "tomboy_keybinder_bind requires at least 2 arguments");
		return NULL;
	}
	first = PySequence_GetSlice(args, 0, 2);
	if (!PyArg_ParseTuple(first, "sO:tomboy_keybinder_bind", &keystring, &handler)) {
		Py_XDECREF(first);
		return NULL;
	}
	Py_XDECREF(first);

	if (!PyCallable_Check(handler)) {
		PyErr_SetString(PyExc_TypeError, "tomboy_keybinder_bind: 2nd argument must be callable");
		return NULL;
	}

	for (iter = HA_List; iter != NULL; iter = iter->next) {
		Handler_and_Args *ha = (Handler_and_Args *) iter->data;

		if (strcmp(keystring, ha->keystring) == 0) {
			PyErr_SetString(PyExc_KeyError, "tomboy_keybinder_bind: keystring is already bound");
			return NULL;
		}
	}

	extra_args = PySequence_GetSlice(args, 2, len);
	if (extra_args == NULL) {
		return NULL;
	}

	ha = g_new(Handler_and_Args, 1);
	ha->handler = handler;
	ha->args = extra_args;
	ha->keystring = g_strdup(keystring);
	Py_XINCREF(handler);
	Py_XINCREF(extra_args);
	
	tomboy_keybinder_bind(keystring, &handler_c_func, ha);
	HA_List = g_slist_prepend(HA_List, ha);

	Py_INCREF(Py_None);
	return Py_None;
}
#line 113 "_keybinder.c"


#line 104 "_keybinder.override"
static PyObject*
_wrap_tomboy_keybinder_unbind (PyGObject *self, PyObject *args, PyObject *kwargs) 
{
	guint len;
	PyObject *first;
	char *keystring = NULL;
	GSList *iter;
	
	len = PyTuple_Size(args);
	if (len != 1) {
		PyErr_SetString(PyExc_TypeError, "tomboy_keybinder_unbind requires exactly 1 argument");
		return NULL;
	}
	if (!PyArg_ParseTuple(args, "s:tomboy_keybinder_unbind", &keystring)) {
		return NULL;
	}

	for (iter = HA_List; iter != NULL; iter = iter->next) {
		Handler_and_Args *ha = (Handler_and_Args *) iter->data;

		if (strcmp(keystring, ha->keystring) == 0) {
			tomboy_keybinder_unbind(keystring, &handler_c_func);
			HA_List = g_slist_remove(HA_List, ha);
			Py_XDECREF(ha->handler);
			Py_XDECREF(ha->args);
			g_free(ha->keystring);
			g_free(ha);

			Py_INCREF(Py_None);
			return Py_None;
		}
	}

	PyErr_SetString(PyExc_KeyError, "tomboy_keybinder_bind: keystring is not bound");
	return NULL;
}
#line 153 "_keybinder.c"


static PyObject *
_wrap_tomboy_keybinder_is_modifier(PyObject *self, PyObject *args, PyObject *kwargs)
{
    static char *kwlist[] = { "keycode", NULL };
    PyObject *py_keycode = NULL;
    int ret;
    guint keycode = 0;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs,"O:tomboy_keybinder_is_modifier", kwlist, &py_keycode))
        return NULL;
    if (py_keycode) {
        if (PyLong_Check(py_keycode))
            keycode = PyLong_AsUnsignedLong(py_keycode);
        else if (PyInt_Check(py_keycode))
            keycode = PyInt_AsLong(py_keycode);
        else
            PyErr_SetString(PyExc_TypeError, "Parameter 'keycode' must be an int or a long");
        if (PyErr_Occurred())
            return NULL;
    }
    
    ret = tomboy_keybinder_is_modifier(keycode);
    
    return PyBool_FromLong(ret);

}

static PyObject *
_wrap_tomboy_keybinder_get_current_event_time(PyObject *self)
{
    guint32 ret;

    
    ret = tomboy_keybinder_get_current_event_time();
    
    return PyLong_FromUnsignedLong(ret);

}

const PyMethodDef py_keybinder_functions[] = {
    { "tomboy_keybinder_bind", (PyCFunction)_wrap_tomboy_keybinder_bind, METH_VARARGS|METH_KEYWORDS,
      NULL },
    { "tomboy_keybinder_unbind", (PyCFunction)_wrap_tomboy_keybinder_unbind, METH_VARARGS|METH_KEYWORDS,
      NULL },
    { "tomboy_keybinder_is_modifier", (PyCFunction)_wrap_tomboy_keybinder_is_modifier, METH_VARARGS|METH_KEYWORDS,
      NULL },
    { "tomboy_keybinder_get_current_event_time", (PyCFunction)_wrap_tomboy_keybinder_get_current_event_time, METH_NOARGS,
      NULL },
    { NULL, NULL, 0, NULL }
};

/* initialise stuff extension classes */
void
py_keybinder_register_classes(PyObject *d)
{

#line 212 "_keybinder.c"
}
