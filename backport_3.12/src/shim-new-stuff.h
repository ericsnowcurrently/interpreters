// See ./implementations.h for the list where functions are implemented.
// See the bottom for customizations.


/*************************************/
/* new Python.h-included headers     */

#undef Py_ATOMIC_H
#include "pyatomic.h"
#include "lock.h"


/*************************************/
/* constants                         */

// cpython/pystate.h
#define _PyThreadState_WHENCE_NOTSET -1
#define _PyThreadState_WHENCE_UNKNOWN 0
#define _PyThreadState_WHENCE_INIT 1
#define _PyThreadState_WHENCE_FINI 2
#define _PyThreadState_WHENCE_THREADING 3
#define _PyThreadState_WHENCE_GILSTATE 4
#define _PyThreadState_WHENCE_EXEC 5

// pycore_interp.h
#define _PyInterpreterState_WHENCE_UNKNOWN 0
#define _PyInterpreterState_WHENCE_RUNTIME 1
#define _PyInterpreterState_WHENCE_LEGACY_CAPI 2
#define _PyInterpreterState_WHENCE_CAPI 3
#define _PyInterpreterState_WHENCE_XI 4
#define _PyInterpreterState_WHENCE_STDLIB 5

// pycore_pythread.h
#define PyThread_UNSET_TIMEOUT ((PyTime_t)(-1 * 1000 * 1000 * 1000))

// Include/moduleobject.h
#define Py_mod_gil 0
#define Py_MOD_GIL_NOT_USED NULL


/*************************************/
/* macros                            */

// pyport.h
#define _Py_FALLTHROUGH do { } while (0)

// pymacro.h
#define _Py_CONTAINER_OF(ptr, type, member) \
    (type*)((char*)ptr - offsetof(type, member))

// pycore_code.h
#define _PyCode_HAS_EXECUTORS(CODE) (0)
//    (CODE->co_executors != NULL)
//#define _PyCode_HAS_INSTRUMENTATION(CODE) (0)
#define _PyCode_HAS_INSTRUMENTATION(CODE) \
    (CODE->_co_instrumentation_version > 0)


/*************************************/
/* typedefs                          */

// pycore_ceval.h
typedef int (*_Py_pending_call_func)(void *);

// pycore_pythread.h
typedef unsigned long long PyThread_ident_t;

// cpython/modsupport.h
typedef struct {
    uint8_t v;
} _PyOnceFlag;

// pycore_typeobject.h
//typedef struct {
//    PyTypeObject *type;
//    // This field is the only difference from 3.12's static_builtin_state.
//    int isbuiltin;
//    int readying;
//    int ready;
//    PyObject *tp_dict;
//    PyObject *tp_subclasses;
//    PyObject *tp_weaklist;
//} managed_static_type_state;


/*************************************/
/* function equivalents              */

// cpython/pystate.h
#define _PyThreadState_NewBound(INTERP, WHENCE) \
    PyThreadState_New(INTERP)

// pycore_interp.h
#define _PyInterpreterState_IsReady(INTERP) (1)

// cpython/pyerrors.h
#define PyErr_FormatUnraisable(msg) \
    _PyErr_WriteUnraisableMsg(msg, NULL)

// pycore_ceval.h
#define _Py_EnterRecursiveCallTstate(TSTATE, WHERE) \
    Py_EnterRecursiveCall(WHERE)
#define _Py_LeaveRecursiveCallTstate(TSTATE) \
    Py_LeaveRecursiveCall()

// Include.object.h
#define PyType_GetModuleName(TYPE) \
    PyObject_GetAttrString(((PyObject *)TYPE), "__module__")

// pycore_weakref.h
#define _PyWeakref_GET_REF(wr) \
    Py_NewRef(PyWeakref_GetObject(wr))


/*************************************/
/* backported functions              */

// cpython/pystate.h
extern int _PyInterpreterState_FailIfRunningMain(PyInterpreterState *);
//extern PyThreadState * _PyThreadState_NewBound(PyInterpreterState *, int);

// pycore_pystate.h
extern int _PyThreadState_IsAttached(PyThreadState *);

// pycore_interp.h
extern long _PyInterpreterState_GetWhence(PyInterpreterState *interp);
extern void _PyInterpreterState_SetWhence(PyInterpreterState *, long);
//extern int _PyInterpreterState_IsReady(PyInterpreterState *interp);
extern PyInterpreterState * _PyInterpreterState_LookUpIDObject(PyObject *);

// pycore_pylifecycle.h
extern PyObject * _PyInterpreterConfig_AsDict(PyInterpreterConfig *);
extern int _PyInterpreterConfig_InitFromDict(PyInterpreterConfig *, PyObject *);
extern int _PyInterpreterConfig_InitFromState(PyInterpreterConfig *, PyInterpreterState *);
extern int _PyInterpreterConfig_UpdateFromDict(PyInterpreterConfig *, PyObject *);

// pycore_pythread.h
extern PyThread_ident_t PyThread_get_thread_ident_ex(void);
extern int PyThread_ParseTimeoutArg(PyObject *, int, PY_TIMEOUT_T *);
extern PyLockStatus PyThread_acquire_lock_timed_with_retries(PyThread_type_lock, PY_TIMEOUT_T);

// pycore_pytime.h
extern int PyTime_MonotonicRaw(PyTime_t *);
extern int PyTime_TimeRaw(PyTime_t *);

// pycore_pybuffer.h
// XXX Needs to add larger pending calls queue?
extern int _PyBuffer_ReleaseInInterpreterAndRawFree(PyInterpreterState *, Py_buffer *);

// Include.object.h
//extern PyObject * PyType_GetModuleName(PyTypeObject *type);

// Include/dictobject.h / Include/cpython/dictobject.h
extern int PyDict_GetItemStringRef(PyObject *mp, const char *key, PyObject **result);
extern int PyDict_PopString(PyObject *dict, const char *key, PyObject **result);


//===============================================
// customizations
//===============================================

//#include "pycore_lock.h"
#include "pycore_crossinterp.h"


/*************************************/
/* runtime state                     */

extern _PyXI_global_state_t * _interpreters_get_global_xistate(void);
extern _PyXI_state_t * _interpreters_get_xistate(PyInterpreterState *);

// pycore_crossinterp.h
#undef _PyXI_GET_GLOBAL_STATE
#undef _PyXI_GET_STATE
#define _PyXI_GET_GLOBAL_STATE(interp) \
    _interpreters_get_global_xistate()
#define _PyXI_GET_STATE(interp) \
    _interpreters_get_xistate(interp)

// pycore_typeobject.h
//extern int _PyStaticType_InitBuiltin(PyInterpreterState *, PyTypeObject *);
//extern void _PyStaticType_FiniBuiltin(PyInterpreterState *, PyTypeObject *);


/*************************************/
/* backported functions              */

// pycore_crossinterp.h
// XXX Needs to add larger pending calls queue?
//extern int _PyCrossInterpreterData_ReleaseAndRawFree(_PyCrossInterpreterData *);
