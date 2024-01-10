#! /usr/bin/env python3

import logging
import os
import os.path
import sys
import textwrap

import _utils
import _cpython
import _metadata


VERBOSITY = 4  # logging.DEBUG

logger = logging.getLogger()
debug = (lambda msg='': print(msg))
log = (lambda msg='': print(msg))
warn = (lambda msg: print(msg, file=sys.stderr))
err = (lambda msg: print(msg, file=sys.stderr))


def init_logger(logger, verbosity=VERBOSITY):
    _utils.init_logger(logger, verbosity)
    global debug, log, warn, err
    debug = (lambda msg='': logger.debug(msg))
    log = (lambda msg='': logger.info(msg))
    warn = (lambda msg='': logger.warning(msg))
    err = (lambda msg='': logger.error(msg))


ROOT = os.path.abspath(
        os.path.dirname(
            os.path.dirname(__file__)))
SRC_DIR = os.path.join(ROOT, 'src')
DOWNLOADS_DIR = os.path.join(ROOT, 'src/orig')
METADATA_FILE = os.path.join(ROOT, 'METADATA')

SRC_PY = [
    '/Lib/interpreters/__init__.py',
    '/Lib/interpreters/queues.py',
    '/Lib/interpreters/channels.py',
]
SRC_C = [
    '/Modules/_interpretersmodule.c',
    '/Modules/_interpqueuesmodule.c',
    '/Modules/_interpchannelsmodule.c',
#    '/Modules/_interpreters_common.h',

    '/Python/crossinterp.c',
#    '/Python/crossinterp_data_lookup.h',
#    '/Python/crossinterp_exceptions.h',

    '/Python/thread.c',
    '/Objects/abstract.c',
]
# Before PEP 734 is accepted and the impl. merged:
PRE_PEP_734 = {
    '/Lib/interpreters/__init__.py': '/Lib/test/support/interpreters/__init__.py',
    '/Lib/interpreters/queues.py': '/Lib/test/support/interpreters/queues.py',
    '/Lib/interpreters/channels.py': '/Lib/test/support/interpreters/channels.py',
    '/Modules/_interpretersmodule.c': '/Modules/_xxsubinterpretersmodule.c',
    '/Modules/_interpqueuesmodule.c': '/Modules/_xxinterpqueuesmodule.c',
    '/Modules/_interpchannelsmodule.c': '/Modules/_xxinterpchannelsmodule.c',
}

INCLUDES = [
    '/Include/internal/pycore_abstract.h',
    '/Include/internal/pycore_crossinterp.h',
    '/Include/internal/pycore_interp.h',
    '/Include/internal/pycore_initconfig.h',
    '/Include/internal/pycore_long.h',
    '/Include/internal/pycore_modsupport.h',
    '/Include/internal/pycore_pybuffer.h',
    '/Include/internal/pycore_pyerrors.h',
    '/Include/internal/pycore_pystate.h',
    '/Include/internal/pycore_ceval.h',
    '/Include/internal/pycore_namespace.h',
    '/Include/internal/pycore_typeobject.h',
    '/Include/internal/pycore_weakref.h',
    '/Include/internal/pycore_pythread.h',
]
INCLUDES_INDIRECT = [
    '/Include/internal/pycore_lock.h',
    '/Include/internal/pycore_moduleobject.h',
    '/Include/internal/pycore_critical_section.h',
    '/Include/internal/pycore_object.h',
]

USE_SHIM = set([
    # incompatible, new, excessive baggage, etc.

    '/Include/internal/pycore_abstract.h',
#    '/Include/internal/pycore_crossinterp.h',
    '/Include/internal/pycore_interp.h',
    '/Include/internal/pycore_initconfig.h',
    '/Include/internal/pycore_long.h',
    '/Include/internal/pycore_modsupport.h',
    '/Include/internal/pycore_pybuffer.h',
    '/Include/internal/pycore_pyerrors.h',
    '/Include/internal/pycore_pystate.h',

    '/Include/internal/pycore_ceval.h',
    '/Include/internal/pycore_namespace.h',
#    '/Include/internal/pycore_typeobject.h',
#    '/Include/internal/pycore_weakref.h',
    '/Include/internal/pycore_pythread.h',

    '/Include/internal/pycore_lock.h',
#    '/Include/internal/pycore_moduleobject.h',
    '/Include/internal/pycore_critical_section.h',
    '/Include/internal/pycore_object.h',
])
PENDING_UPSTREAM = set([
    '/Modules/_interpreters_common.h',
    '/Python/crossinterp_data_lookup.h',
    '/Python/crossinterp_exceptions.h',
])
INTERNAL = set([
    'shim-compatible-includes.h',
    'shim-new-stuff.h',
])


def _resolve_directories(downdir=None, srcdir=None):
    if srcdir is None:
        srcdir = SRC_DIR
        if downdir is None:
            downdir = DOWNLOADS_DIR
    elif downdir is None:
        downdir = os.path.join(srcdir, 'orig')
    incldir = os.path.join(srcdir, 'Include')
    return downdir, srcdir, incldir


def _clear_all(downdir, srcdir, incldir):
    srcglob = os.path.join(srcdir, '*.c')

#    pkgroot = os.path.join(srcdir, 'interpreters')
#    debug(f'clearing ./{os.path.relpath(pkgroot)}/*')
#    _utils.clear_directory(pkgroot)

    debug(f'clearing ./{os.path.relpath(downdir)}/*')
    _utils.clear_directory(downdir)

#    debug(f'clearing ./{os.path.relpath(incldir)}/*')
#    _utils.clear_directory(incldir)

#    debug(f'clearing ./{os.path.relpath(srcglob)}')
#    _utils.rm_files(srcglob)

    debug(f'clearing ./{os.path.relpath(srcdir)}/**/*.orig')
    _utils.rm_files(os.path.join(srcdir, '**', '*.orig'))


def _download_source(repo, revision, downdir, knowndirs):
    files = {}
    maybe_old = dict(PRE_PEP_734)
    old = []

    _download, maybe_old = _cpython.get_alts_downloader(
             repo, revision, downdir, PRE_PEP_734,
             files=files,
             knowndirs=knowndirs)

    def download(path):
        target, downpath, altpath = _download(path)
        assert files[path] == target, (files[path], target)
        files[path] = (target, 'copy')
        if downpath == altpath:
            old.append(path)

    debug('.py files:')
    for path in SRC_PY:
        download(path)

    debug('')
    debug('.c files:')
    for path in SRC_C:
        download(path)

    assert not maybe_old or maybe_old == PRE_PEP_734, (maybe_old, old)
    assert not old or sorted(old) == sorted(PRE_PEP_734), (maybe_old, sorted(old), sorted(PRE_PEP_734))

    return files


def _download_includes(repo, revision, cfiles, downdir, knowndirs):
    files = {}

    _download = _cpython.get_downloader(repo, revision, downdir,
                                        files=files,
                                        knowndirs=knowndirs)

    def download(path, parent=None):
        target = _download(path)
        copy = 'copy'
        if path in USE_SHIM:
            copy = 'dummy'
        elif parent:
            _, parent_copy = files[parent]
            if parent_copy != 'copy':
                copy = 'ignore'
        files[path] = (target, copy)
        return target

    seen = {}

    debug('.h files (direct):')
    for path in INCLUDES:
        assert path.startswith('/Include/'), repr(path)
        target = download(path)
        seen[path] = target

    debug()
    debug('.h files (indirect):')
    for path in INCLUDES_INDIRECT:
        assert path.startswith('/Include/'), repr(path)
        target = download(path)
        seen[path] = target

    return files


def _resolve_applied_downloads(files, srcdir, incldir):
    def resolve_src_target(path):
        assert path.startswith('/'), repr(path)
        basename = path.split('/')[-1]
        if path.endswith('.py'):
            assert '/interpreters/' in path, repr(path)
            reltarget = f'interpreters/{basename}'
        elif path.endswith('.c'):
            reltarget = basename
        elif path.startswith('/Include/'):
            return os.path.join(incldir, basename)
        else:
            raise NotImplementedError(repr(path))
        return os.path.join(srcdir, reltarget)

    for path, (downloaded, copy) in files.items():
        target = resolve_src_target(path)
        if copy == 'copy':
            pass
        elif copy == 'dummy':
            assert path in USE_SHIM, repr(path)
            downloaded = None
        elif copy == 'ignore':
            target = None
            downloaded = None
        else:
            raise NotImplementedError(copy)
        yield path, target, downloaded


def apply_download(target, downloaded, fixer, backups):
    if os.path.exists(target):
        with open(target) as infile:
            existing = infile.read()
    else:
        existing = None

    reltarget = os.path.relpath(target)
    if downloaded is None:
        if existing is not None:
            if not existing:
                debug(f' ./{reltarget:40}  <- dummy')
            else:
                debug(f' ./{reltarget:40}  (cleared)  <- dummy')
                os.unlink(target)
                _utils.touch(target)
        else:
            debug(f' ./{reltarget:40}  (new)  <- dummy')
            _utils.touch(target)
        return

    if existing is None:
        debug(f' ./{reltarget:40}  (new)  <- ./{os.path.relpath(downloaded)}')
        apply = fixer.match(downloaded)
        if apply is None:
            _utils.copy_file(downloaded, target)
            text = None
        else:
            debug(f'  + fixing ./{reltarget}')
            with open(downloaded) as infile:
                text = infile.read()
            text = apply(text)
    else:
        debug(f' ./{reltarget:40}  <- ./{os.path.relpath(downloaded)}')
        with open(downloaded) as infile:
            text = infile.read()
        apply = fixer.match(downloaded)
        if apply is not None:
            debug(f'  + fixing ./{reltarget}')
            text = apply(text)
        if text != existing:
            debug(f'  + backing up ./{reltarget}')
            with open(f'{target}.orig', 'w') as orig:
                orig.write(existing)
            backups.append((reltarget, f'{reltarget}.orig'))
    if text is not None:
        with open(target, 'w') as outfile:
            outfile.write(text)


class FileFixer:

    _FIXES = {}

    def register(basename, *alts, _fixes=_FIXES):
        def decorator(func):
            assert basename not in _fixes, (basename, _fixes)
            _fixes[basename] = func
            for alt in alts:
                assert alt not in _fixes, (alt, _fixes)
                _fixes[alt] = func
            return staticmethod(func)
        return decorator

    @register('_interpretersmodule.c', '_xxsubinterpretersmodule.c')
    def fix__interpretersmodule_c(text):
        text = text.replace(
            '#define MODULE_NAME _xxsubinterpreters',
            '#define MODULE_NAME _interpreters',
        )
        text = text.replace(
            '_PyInterpreterState_LookUpID(',
            '_PyInterpreterState_LookUpIDFixed(',
        )

        before, _, after = text.partition('module_clear(PyObject *mod)')
        before += 'module_clear(PyObject *mod)'
        text = before + after.replace(
            'module_state *state = get_module_state(mod);',
            textwrap.dedent('''\
            module_state *state = get_module_state(mod);

            PyInterpreterState *interp = PyInterpreterState_Get();
            PyStatus status = _PyXI_InitTypes(interp);
            if (PyStatus_Exception(status)) {
                _PyErr_SetFromPyStatus(status);
                return -1;
            }
            '''[4:]).rstrip(),
        )

        text = text.replace(
            'clear_module_state(state);',
            textwrap.dedent('''\
            clear_module_state(state);
            _PyXI_FiniTypes(PyInterpreterState_Get());
            '''[4:]).rstrip(),
            1,  # count
        )
        return text

    @register('_interpqueuesmodule.c', '_xxinterpqueuesmodule.c')
    def fix__interpqueuesmodule_c(text):
        text = text.replace(
            '#define MODULE_NAME _xxinterpqueues',
            '#define MODULE_NAME _interpqueues',
        )
        return text

    @register('_interpchannelsmodule.c', '_xxinterpchannelsmodule.c')
    def fix__interpchannelsmodule_c(text):
        text = text.replace(
            '#define MODULE_NAME _xxinterpchannels',
            '#define MODULE_NAME _interpchannels',
        )
        return text

    @register('crossinterp.c')
    def fix_crossinterp_c(text):
        text = text.replace(
            '_PyInterpreterState_LookUpID(',
            '_PyInterpreterState_LookUpIDFixed(',
        )
        return text

    @register('pycore_crossinterp.h')
    def fix_pycore_crossinterp_h(text):
        # s/^struct _xid {/struct _xid_new {/
        text = text.replace('struct _xid {', 'struct _xid_new {')

        text = text.replace(
            'PyAPI_DATA(PyObject *) PyExc_InterpreterError;',
            textwrap.dedent('''\
            extern PyObject * _get_exctype(PyInterpreterState *, const char *);
            #define GET_EXC_TYPE(TYPE) \\
                _get_exctype(PyInterpreterState_Get(), #TYPE)
            #define PyExc_InterpreterError \\
                GET_EXC_TYPE(PyExc_InterpreterError)
            ''').rstrip(),
        )
        text = text.replace(
            'PyAPI_DATA(PyObject *) PyExc_InterpreterNotFoundError;',
            textwrap.dedent('''\
            #define PyExc_InterpreterNotFoundError \\
                GET_EXC_TYPE(PyExc_InterpreterNotFoundError)

            PyInterpreterState * _PyInterpreterState_LookUpIDFixed(int64_t);
            ''').rstrip(),
        )
        return text

    @register('pycore_typeobject.h')
    def fix_pycore_typeobject_h(text):
        text = text.replace(
            'PyAPI_FUNC(PyObject *) _PyType_GetModuleName(PyTypeObject *);',
            textwrap.dedent('''\
            #define _PyType_GetModuleName(cls) \\
                PyObject_GetAttrString((PyObject *)cls, "__module__")
            ''').rstrip(),
        )
        return text

    del register

    def match(self, filename):
        basename = os.path.basename(filename)
        return self._FIXES.get(basename)


##################################
# the script

def parse_args(argv=sys.argv[1:], prog=sys.argv[0]):
    import argparse
    parser = argparse.ArgumentParser(prog=prog)

    parser.add_argument('revision', nargs='?')

    args = parser.parse_args()
    ns = vars(args)

    return args.revision


def main(revision=None, repo=None):
    if not revision:
        revision = 'main'
    repo = _cpython.resolve_repo(repo)

    revision, branch = repo.resolve_revision(revision)

    fixer = FileFixer()
    downdir, srcdir, incldir = _resolve_directories()
    knowndirs = set()
    files = {}

    def section(title):
        assert title
        debug()
        debug('####################')
        log(title)
        debug('####################')
        debug()

    ###############
    section('removing old files')

    _clear_all(downdir, srcdir, incldir)

    ###############
    section('downloading')

    files = _download_source(repo, revision, downdir, knowndirs)
    cfiles = [f for f, _ in files.values() if f.endswith('.c')]
    debug()

    inclfiles = _download_includes(repo, revision, cfiles, downdir, knowndirs)
    files.update(inclfiles)

    ###############
    section('applying downloads')

    ignored = []
    backups = []
    expected = set()
    for path, target, downloaded in _resolve_applied_downloads(files, srcdir, incldir):
        if target is None:
            ignored.append(path)
            continue
        expected.add(target)
        apply_download(target, downloaded, fixer, backups)

    if backups:
        debug()
        debug('backed up:')
        for reltarget, relbackup in backups:
            debug(f'  ./{reltarget:40}  ->  ./{relbackup}')

    if ignored:
        debug()
        debug('ignored:')
        for path in ignored:
            debug(f'  {path}')

    extra = {f'{srcdir}/{n}' for n in os.listdir(srcdir) if n.endswith(('.c', '.h'))}
    pkgdir = os.path.join(srcdir, 'interpreters')
    extra = {f'{pkgdir}/{n}' for n in os.listdir(pkgdir) if n.endswith('.py')}
    extra.update(f'{incldir}/{n}' for n in os.listdir(incldir) if n.endswith('.h'))
    extra -= set(expected)
    extra -= PENDING_UPSTREAM
    extra -= INTERNAL
    if extra:
        debug()
        debug('removed (extra):')
        for filename in sorted(extra):
            debug(f'  {os.path.relpath(filename)}')
            os.unlink(filename)

    ###############
    section('writing metadata')

    _metadata.write(repo, revision, files, branch)
    debug('...done')

    ###############
    debug()


if __name__ == '__main__':
    verbosity = VERBOSITY
    revision = parse_args()
    init_logger(logger, verbosity)
    main(revision)
