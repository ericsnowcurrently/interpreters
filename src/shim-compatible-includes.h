
#include "Python.h"

// pycore_long.h
#define SIGN_MASK 3
#define SIGN_NEGATIVE 2
#define _PyLong_IsNegative(OP) \
    (((const PyLongObject *)(OP))->long_value.lv_tag & SIGN_MASK) == SIGN_NEGATIVE

// pycore_abstract.h
static inline int
_PyIndex_Check(PyObject *obj)
{
    PyNumberMethods *tp_as_number = Py_TYPE(obj)->tp_as_number;
    return (tp_as_number != NULL && tp_as_number->nb_index != NULL);
}

// pycore_pystate.h
extern PyInterpreterState * _PyInterpreterState_LookUpID(int64_t);
extern PyInterpreterState * PyInterpreterID_LookUp(PyObject *);
extern int _PyInterpreterState_IsRunningMain(PyInterpreterState *);
extern int _PyInterpreterState_SetRunningMain(PyInterpreterState *);
extern int _PyInterpreterState_SetNotRunningMain(PyInterpreterState *);
extern void _PyInterpreterState_FailIfRunningMain(PyInterpreterState *);
#define PyUnstable_InterpreterState_GetMainModule(INTERP) \
    _PyInterpreterState_GetMainModule(INTERP)

// pycore_interp.h
extern int _PyInterpreterState_IDInitref(PyInterpreterState *);
extern int _PyInterpreterState_IDIncref(PyInterpreterState *);
extern void _PyInterpreterState_IDDecref(PyInterpreterState *);

// pycore_typeobject.h
extern int _PyStaticType_InitBuiltin(PyInterpreterState *, PyTypeObject *);
extern void _PyStaticType_Dealloc(PyInterpreterState *, PyTypeObject *);
extern PyObject * _PyType_GetModuleName(PyTypeObject *);

// pycore_ceval.h
#define _Py_EnterRecursiveCallTstate(TSTATE, WHERE) \
    Py_EnterRecursiveCall(WHERE)
#define _Py_LeaveRecursiveCallTstate(TSTATE) \
    Py_LeaveRecursiveCall()

// pycore_initconfig.h
#define _PyStatus_OK() \
    (PyStatus){._type = _PyStatus_TYPE_OK}
#define _PyStatus_ERR(ERR_MSG) \
    (PyStatus){ \
        ._type = _PyStatus_TYPE_ERROR, \
        .err_msg = (ERR_MSG)}
#define _PyStatus_EXCEPTION(err) \
    ((err)._type != _PyStatus_TYPE_OK)

// pycore_namespace.h
extern PyObject* _PyNamespace_New(PyObject *);

// pycore_weakref.h
extern PyObject* _PyWeakref_GET_REF(PyObject *);

// pycore_global_objects.h
#define _Py_EMPTY_STR PyUnicode_InternFromString("")