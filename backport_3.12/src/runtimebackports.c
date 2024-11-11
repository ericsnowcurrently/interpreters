
#include "Python.h"
#include "pycore_crossinterp.h"
#include "pycore_pystate.h"
#include "pycore_pythread.h"


//*************************************

#define STATIC_STR(NAME, LITERAL) \
    struct { \
        PyASCIIObject _ascii; \
        uint8_t _data[sizeof(LITERAL)]; \
    } NAME = { \
        ._ascii = { \
            /* See _PyObject_HEAD_INIT() in pycore_object.h. */ \
            .ob_base = { \
                _PyObject_EXTRA_INIT \
                .ob_refcnt = _Py_IMMORTAL_REFCNT, \
                .ob_type = &PyUnicode_Type, \
            }, \
            .length = sizeof(LITERAL) - 1, \
            .hash = -1, \
            .state = { \
                .kind = 1, \
                .compact = 1, \
                .ascii = 1, \
                .statically_allocated = 1, \
            }, \
        }, \
        ._data = LITERAL, \
    }


//*************************************
// substitutes for new _PyRuntimeState fields
// (pycore_crossinterp.h)

// In 3.12, there is no xi field, so we store it in a static variable.

typedef struct {
    struct {
        _PyXI_global_state_t base;
        int initcount;
    } xi;
} global_backport_t;
static global_backport_t global_state = {0};

// _PyRuntimeState.xi

_PyXI_global_state_t *
_interpreters_get_global_xistate(void)
{
    if (global_state.xi.initcount == 0) {
        if (_Py_xi_global_state_init(&global_state.xi.base) < 0) {
            return NULL;
        }
        // XXX Add an atexit function to call _Py_xi_global_state_fini().
    }
    global_state.xi.initcount += 1;
    return &global_state.xi.base;
}


//*************************************
// substitutes for new PyInterpreterState fields
// (pycore_crossinterp.h)

// In 3.12, there is no PyInterpreterState.xi field, nor whence field,
// so we store them in a capsule in the interpreter's dict.

typedef struct {
    struct {
        _PyXI_state_t base;
        int initialized;
    } xi;
    long whence;
} backport_t;

STATIC_STR(backport_state_key, "_interpreters_backport_state_");
#define BACKPORT_STATE_KEY_OBJ ((PyObject *)&backport_state_key)

static void
backport_capsule_destructor(PyObject *capsule)
{
    backport_t* state = (backport_t *)PyCapsule_GetPointer(capsule, NULL);
    assert(state != NULL);
    if (state->xi.initialized) {
        PyInterpreterState *interp = PyInterpreterState_Get();
        _Py_xi_state_fini(&state->xi.base, interp);
    }
    PyMem_RawFree(state);
}

static backport_t *
get_backport_state(PyInterpreterState *interp)
{
    backport_t *state = NULL;
    PyObject *dict = PyInterpreterState_GetDict(interp);
    if (dict == NULL) {
        return NULL;
    }
    PyObject *capsule = PyDict_GetItemWithError(dict, BACKPORT_STATE_KEY_OBJ);
    if (capsule == NULL) {
        if (PyErr_Occurred()) {
            return NULL;
        }
        state = (backport_t *)PyMem_RawMalloc(sizeof(backport_t));
        if (state == NULL) {
            PyErr_NoMemory();
            return NULL;
        }
        *state = (backport_t){
            .whence = _PyInterpreterState_WHENCE_UNKNOWN,
        };
        capsule = PyCapsule_New(
                    state, NULL, backport_capsule_destructor);
        if (capsule == NULL) {
            PyMem_RawFree(state);
            return NULL;
        }
        int res = PyDict_SetItem(dict, BACKPORT_STATE_KEY_OBJ, capsule);
        Py_CLEAR(capsule);
        if (res < 0) {
            return NULL;
        }
    }
    else {
        Py_INCREF(capsule);
        state = (backport_t *)PyCapsule_GetPointer(capsule, NULL);
        Py_CLEAR(capsule);
        if (state == NULL) {
            return NULL;
        }
    }
    return state;
}

// PyInterpreterState.xi

_PyXI_state_t *
_interpreters_get_xistate(PyInterpreterState *interp)
{
    backport_t *state = get_backport_state(interp);
    if (state == NULL) {
        return NULL;
    }
    if (!state->xi.initialized) {
        if (_Py_xi_state_init(&state->xi.base, interp) < 0) {
            return NULL;
        }
    }
    return &state->xi.base;
}

// PyInterpreterState.whence

long
_PyInterpreterState_GetWhence(PyInterpreterState *interp)
{
    backport_t *state = get_backport_state(interp);
    if (state == NULL) {
        return -1;
    }
    return state->whence;
}

STATIC_STR(set_whence_error, "failed to set interpreter whence");
#define SET_WHENCE_ERR_MSG ((PyObject *)&set_whence_error)
void
_PyInterpreterState_SetWhence(PyInterpreterState *interp, long whence)
{
    backport_t *state = get_backport_state(interp);
    if (state == NULL) {
        PyErr_WriteUnraisable(SET_WHENCE_ERR_MSG);
        PyErr_Clear();
        return;
    }
    state->whence = whence;
}


//*************************************
// Python/pystate.c

// from pycore_abstract.h
static inline int
_PyIndex_Check(PyObject *obj)
{
    PyNumberMethods *tp_as_number = Py_TYPE(obj)->tp_as_number;
    return (tp_as_number != NULL && tp_as_number->nb_index != NULL);
}

static int64_t
_PyInterpreterState_ObjectToID(PyObject *idobj)
{
    if (!_PyIndex_Check(idobj)) {
        PyErr_Format(PyExc_TypeError,
                     "interpreter ID must be an int, got %.100s",
                     Py_TYPE(idobj)->tp_name);
        return -1;
    }

    // This may raise OverflowError.
    // For now, we don't worry about if LLONG_MAX < INT64_MAX.
    long long id = PyLong_AsLongLong(idobj);
    if (id == -1 && PyErr_Occurred()) {
        return -1;
    }

    if (id < 0) {
        PyErr_Format(PyExc_ValueError,
                     "interpreter ID must be a non-negative int, got %R",
                     idobj);
        return -1;
    }
#if LLONG_MAX > INT64_MAX
    else if (id > INT64_MAX) {
        PyErr_SetString(PyExc_OverflowError, "int too big to convert");
        return -1;
    }
#endif
    else {
        return (int64_t)id;
    }
}

PyInterpreterState *
_PyInterpreterState_LookUpIDObject(PyObject *requested_id)
{
    int64_t id = _PyInterpreterState_ObjectToID(requested_id);
    if (id < 0) {
        return NULL;
    }
    return _PyInterpreterState_LookUpID(id);
}

int
_PyInterpreterState_FailIfRunningMain(PyInterpreterState *interp)
{
    if (_PyInterpreterState_IsRunningMain(interp)) {
        PyErr_SetString(PyExc_InterpreterError,
                        "interpreter already running");
        return -1;
    }
    return 0;
}

int
_PyThreadState_IsAttached(PyThreadState *tstate)
{
    if (!tstate->_status.active) {
        return 0;
    }
    if (tstate != _PyThreadState_GET()) {
        Py_FatalError("not current thread state");
    }
    struct _gil_runtime_state *gil = tstate->interp->ceval.gil;
    if (!_Py_atomic_load_relaxed(&gil->locked)) {
        return 0;
    }
    return (tstate != (PyThreadState*)_Py_atomic_load_relaxed(&gil->last_holder));
}


//*************************************
// Python/thread.c

int
PyThread_ParseTimeoutArg(PyObject *arg, int blocking, PY_TIMEOUT_T *timeout_p)
{
    assert(_PyTime_FromSeconds(-1) == PyThread_UNSET_TIMEOUT);
    if (arg == NULL || arg == Py_None) {
        *timeout_p = blocking ? PyThread_UNSET_TIMEOUT : 0;
        return 0;
    }
    if (!blocking) {
        PyErr_SetString(PyExc_ValueError,
                        "can't specify a timeout for a non-blocking call");
        return -1;
    }

    PyTime_t timeout;
    if (_PyTime_FromSecondsObject(&timeout, arg, _PyTime_ROUND_TIMEOUT) < 0) {
        return -1;
    }
    if (timeout < 0) {
        PyErr_SetString(PyExc_ValueError,
                        "timeout value must be a non-negative number");
        return -1;
    }

    if (_PyTime_AsMicroseconds(timeout,
                               _PyTime_ROUND_TIMEOUT) > PY_TIMEOUT_MAX) {
        PyErr_SetString(PyExc_OverflowError,
                        "timeout value is too large");
        return -1;
    }
    *timeout_p = timeout;
    return 0;
}

PyLockStatus
PyThread_acquire_lock_timed_with_retries(PyThread_type_lock lock,
                                         PY_TIMEOUT_T timeout)
{
    PyThreadState *tstate = _PyThreadState_GET();
    PyTime_t endtime = 0;
    if (timeout > 0) {
        endtime = _PyDeadline_Init(timeout);
    }

    PyLockStatus r;
    do {
        PyTime_t microseconds;
        microseconds = _PyTime_AsMicroseconds(timeout, _PyTime_ROUND_CEILING);

        /* first a simple non-blocking try without releasing the GIL */
        r = PyThread_acquire_lock_timed(lock, 0, 0);
        if (r == PY_LOCK_FAILURE && microseconds != 0) {
            Py_BEGIN_ALLOW_THREADS
            r = PyThread_acquire_lock_timed(lock, microseconds, 1);
            Py_END_ALLOW_THREADS
        }

        if (r == PY_LOCK_INTR) {
            /* Run signal handlers if we were interrupted.  Propagate
             * exceptions from signal handlers, such as KeyboardInterrupt, by
             * passing up PY_LOCK_INTR.  */
            if (_PyEval_MakePendingCalls(tstate) < 0) {
                return PY_LOCK_INTR;
            }

            /* If we're using a timeout, recompute the timeout after processing
             * signals, since those can take time.  */
            if (timeout > 0) {
                timeout = _PyDeadline_Get(endtime);

                /* Check for negative values, since those mean block forever.
                 */
                if (timeout < 0) {
                    r = PY_LOCK_FAILURE;
                }
            }
        }
    } while (r == PY_LOCK_INTR);  /* Retry if we were interrupted. */

    return r;
}

PyThread_ident_t
PyThread_get_thread_ident_ex(void)
{
#if defined(HAVE_PTHREAD_STUBS)
    return 0;
#elif defined(_USE_PTHREADS)  /* AKA _PTHREADS */
    return (PyThread_ident_t)pthread_self();
#elif defined(NT_THREADS)
    return GetCurrentThreadId();
#else
    return 0;
#endif
}


//*************************************
// Python/pytime.c

int
PyTime_MonotonicRaw(PyTime_t *result)
{
    *result = _PyTime_GetMonotonicClock();
    return 0;
}

int
PyTime_TimeRaw(PyTime_t *result)
{
    *result = _PyTime_GetSystemClock();
    return 0;
}


//*************************************
// Objects/dictobject.c

int
PyDict_GetItemStringRef(PyObject *mp, const char *key, PyObject **result)
{
    int rc = -1;
    PyObject *key_obj = PyUnicode_FromString(key);
    if (key_obj == NULL) {
        return -1;
    }
    PyObject *obj = PyDict_GetItemWithError(mp, key_obj);
    Py_DECREF(key_obj);
    if (obj == NULL) {
        if (PyErr_Occurred()) {
            return -1;
        }
        rc = 0;
    }
    else {
        rc = 1;
    }
    if (result != NULL) {
        Py_XINCREF(obj);
        *result = obj;
    }
    return rc;
}

int
PyDict_PopString(PyObject *dict, const char *key, PyObject **result)
{
    int res = PyDict_GetItemStringRef(dict, key, result);
    if (res == 1) {
        if (PyDict_DelItemString(dict, key) < 0) {
            if (!PyErr_ExceptionMatches(PyExc_KeyError)) {
                if (result != NULL) {
                    Py_CLEAR(*result);
                }
                return -1;
            }
            PyErr_Clear();
        }
    }
    return res;
}

PyDictKeysObject *
_PyDict_NewKeysForClass(void)
{
    // This method is only needed for heap types.
    Py_UNREACHABLE();
    return NULL;
}


//*************************************
// Objects/abstract.c

static int
_buffer_release_call(void *arg)
{
    PyBuffer_Release((Py_buffer *)arg);
    return 0;
}

int
_PyBuffer_ReleaseInInterpreterAndRawFree(PyInterpreterState *interp,
                                         Py_buffer *view)
{
    // XXX Needs to add larger pending calls queue?
    return _Py_CallInInterpreterAndRawFree(interp, _buffer_release_call, view);
}


//*************************************
// Objects/memoryobject.c

PyObject *
_PyMemoryView_FromBufferProc(PyObject *v, int flags, getbufferproc bufferproc)
{
    Py_buffer buf = {0};
    if (bufferproc(v, &buf, flags) < 0) {
        return NULL;
    }
    PyObject *res = PyMemoryView_FromBuffer(&buf);
    ((PyMemoryViewObject *)res)->mbuf->master.obj = buf.obj;
    ((PyMemoryViewObject *)res)->view.obj = buf.obj;
    PyBuffer_Release(&buf);
    return res;
}


//*************************************
// Objects/weakrefobbject.c

void
_PyStaticType_ClearWeakRefs(PyInterpreterState *interp, PyTypeObject *type)
{
    static_builtin_state *state = _PyStaticType_GetState(interp, type);
    PyObject **list = _PyStaticType_GET_WEAKREFS_LISTPTR(state);
    while (*list != NULL) {
        Py_CLEAR(((PyWeakReference *)*list)->wr_callback);
        _PyWeakref_ClearRef((PyWeakReference *)*list);
    }
}
