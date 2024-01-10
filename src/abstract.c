/* Abstract Object Interface (many thanks to Jim Fulton) */
/* This is only the code from 3.13+ that isn't in 3.12. */

#include "Python.h"
#include "pycore_abstract.h"
#include "pycore_pybuffer.h"
#include "pycore_crossinterp.h"   // _Py_CallInInterpreter()


static int
_buffer_release_call(void *arg)
{
    PyBuffer_Release((Py_buffer *)arg);
    return 0;
}

int
_PyBuffer_ReleaseInInterpreter(PyInterpreterState *interp,
                               Py_buffer *view)
{
    return _Py_CallInInterpreter(interp, _buffer_release_call, view);
}

int
_PyBuffer_ReleaseInInterpreterAndRawFree(PyInterpreterState *interp,
                                         Py_buffer *view)
{
    return _Py_CallInInterpreterAndRawFree(interp, _buffer_release_call, view);
}
