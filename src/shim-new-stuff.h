
// pystate.h
#define _PyThreadState_WHENCE_INTERP 1
#define _PyThreadState_WHENCE_THREADING 2
#define _PyThreadState_WHENCE_GILSTATE 3
#define _PyThreadState_WHENCE_EXEC 4
#define PyInterpreterState_GetIDObject _PyInterpreterState_GetIDObject

// pycore_tstate.h
#define _PyThreadState_SetWhence(TSTATE, WHENCE)

// pycore_crossinterp.h
#define _PyCrossInterpreterData_DATA(DATA) ((DATA)->data)
#define _PyCrossInterpreterData_OBJ(DATA) ((DATA)->obj)
#define _PyCrossInterpreterData_INTERPID(DATA) ((DATA)->interp)
#define _PyCrossInterpreterData_SET_FREE(DATA, VAL) \
    do {(DATA)->free = VAL; } while (0)
#define _PyCrossInterpreterData_SET_NEW_OBJECT(DATA, VAL) \
    do {(DATA)->new_object = VAL; } while (0)

// pycore_code.h
#define _PyCode_HAS_EXECUTORS(CODE) (0)
#define _PyCode_HAS_INSTRUMENTATION(CODE) (0)

// pycore_lock.h
typedef struct _PyMutex { uint8_t v; } PyMutex;
extern void PyMutex_Lock(PyMutex *);
extern void PyMutex_Unlock(PyMutex *);

// pycore_interp.h
// XXX
extern struct _xi_state * _PyInterpreterState_GetXIState(PyInterpreterState *);
//static inline struct _xi_state *
//_PyInterpreterState_GetXIState(PyInterpreterState *interp)
//{
//}

// pycore_ceval_state.h
typedef int (*_Py_pending_call_func)(void *);

// pycore_ceval.h
#define _Py_PENDING_RAWFREE 2
// XXX Add a hack to support many pending calls.
extern int _PyEval_AddPendingCall(
        PyInterpreterState *, _Py_pending_call_func, void *, int);

// pylifecycle.h
#define PyUnstable_AtExit _Py_AtExit

// pycore_pythread.h
/*
XXX
PyThread_acquire_lock_timed_with_retries()
PyThread_ParseTimeoutArg()
*/

// pycore_pybuffer.h
// XXX
extern int _PyBuffer_ReleaseInInterpreterAndRawFree(PyInterpreterState *, Py_buffer *);
//static inline int
//_PyBuffer_ReleaseInInterpreterAndRawFree(PyInterpreterState *interp, Py_buffer *buf)
//{
//    return _Py_CallInInterpreterAndRawFree(interp, _buffer_release_call, view);
//}
