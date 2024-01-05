
extern int _PyCrossInterpreterData_RegisterClassLocal(
    PyInterpreterState *interp,
    PyTypeObject *cls,
    crossinterpdatafunc getdata);

static int
ensure_xid_class(PyTypeObject *cls, crossinterpdatafunc getdata)
{
    assert(cls->tp_flags & Py_TPFLAGS_HEAPTYPE);
    PyInterpreterState *interp = PyInterpreterState_Get();
    return _PyCrossInterpreterData_RegisterClassLocal(interp, cls, getdata);
}
