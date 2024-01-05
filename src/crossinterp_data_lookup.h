
/*******************/
/* the lookup func */
/*******************/

static crossinterpdatafunc _lookup_getdata_from_registry(
                                            PyInterpreterState *, PyObject *);

static crossinterpdatafunc
lookup_getdata(PyInterpreterState *interp, PyObject *obj)
{
   /* Cross-interpreter objects are looked up by exact match on the class.
      We can reassess this policy when we move from a global registry to a
      tp_* slot. */
    return _lookup_getdata_from_registry(interp, obj);
}


/*************/
/* lifecycle */
/*************/

//static void _init_local_xi_state(PyInterpreterState *);
//static void _fini_local_xi_state(PyInterpreterState *);

static void
xid_lookup_init(PyInterpreterState *interp)
{
//    _init_local_xi_state(interp);
}

static void
xid_lookup_fini(PyInterpreterState *interp)
{
//    _fini_local_xi_state(interp);
}


/***********************************************/
/* a registry of {type -> crossinterpdatafunc} */
/***********************************************/

// In 3.12 the global registry is implemented in pystate.c, but there
// is not per-interpreter registry (for heap types).  We add it here,
// via PyInterpreterState.dict.

static struct _xidregistry *
_new_local_xidregistry(void)
{
    struct _xidregistry *reg = PyMem_RawMalloc(sizeof(struct _xidregistry));
    if (reg == NULL) {
        PyErr_NoMemory();
        return NULL;
    }
    *reg = (struct _xidregistry){
        .initialized=1,
    };
    return reg;
}

static void
_free_local_xidregistry(struct _xidregistry *reg)
{
    struct _xidregitem *cur = reg->head;
    reg->head = NULL;
    while (cur != NULL) {
        struct _xidregitem *next = cur->next;
        Py_XDECREF(cur->weakref);
        PyMem_RawFree(cur);
        cur = next;
    }
    PyMem_RawFree(reg);
}

static void
_capsule_fini(PyObject *capsule)
{
    struct _xidregistry *reg = (struct _xidregistry *)PyCapsule_GetPointer(capsule, NULL);
    assert(reg != NULL);
    _free_local_xidregistry(reg);
}

static struct _xidregistry *
_get_local_xidregistry(PyInterpreterState *interp)
{
    struct _xidregistry *reg = NULL;

    // Get the registry from PyInterpreterState.dict (or create it).
    PyObject *ns = PyInterpreterState_GetDict(interp);
    if (ns == NULL) {
        if (!PyErr_Occurred()) {
            PyErr_SetString(PyExc_RuntimeError,
                            "no interpreter dict found for XID registry");
        }
        return NULL;
    }
#define INTERP_KEY "_xid_registry"
    PyObject *regobj = PyDict_GetItemString(ns, INTERP_KEY);
    if (regobj == NULL) {
        assert(!PyErr_Occurred());
        PyObject *key = PyUnicode_FromString(INTERP_KEY);
        if (key == NULL) {
            return NULL;
        }
        regobj = PyDict_GetItemWithError(ns, key);
        Py_DECREF(key);
        if (regobj == NULL) {
            if (PyErr_Occurred()) {
                return NULL;
            }
            // Create it and add the capsule.
            reg = _new_local_xidregistry();
            if (reg == NULL) {
                return NULL;
            }
            regobj = PyCapsule_New(reg, NULL, _capsule_fini);
            if (regobj == NULL) {
                PyMem_RawFree(reg);
                return NULL;
            }
            int res = PyDict_SetItemString(ns, INTERP_KEY, regobj);
            Py_CLEAR(regobj);
            if (res < 0) {
                return NULL;
            }
        }
    }
    if (reg == NULL) {
        assert(regobj != NULL);
        reg = (struct _xidregistry *)PyCapsule_GetPointer(regobj, NULL);
        Py_DECREF(regobj);
        if (reg == NULL) {
            return NULL;
        }
    }
    Py_XDECREF(regobj);
    return reg;
}

//struct _local_xidregistry {
//    struct _xidregistry registry;
//    int64_t interpid;
//};
//struct _local_xidregistries {
//    struct _local_xidregistry *registries;
//    int64_t count;
//    // We pre-allocate room for the first 10.
//    struct _local_xidregistry _registries[10];
//};
//struct _local_xi_state {
//    // 0 means "not initialized"
//    int64_t interp_count;
//    // We leak the mutex (and never re-initialie it).
//    PyThread_type_lock mutex;
//    // Each bucket is indexed by the low digit of the interpreter ID.
//    struct _local_xidregistries *xid[10];
//};
//static struct _local_xi_state _xistate = {0};
//
//static void
//_init_local_xi_state(PyInterpreterState *interp)
//{
//    if (_xistate.mutex == NULL) {
//        _PyThread_EnsureLockInitialized(&_xistate.mutex);
//    }
//    PyThread_acquire_lock(_xistate.mutex, WAIT_LOCK);
//
//
//    if (!_xistate.initialized) {
//        // There is 
//        _xistate.initialized = 1;
//        assert(_xistate.mutex == NULL);
//    }
//
//    PyThread_release_lock(_xistate.mutex);
//}
//
//static void
//_fini_local_xi_state(PyInterpreterState *interp)
//{
//}
//
//static struct _xidregistry *
//_get_local_registry(PyInterpreterState *interp)
//{
//
//    if (interp == PyInterpreterState_Main()) {
//        return &_xidregistries[0]._registries[0];
//    }
//    else {
//    }
//}

static int
_xidregistry_add_type(struct _xidregistry *reg,
                      PyTypeObject *cls, crossinterpdatafunc getdata)
{
    struct _xidregitem *newhead = PyMem_RawMalloc(sizeof(struct _xidregitem));
    if (newhead == NULL) {
        return -1;
    }
    *newhead = (struct _xidregitem){
        // We do not keep a reference, to avoid keeping the class alive.
        .cls = cls,
        .refcount = 1,
        .getdata = getdata,
    };
    if (cls->tp_flags & Py_TPFLAGS_HEAPTYPE) {
        // XXX Assign a callback to clear the entry from the registry?
        newhead->weakref = PyWeakref_NewRef((PyObject *)cls, NULL);
        if (newhead->weakref == NULL) {
            PyMem_RawFree(newhead);
            return -1;
        }
    }
    newhead->next = reg->head;
    if (newhead->next != NULL) {
        newhead->next->prev = newhead;
    }
    reg->head = newhead;
    return 0;
}

static struct _xidregitem *
_xidregistry_remove_entry(struct _xidregistry *reg, struct _xidregitem *entry)
{
    struct _xidregitem *next = entry->next;
    if (entry->prev != NULL) {
        assert(entry->prev->next == entry);
        entry->prev->next = next;
    }
    else {
        assert(reg->head == entry);
        reg->head = next;
    }
    if (next != NULL) {
        next->prev = entry->prev;
    }
    Py_XDECREF(entry->weakref);
    PyMem_RawFree(entry);
    return next;
}

static struct _xidregitem *
_xidregistry_find_type(struct _xidregistry *reg, PyTypeObject *cls)
{
    struct _xidregitem *cur = reg->head;
    while (cur != NULL) {
        if (cur->weakref != NULL) {
            // cur is/was a heap type.
            PyObject *registered = _PyWeakref_GET_REF(cur->weakref);
            if (registered == NULL) {
                // The weakly ref'ed object was freed.
                cur = _xidregistry_remove_entry(reg, cur);
                continue;
            }
            assert(PyType_Check(registered));
            assert(cur->cls == (PyTypeObject *)registered);
            assert(cur->cls->tp_flags & Py_TPFLAGS_HEAPTYPE);
            Py_DECREF(registered);
        }
        if (cur->cls == cls) {
            return cur;
        }
        cur = cur->next;
    }
    return NULL;
}

int
_PyCrossInterpreterData_RegisterClassLocal(PyInterpreterState *interp,
                                           PyTypeObject *cls,
                                           crossinterpdatafunc getdata)
{
    assert(cls->tp_flags & Py_TPFLAGS_HEAPTYPE);
    struct _xidregistry *reg = _get_local_xidregistry(interp);
    if (reg == NULL) {
        return -1;
    }
    return _xidregistry_add_type(reg, cls, getdata);
}


static crossinterpdatafunc
_lookup_getdata_from_registry(PyInterpreterState *interp, PyObject *obj)
{
    assert(interp == PyInterpreterState_Get());
    PyTypeObject *cls = Py_TYPE(obj);
    assert(cls != NULL);
    if (cls->tp_flags & Py_TPFLAGS_HEAPTYPE) {
        struct _xidregistry *reg = _get_local_xidregistry(interp);
        if (reg == NULL) {
            return NULL;
        }
        struct _xidregitem *matched = _xidregistry_find_type(reg, cls);
        return matched != NULL ? matched->getdata : NULL;
    }
    else {
        return _PyCrossInterpreterData_Lookup(obj);
    }
}
