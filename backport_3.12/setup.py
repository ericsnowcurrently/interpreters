import os
import os.path
import sys

from setuptools import Extension, setup


#Py_DEBUG = (os.getenv('Py_DEBUG') is not None)
Py_DEBUG = hasattr(sys, 'gettotalrefcount')
if Py_DEBUG:
    DEBUG = True
else:
    DEBUG = (os.getenv('DEBUG') is not None)

EXT_COMMON = dict(
    language='c',
    include_dirs=[
        'src/3.12/Include/internal',
        'src/Include',
        'src/Include/internal',
    ],
    define_macros=[
        ('Py_BUILD_CORE_MODULE', '1'),
#        *([
#            ('Py_DEBUG', '1'),
##            ('Py_REF_DEBUG', '1'),
#        ] if DEBUG else []),
    ],
    extra_compile_args=[
        '-include', 'src/shim-compatible-includes.h',
        '-include', 'src/shim-new-stuff.h',
        #*([ '-g', '-Og'] if DEBUG else [])
    ],
)

#DEPENDENCIES = [
#    'src/Python/interpconfig',
#    'src/Python/crossinterp',
#    'src/Python/lock',
#    'src/Python/parking_lot',
#    'src/runtimebackports',
#    'src/3.12/Objects/typeobject',
#]
#EXTRA_SOURCES = [f'{v}.c' for v in DEPENDENCIES]
#EXTRA_OBJECTS = [f'{v}.o' for v in DEPENDENCIES]
SOURCES_COMMON = [
    'src/Python/interpconfig.c',
    'src/Python/crossinterp.c',
    'src/Python/lock.c',
    'src/Python/parking_lot.c',
    'src/runtimebackports.c',
    'src/3.12/Objects/typeobject.c',
]

setup(
    ext_modules=[
        Extension(
            name='_interpreters',
            sources=['src/_interpretersmodule.c',
                     *SOURCES_COMMON],
#                     *EXTRA_SOURCES],
            **EXT_COMMON,
        ),
        Extension(
            name='_interpqueues',
            sources=['src/_interpqueuesmodule.c',
                     *SOURCES_COMMON],
#            sources=['src/_interpqueuesmodule.c'],
#            extra_objects=EXTRA_OBJECTS,
            **EXT_COMMON,
        ),
        Extension(
            name='_interpchannels',
            sources=['src/_interpchannelsmodule.c',
                     *SOURCES_COMMON],
#            sources=['src/_interpchannelsmodule.c'],
#            extra_objects=EXTRA_OBJECTS,
            **EXT_COMMON,
        ),
    ],
)
