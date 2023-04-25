## Setup

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
