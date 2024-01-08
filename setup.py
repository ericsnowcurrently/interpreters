import os
import os.path

from setuptools import Extension, setup

Py_DEBUG = (os.getenv('Py_DEBUG') is not None)
if Py_DEBUG:
    DEBUG = True
else:
    DEBUG = (os.getenv('DEBUG') is not None)

EXT_COMMON = dict(
    language='c',
    include_dirs=[
        'src/Include',
        'src/Include/internal',
    ],
    define_macros=[
        ('Py_BUILD_CORE', '1'),
        *([
            ('Py_DEBUG', '1'),
#            ('Py_REF_DEBUG', '1'),
        ] if Py_DEBUG else []),
    ],
    extra_compile_args=[
        '-include', 'src/shim-compatible-includes.h',
        '-include', 'src/shim-new-stuff.h',
        #*([ '-g', '-Og'] if DEBUG else [])
        *([ '-g', '-O0'] if DEBUG else [])
    ],
)
SOURCES_COMMON = [
    'src/crossinterp.c',
]


setup(
    ext_modules=[
        Extension(
            name='_interpreters',
            sources=['src/_interpretersmodule.c',
                     'src/abstract.c',
                     *SOURCES_COMMON],
            **EXT_COMMON,
        ),
        Extension(
            name='_interpqueues',
            sources=['src/_interpqueuesmodule.c',
                     *SOURCES_COMMON],
            **EXT_COMMON,
        ),
        Extension(
            name='_interpchannels',
            sources=['src/_interpchannelsmodule.c',
                     'src/thread.c',
                     *SOURCES_COMMON],
            **EXT_COMMON,
        ),
    ],
)
