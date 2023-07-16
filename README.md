## Setup

To use this directory you must first build the development
version of CPython 3.12 on your machine by following the instructions
[here](https://devguide.python.org/getting-started/setup-building).
(This can seem intimidating but the instructions
are very clear and meticulous and you are likely to succeed on your
first try).

Once you install the CPython development version (make sure you make
any necessary path adjustments), when you run ``python --version`` 
you should see something like this:

```
Python 3.12.0a7+
```

### Windows Note

In Windows (and possibly other systems) you may need to get CPython 3.12
using the `git` command-line command:
```
git clone --branch 3.12 https://github.com/python/cpython
```

Also, when you follow the build instructions you end up creating a debug version
of Python and in Windows this will be given the special name `python_d.exe`. You'll
need to copy this to `python.exe` and configure your path so it will be found.

### Testing the Examples

After cloning this repo, use `pip` or `pipx` to (globally) install the `hatch`
build system.

Move to the root directory of the cloned repo and run:

```
hatch shell
```

This configures and enters a virtual environment. Now move to the
`examples` directory and you can run:

```
pytest
ruff check .
mypy .
```
