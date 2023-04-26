# Demonstrate this from PEP 554:
# Note that the target interpreter's state is never reset, neither
# before "run()" executes the code nor after.  Thus the
# interpreter state is preserved between calls to "run()".
# This includes "sys.modules", the "builtins" module, and the
# internal state of C extension modules.
