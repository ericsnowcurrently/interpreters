## Setup

To use this directory you must first build the development
version of CPython on your machine by following the instructions
[here](https://devguide.python.org/getting-started/setup-building). (This can seem intimidating but the instructions
are very clear and meticulous and you are likely to succeed on your
first try).

Once you install the CPython development version (make sure you make
any necessary path adjustments), when you run ``python --version`` 
you should see something like this:

```
Python 3.12.0a7+
```

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
