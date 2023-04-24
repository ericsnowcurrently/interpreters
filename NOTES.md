RunFailedError problem:
Go to:
cpython\Lib\test\support\interpreters.py
On line 8, change:
from _xxsubinterpreters import is_shareable
to
from _xxsubinterpreters import is_shareable, RunFailedError
