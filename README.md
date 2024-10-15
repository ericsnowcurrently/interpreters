This is the public implementation of PEP 734.

Nearly all development for this project is done in the upstream CPython repo.

----

This PyPI package installs one module: `interpreters_backports`.
The module is a package that mirrors the backported structure of
the 3.14 modules.

You can use the module as a fallback:

```py
try:
    import interpreters
except ModuleNotFoundError:
    from interpreters_backports import interpreters
```
