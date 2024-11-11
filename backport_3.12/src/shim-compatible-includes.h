
#include "Python.h"

#include "pycore_runtime.h"


/*************************************/
/* renamed                           */

// pycore_pystate.h
#define _PyThreadState_GET PyThreadState_GET
#define _PyInterpreterState_GET PyInterpreterState_Get

// cpython/pystate.h
#define PyUnstable_InterpreterState_GetMainModule(INTERP) \
    _PyInterpreterState_GetMainModule(INTERP)

// cpython/pylifecycle.h  (pycore_atexit.h)
#define PyUnstable_AtExit _Py_AtExit

// cpython/pytime.h
#define PyTime_t _PyTime_t

// pycore_typeobject.h
#define _PyStaticType_FiniBuiltin _PyStaticType_Dealloc
typedef static_builtin_state managed_static_type_state;


/*************************************/
/* using a dummy/empty include file  */

// pycore_pystate.h
#define _PyInterpreterState_Main() \
    _PyRuntime.interpreters.main
#define _Py_IsMainInterpreter(INTERP) \
    (INTERP == _PyInterpreterState_Main())
extern int _PyInterpreterState_IsRunningMain(PyInterpreterState *);
extern int _PyInterpreterState_SetRunningMain(PyInterpreterState *);
extern int _PyInterpreterState_SetNotRunningMain(PyInterpreterState *);
extern PyObject * _PyInterpreterState_GetIDObject(PyInterpreterState *);

// pycore_interp.h
extern PyInterpreterState * _PyInterpreterState_LookUpID(int64_t);

// pycore_ceval.h
#define _Py_PENDING_RAWFREE 2
// XXX Needs to add larger pending calls queue?
extern int _PyEval_AddPendingCall(PyInterpreterState *, int (*func)(void *), void *, int);

// pycore_namespace.h
extern PyObject * _PyNamespace_New(PyObject *kwds);


/*************************************/
/* signature changed                 */

// pycore_interp.h
#define _PyInterpreterState_IDIncref(VAL) \
    ((void)_PyInterpreterState_IDIncref(VAL))


/*************************************/
/* 3.12 symbol not exported          */

// See ,/implementations.h for where the functions are implemented.

// pycore_typeobject.h
extern void _PyStaticType_ClearWeakRefs(PyInterpreterState *, PyTypeObject *);
extern int _PyStaticType_InitBuiltin(PyInterpreterState *, PyTypeObject *);
extern void _PyStaticType_Dealloc(PyInterpreterState *, PyTypeObject *);

// pycore_memory.h
extern PyObject * _PyMemoryView_FromBufferProc(PyObject *, int, getbufferproc);
