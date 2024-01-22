
/* lifecycle */

static int
init_exceptions(PyInterpreterState *interp)
{
    int err = -1;
    PyObject *ns = PyInterpreterState_GetDict(interp);
    if (ns == NULL) {
        return -1;
    }
    PyObject *exctype;

    // "PyExc_InterpreterError"
    exctype = PyErr_NewExceptionWithDoc(
        "interpreters.InterpreterError",
        "A cross-interpreter operation failed",
        NULL, NULL);
    if (exctype == NULL) {
        err = -1;
        goto finally;
    }
    err = PyDict_SetItemString(ns, "PyExc_InterpreterError", exctype);
    Py_DECREF(exctype);
    if (err < 0) {
        goto finally;
    }
    PyObject *basetype = exctype;

    // PyExc_InterpreterNotFoundError
    exctype = PyErr_NewExceptionWithDoc(
        "interpreters.InterpreterNotFoundError",
        "An interpreter was not found",
        basetype, NULL);
    if (exctype == NULL) {
        err = -1;
        goto finally;
    }
    err = PyDict_SetItemString(ns, "PyExc_InterpreterNotFoundError", exctype);
    Py_DECREF(exctype);
    if (err < 0) {
        goto finally;
    }

    // NotShareableError
    exctype = PyErr_NewException(
        "interpreters.NotShareableError",
        PyExc_ValueError, NULL);
    if (exctype == NULL) {
        err = -1;
        goto finally;
    }
    err = PyDict_SetItemString(ns, "NotShareableError", exctype);
    Py_DECREF(exctype);
    if (err < 0) {
        goto finally;
    }

    err = 0;

finally:
    Py_DECREF(ns);
    return err;
}

static void
fini_exceptions(PyInterpreterState *interp)
{
    PyObject *ns = PyInterpreterState_GetDict(interp);
    if (ns == NULL) {
        PyErr_Clear();
        return;
    }
    if (PyDict_DelItemString(ns, "NotShareableError") < 0) {
        PyErr_Clear();
    }
    if (PyDict_DelItemString(ns, "PyExc_InterpreterError") < 0) {
        PyErr_Clear();
    }
    if (PyDict_DelItemString(ns, "PyExc_InterpreterNotFoundError") < 0) {
        PyErr_Clear();
    }
    Py_DECREF(ns);
}


/* lookup */

PyObject *
_get_exctype(PyInterpreterState *interp, const char *name)
{
    PyObject *ns = PyInterpreterState_GetDict(interp);
    if (ns == NULL) {
        return NULL;
    }
    PyObject *exctype = PyDict_GetItemString(ns, name);
    Py_DECREF(ns);
    if (exctype == NULL) {
        assert(PyErr_Occurred());
        return NULL;
    }
    return exctype;
}

static PyObject *
_get_not_shareable_error_type(PyInterpreterState *interp)
{
    return _get_exctype(interp, "NotShareableError");
}


/* adapters */

PyInterpreterState *
_PyInterpreterState_LookUpIDFixed(int64_t id)
{
    PyInterpreterState *interp = _PyInterpreterState_LookUpID(id);
    if (interp != NULL) {
        return interp;
    }

    PyObject *exc = PyErr_GetRaisedException();
    assert(exc != NULL && PyErr_GivenExceptionMatches(exc, PyExc_RuntimeError));
#define ARGS ((PyBaseExceptionObject *)exc)->args
    assert(PyTuple_Size(ARGS) == 1);
    assert(!strncmp(PyUnicode_AsUTF8(
                        PyTuple_GetItem(ARGS, 0)),
                    "unrecognized interpreter ID ",
                    46));
#undef ARGS
    // We don't need to decref the existing ob_type
    // bcause it is a builtin static type.
    exc->ob_type = (PyTypeObject *)PyExc_InterpreterNotFoundError;
    PyErr_SetRaisedException(exc);
    return NULL;
}
