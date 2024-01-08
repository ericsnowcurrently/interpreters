
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
extern int _PyInterpreterState_IsRunningMain(PyInterpreterState *);
extern int _PyInterpreterState_SetRunningMain(PyInterpreterState *);
extern int _PyInterpreterState_SetNotRunningMain(PyInterpreterState *);
//extern void _PyInterpreterState_FailIfRunningMain(PyInterpreterState *);
#define _PyInterpreterState_FailIfRunningMain(interp) \
    do { \
        if (_PyInterpreterState_IsRunningMain(interp)) { \
            PyErr_SetString(PyExc_RuntimeError, \
                            "interpreter already running"); \
        } \
    } while (0)
#define PyUnstable_InterpreterState_GetMainModule(INTERP) \
    _PyInterpreterState_GetMainModule(INTERP)
#define _PyThreadState_GET PyThreadState_GET

// pycore_interp.h
extern int _PyInterpreterState_IDInitref(PyInterpreterState *);
extern int _PyInterpreterState_IDIncref(PyInterpreterState *);
extern void _PyInterpreterState_IDDecref(PyInterpreterState *);

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

// pycore_critical_section.h
#define Py_BEGIN_CRITICAL_SECTION(ref_obj)
#define Py_END_CRITICAL_SECTION()

// pycore_global_objects.h
#define _Py_EMPTY_STR PyUnicode_InternFromString("")
