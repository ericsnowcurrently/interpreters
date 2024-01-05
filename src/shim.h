
#include "Python.h"

#include <stdbool.h>


// pycore_interp.h
extern int _PyInterpreterState_IDInitref(PyInterpreterState *);
extern int _PyInterpreterState_IDIncref(PyInterpreterState *);
extern void _PyInterpreterState_IDDecref(PyInterpreterState *);

// pycore_long.h
#define SIGN_MASK 3
#define SIGN_NEGATIVE 2
#define _PyLong_IsNegative(OP) \
    (((const PyLongObject *)(OP))->long_value.lv_tag & SIGN_MASK) == SIGN_NEGATIVE

// pycore_ceval_state.h
typedef int (*_Py_pending_call_func)(void *);

// pycore_ceval.h
#define _Py_PENDING_RAWFREE 2
extern int _PyEval_AddPendingCall(
        PyInterpreterState *, _Py_pending_call_func, void *, int);
#define _Py_EnterRecursiveCallTstate(TSTATE, WHERE) \
    Py_EnterRecursiveCall(WHERE)
#define _Py_LeaveRecursiveCallTstate(TSTATE) \
    Py_LeaveRecursiveCall()

// pycore_pystate.h
extern PyInterpreterState * _PyInterpreterState_LookUpID(int64_t);
extern PyInterpreterState * PyInterpreterID_LookUp(PyObject *);
extern int _PyInterpreterState_IsRunningMain(PyInterpreterState *);
extern int _PyInterpreterState_SetRunningMain(PyInterpreterState *);
extern int _PyInterpreterState_SetNotRunningMain(PyInterpreterState *);
extern void _PyInterpreterState_FailIfRunningMain(PyInterpreterState *);
extern PyThreadState * _PyThreadState_GetCurrent(void);
typedef struct pyruntimestate _PyRuntimeState;
extern _Py_thread_local PyThreadState *_Py_tss_tstate;
#define _PyThreadState_GET() _Py_tss_tstate
#define _PyInterpreterState_GET() _PyThreadState_GET()->interp
#define _Py_IsMainInterpreter(INTERP) \
    ((INTERP) == PyInterpreterState_Main())
#define PyUnstable_InterpreterState_GetMainModule(INTERP) \
    _PyInterpreterState_GetMainModule(INTERP)

// pycore_tstate.h
#define _PyThreadState_SetWhence(TSTATE, WHENCE)

// pystate.h
#define _PyThreadState_WHENCE_INTERP 1
#define _PyThreadState_WHENCE_THREADING 2
#define _PyThreadState_WHENCE_GILSTATE 3
#define _PyThreadState_WHENCE_EXEC 4
#define PyInterpreterState_GetIDObject _PyInterpreterState_GetIDObject

// interpreteridobject.h
#define PyInterpreterID_LookUp _PyInterpreterID_LookUp

// pycore_pyerrors.h
#define _PyErr_SetString(TSTATE, EXCTYPE, MSG) \
    PyErr_SetString(EXCTYPE, MSG)

// pycore_code.h
#define _PyCode_HAS_EXECUTORS(CODE) (0)
#define _PyCode_HAS_INSTRUMENTATION(CODE) (0)

// pylifecycle.h
#define PyUnstable_AtExit _Py_AtExit

// pycore_initconfig.h
#define _PyStatus_OK() \
    (PyStatus){._type = _PyStatus_TYPE_OK}
#define _PyStatus_ERR(ERR_MSG) \
    (PyStatus){ \
        ._type = _PyStatus_TYPE_ERROR, \
        .err_msg = (ERR_MSG)}
#define _PyStatus_EXCEPTION(err) \
    ((err)._type != _PyStatus_TYPE_OK)


//#include "pycore_crossinterp.h"

// pycore_crossinterp.h
#define _PyCrossInterpreterData_DATA(DATA) ((DATA)->data)
#define _PyCrossInterpreterData_OBJ(DATA) ((DATA)->obj)
#define _PyCrossInterpreterData_INTERPID(DATA) ((DATA)->interp)
//_PyXI_session
//_PyXI_Enter()
//_PyXI_ApplyError()
//_PyXI_Exit()
//_PyXI_ApplyCapturedException()
//PyExc_InterpreterError
//PyExc_InterpreterNotFoundError

// pycore_pybuffer.h
extern int _PyBuffer_ReleaseInInterpreterAndRawFree(PyInterpreterState *, Py_buffer *);
//static inline int
//_PyBuffer_ReleaseInInterpreterAndRawFree(PyInterpreterState *interp, Py_buffer *buf)
//{
//    return _Py_CallInInterpreterAndRawFree(interp, _buffer_release_call, view);
//}

// pycore_lock.h
#define Py_CPYTHON_ATOMIC_H
#define Py_CPYTHON_ATOMIC_GCC_H
#define Py_CPYTHON_ATOMIC_MSC_H
#define Py_CPYTHON_ATOMIC_STD_H
#include "cpython/pyatomic.h"
//typedef struct { uint8_t v; } PyMutex;

// pycore_critical_section.h
#define Py_BEGIN_CRITICAL_SECTION(OBJ) do { } while (0)
#define Py_END_CRITICAL_SECTION(OBJ) do { } while (0)

// pycore_pythread.h
extern PyLockStatus PyThread_acquire_lock_timed_with_retries(PyThread_type_lock, PY_TIMEOUT_T);
extern int PyThread_ParseTimeoutArg(PyObject *, int, PY_TIMEOUT_T *);
