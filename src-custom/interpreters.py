import interpreters_backport
interpreters_backport._install_from_placeholder(__name__)
assert (mod := __import__('sys').modules[__name__]).__file__ != __file__, (mod, __file__)
