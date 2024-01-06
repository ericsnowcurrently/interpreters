import os.path

from setuptools import Extension, setup


EXT_COMMON = dict(
    language='c',
    include_dirs=[
        'src/Include',
        'src/Include/internal',
    ],
    define_macros=[
        ('Py_BUILD_CORE', '1'),
    ],
    extra_compile_args=[
        '-include', 'src/shim-compatible-includes.h',
        '-include', 'src/shim-new-stuff.h',
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
            name='_queues',
            sources=['src/_interpqueuesmodule.c',
                     *SOURCES_COMMON],
            **EXT_COMMON,
        ),
        Extension(
            name='_channels',
            sources=['src/_interpchannelsmodule.c',
                     'src/thread.c',
                     *SOURCES_COMMON],
            **EXT_COMMON,
        ),
    ],
)
