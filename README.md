This is the public pure-Python implementation of PEP 734,
along with several other backports.

For the implementation of the low-level modules, only on Python 3.12,
see https://pypi.org/project/interpreters-3-12/.

Nearly all development for this project is done in the upstream CPython repo.

----

This PyPI package installs two modules: `interpreters_backports` and
`interpreters_experimental`.  The "backports" module is a package
 that mirrors the backported structure of the 3.14 modules.  The
"experimental" module is a package containing modules that may
end up in the stdlib.

Note that only the `interpreters` and `interpreters.queues` modules
are part of PEP 734.

You can use the modules as fallbacks:

```py
try:
    import interpreters
except ModuleNotFoundError:
    from interpreters_backports import interpreters

try:
    import interpreters.queues
except ModuleNotFoundError:
    import interpreters_backports.interpreters.queues
    from interpreters_backports import interpreters

try:
    from interpreters import channels
except ModuleNotFoundError:
    from interpreters_experimental.interpreters import channels

try:
    from concurrent.futures import ThreadPoolExecutor
except ModuleNotFoundError:
    from interpreters_backports.concurrent.futures import ThreadPoolExecutor
```
