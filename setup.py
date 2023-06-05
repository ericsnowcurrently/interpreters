from setuptools import Extension, setup


setup(
    ext_modules=[
        Extension(
            name='_interpreters',
            sources=['src/_interpreters.c'],
        ),
        Extension(
            name='_channels',
            sources=['src/_channels.c'],
        ),
    ]
)
