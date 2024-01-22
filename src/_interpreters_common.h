
#define _RESOLVE_MODINIT_FUNC_NAME(NAME) \
    PyInit_ ## NAME
#define RESOLVE_MODINIT_FUNC_NAME(NAME) \
    _RESOLVE_MODINIT_FUNC_NAME(NAME)


extern int _PyCrossInterpreterData_RegisterClassLocal(
    PyInterpreterState *interp,
    PyTypeObject *cls,
    crossinterpdatafunc getdata);

static int
ensure_xid_class(PyTypeObject *cls, crossinterpdatafunc getdata)
{
    if (cls->tp_flags & _Py_TPFLAGS_STATIC_BUILTIN) {
        return _PyCrossInterpreterData_RegisterClass(cls, getdata);
    }
    PyInterpreterState *interp = PyInterpreterState_Get();
    return _PyCrossInterpreterData_RegisterClassLocal(interp, cls, getdata);
}
