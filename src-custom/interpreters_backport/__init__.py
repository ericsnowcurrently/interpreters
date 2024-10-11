import sys

try:
    __import__('_interpreters')
except ModuleNotFoundError:
    # It must be an out-of-date Python.  Be nice and help out.
    sys.modules['_interpreters'] = __import__('_xxsubinterpreters')
    sys.modules['_interpqueues'] = __import__('_xxinterpqueues')
    sys.modules['_interpchannels'] = __import__('_xxinterpchannels')

from . import interpreters
__import__(f'{__name__}.interpreters.queues')
__import__(f'{__name__}.interpreters.channels')


MODULES = {
    'interpreters': interpreters,
    'interpreters.queues': interpreters.queues,
    'interpreters.channels': interpreters.channels,
    'interpreters._crossinterp': interpreters._crossinterp,
}


def install(*, force=True):
    """Install the relevant stdlib backport modules.

    PEP 734:
    * interpreters
    * interpreters.queues

    experimental:
    * interpreters.channels
    """
    # XXX Adjust for the current Python version.
    _Installer.install_module('interpreters', force)
    _Installer.install_module('interpreters._crossinterp', force)
    _Installer.install_module('interpreters.queues', force)
    # XXX Move this to the experimental package.
    _Installer.install_module('interpreters.channels', force)


def uninstall():
    raise NotImplementedError


def install_pep_734(*, force=True):
    _Installer.install_module('interpreters', force)
    _Installer.install_module('interpreters._crossinterp', force)
    _Installer.install_module('interpreters.queues', force)


def install_experimental(*, force=True):
    install_pep_734(force=force)
    _Installer.install_module('interpreters.channels', force)


def _install_from_placeholder(modname):
    force = True
    if modname == 'interpreters':
        del sys.modules[modname]
        _Installer.install_module('interpreters', force)
        _Installer.install_module('interpreters._crossinterp', force)
        _Installer.install_module('interpreters.queues', force)
        _Installer.install_module('interpreters.channels', force)
    else:
        raise NotImplementedError(modname)


class _Installer:

    @classmethod
    def install_module(cls, modname, force=True):
        try:
            owned = MODULES[modname]
        except KeyError:
            raise ValueError(f'unsupported module {modname}')
        assert owned.__name__ == f'{__name__}.{modname}', owned
        assert (_owned := sys.modules.get(owned.__name__)) is owned, _owned

        missing = object()
        current = sys.modules.get(modname, missing)
        if current is None:
            # It has been disabled, so let the import machinery raise.
            # XXX Allow if "force" is true?
            __import__(modname)
        elif current is not missing:
            if current is owned:
                # Already installed.
                return
            if not force:
                raise RuntimeError(f'module {modname} already imported')

        if not force:
            stdlib = cls.find_stdlib_module(modname)
            if stdlib is not None:
                raise RuntimeError(f'{modname} is already in the stdlib')

        sys.modules[modname] = owned

    @classmethod
    def find_stdlib_module(cls, modname):
        stdlibdir = cls.get_stdlib_dir()
        for finder in cls.get_finders():
            spec = finder.find_spec(modname, [stdlibdir])
            if spec is not None:
                return spec
        else:
            # Fall back to a normal import, focused on the stdlib dir.
            import importlib.util
            class FakePackage: __path__ = [stdlibdir]
            return importlib.util.find_spec(modname, FakePackage)

    @classmethod
    def get_finders(cls):
        finders = []
        fallback = None
        finder = sys.meta_path[-1]
        if getattr(finder, '__name__', None) != 'PathFinder':
            for finder in sys.meta_path[::-1]:
                if getattr(finder, '__name__', None) == 'PathFinder':
                    finders.append(finder)
                    break
            else:
                # XXX Fall back to a naive solution?
                raise NotImplementedError
                fallback = ...
        import importlib.machinery
        finders.append(importlib.machinery.FrozenImporter)
        if fallback:
            finders.append(fallback)
        return finders

    @classmethod
    def get_stdlib_dir(cls):
        try:
            return cls.STDLIB_DIR
        except AttributeError:
            try:
                cls.STDLIB_DIR = sys._stdlib_dir
            except AttributeError:
                import os
                import os.path
                cls.STDLIB_DIR = os.path.dirname(os.__file__)
            return cls.STDLIB_DIR
