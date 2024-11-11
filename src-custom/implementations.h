
/*************************************/
/* ./runtimebackports.c              */

extern _PyXI_global_state_t * _interpreters_get_global_xistate(void);
extern _PyXI_state_t * _interpreters_get_xistate(PyInterpreterState *);

// Python/pystate.c
extern long _PyInterpreterState_GetWhence(PyInterpreterState *interp);
extern void _PyInterpreterState_SetWhence(PyInterpreterState *, long);
extern PyInterpreterState * _PyInterpreterState_LookUpIDObject(PyObject *);
extern int _PyInterpreterState_FailIfRunningMain(PyInterpreterState *);
extern int _PyThreadState_IsAttached(PyThreadState *);

// Python/thread.c
extern int PyThread_ParseTimeoutArg(PyObject *arg, int blocking, PY_TIMEOUT_T *timeout);
extern PyLockStatus PyThread_acquire_lock_timed_with_retries(PyThread_type_lock, PY_TIMEOUT_T microseconds);

// Python/thread_pthread.h / Python/thread_nt.h
extern PyThread_ident_t PyThread_get_thread_ident_ex(void);

// Python/pytime.c
extern int PyTime_MonotonicRaw(PyTime_t *result);
extern int PyTime_TimeRaw(PyTime_t *result);

// Objects/dictobject.c
extern int PyDict_GetItemStringRef(PyObject *mp, const char *key, PyObject **result);
extern int PyDict_PopString(PyObject *dict, const char *key, PyObject **result);

// Objects/abstract.c
extern int _PyBuffer_ReleaseInInterpreterAndRawFree(PyInterpreterState *, Py_buffer *);

// Objecs/memoryobject.c
extern PyObject * _PyMemoryView_FromBufferProc(PyObject *, int, getbufferproc);

// Objects/weakrefobject.c
extern void _PyStaticType_ClearWeakRefs(PyInterpreterState *, PyTypeObject *);


/*************************************/
/* src-upstream/Python/initconfig.c  */

// Python/initconfig.c
extern PyObject * _PyInterpreterConfig_AsDict(PyInterpreterConfig *);
extern int _PyInterpreterConfig_InitFromDict(PyInterpreterConfig *, PyObject *);
extern int _PyInterpreterConfig_InitFromState(PyInterpreterConfig *, PyInterpreterState *);
extern int _PyInterpreterConfig_UpdateFromDict(PyInterpreterConfig *, PyObject *);


/*************************************/
/* ./3.12/Objects/typeobject.c       */

// Objects/typeobject.c
extern int _PyStaticType_InitBuiltin(PyInterpreterState *, PyTypeObject *);
extern void _PyStaticType_Dealloc(PyInterpreterState *, PyTypeObject *);
