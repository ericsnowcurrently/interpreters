#! /usr/bin/env python3

import datetime
import logging
import os
import os.path
import sys
import textwrap

import _utils
import _cpython


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

    pkgroot = os.path.join(srcdir, 'interpreters')
    debug(f'clearing ./{os.path.relpath(pkgroot)}/*')
    _utils.clear_directory(pkgroot)

    debug(f'clearing ./{os.path.relpath(downdir)}/*')
    _utils.clear_directory(downdir)

    debug(f'clearing ./{os.path.relpath(incldir)}/*')
    _utils.clear_directory(incldir)

    debug(f'clearing ./{os.path.relpath(srcglob)}')
    _utils.rm_files(srcglob)


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


def _apply_downloads(files, srcdir, incldir):
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
            if os.path.exists(target):
                # /Modules/_interpreters_common.h
                # /Python/crossinterp_data_lookup.h
                downloaded = f'!{downloaded}'
            else:
                _utils.copy_file(downloaded, target)
        elif copy == 'dummy':
            assert path in USE_SHIM, repr(path)
            _utils.touch(target)
            downloaded = None
        elif copy == 'ignore':
            target = None
            downloaded = None
        else:
            raise NotImplementedError(copy)
        yield path, target, downloaded


class FileFixer:

    _FIXES = _utils.FileFixes()

    def register(filename, *, _fixes=_FIXES):
        deco = _fixes.register(filename)
        def decorator(func):
            func = deco(func)
            return staticmethod(func)
        return decorator

    @register('_interpretersmodule.c')
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

    @register('_interpqueuesmodule.c')
    def fix__interpqueuesmodule_c(text):
        text = text.replace(
            '#define MODULE_NAME _xxinterpqueues',
            '#define MODULE_NAME _interpqueues',
        )
        return text

    @register('_interpchannelsmodule.c')
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

    def run(self, *files, backup='.orig'):
        for filename in files:
            self._FIXES.apply_to_file(filename, backup)


def write_metadata(repo, revision, files, branch=None, filename=None):
    repo = _cpython.resolve_repo(repo)
    timestamp = datetime.datetime.utcnow()
    text = textwrap.dedent(f"""
        [DEFAULT]
        timestamp = {timestamp:%Y-%m-%d %H:%M:%S}

        [upstream]
        repo = {repo}
        revision = {revision}
        branch = {branch or ''}

        [files]
        downloaded = %s
        """)

    filelines = ['{']
    indent = ' ' * 4
    for relfile, (target, _) in sorted(files.items()):
        reltarget = os.path.relpath(target, ROOT)
        filelines.append(f'{indent}{relfile:45} -> {reltarget}')
    filelines.append(indent + '}')
    text = text % os.linesep.join(filelines)

    if not filename:
        filename = METADATA_FILE
    with open(filename, 'w', encoding='utf-8') as outfile:
        outfile.write(text)
    return filename


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
    section('copying downloaded files')

    copied = []
    ignored = []
    for path, target, downloaded in _apply_downloads(files, srcdir, incldir):
        if target is None:
            ignored.append(path)
            continue
        reltarget = os.path.relpath(target)
        if downloaded:
            down_prefix = ''
            if downloaded.startswith('!'):
                down_prefix = '(ignored) '
                downloaded = downloaded[1:]
            else:
                copied.append(target)
            debug(f' ./{reltarget:40}  <- {down_prefix}./{os.path.relpath(downloaded)}')
        else:
            debug(f' ./{reltarget:40}  <- dummy')
    if ignored:
        debug()
        debug('ignored:')
        for path in ignored:
            debug(f'  {path}')

    ###############
    section('applying fixes')

    fixer.run(*copied)
    debug('...done')

    ###############
    section('writing metadata')

    write_metadata(repo, revision, files, branch)
    debug('...done')

    ###############
    debug()


if __name__ == '__main__':
    verbosity = VERBOSITY
    revision = parse_args()
    init_logger(logger, verbosity)
    main(revision)
