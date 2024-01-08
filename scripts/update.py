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
REPO = os.path.join(ROOT, 'build', 'cpython')

REPO_URL = 'https://github.com/python/cpython'

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

#PUBLIC_NOT_USED = set([
#    '/Include/cpython/optimizer.h',
#    '/Include/cpython/tracemalloc.h',
#    '/Include/pystats.h',
#])
#PUBLIC_USED = {
#    '/Include/object.h': ['/Include/pyatomic.h'],
#    '/Include/internal/pycore_ceval.h': ['/Include/pyatomic.h'],
#    '/Include/internal/pycore_interp.h': ['/Include/pyatomic.h'],
#    '/Include/internal/pycore_lock.h': ['/Include/pyatomic.h'],
#    '/Include/internal/pycore_object.h': ['/Include/pyatomic.h'],
#    '/Include/internal/pycore_parking_lot.h': ['/Include/pyatomic.h'],
#    '/Include/internal/pycore_runtime.h': ['/Include/pyatomic.h'],
#}

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


def clear_all(downdir=None, srcdir=None):
    downdir, srcdir, incldir = _resolve_directories(downdir, srcdir)
    return _clear_all(downdir, srcdir, incldir)


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


def download_source(repo, revision, downdir=None, knowndirs=None):
    if knowndirs is None:
        knowndirs = set()
    repo = _cpython.resolve_repo(repo)
    downdir, *_ = _resolve_directories(downdir)
    return _download_source(repo, revision, downdir, knowndirs)


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


#def _analyze_dependencies(filenames, download=None):
#    deps = {}
#    includes = []
#    for filename in filenames:
#        debug(f'+ ./{os.path.relpath(filename)}')
#        deps[filename] = []
#        with open(filename) as infile:
#            for dep in _cpython.analyze_dependencies(infile, filename,
#                                                     recurse=download):
#                deps[filename].append(dep)
#                if dep.kind == 'include-user':
#                    if dep.name not in includes:
#                        includes.append(dep.name)
#    return deps, includes


def _list_public_headers(repo, revision=None):
    includes = _cpython.list_public_headers(repo, revision)
    other = _cpython.list_public_headers(repo, '3.12')
    new = set(includes) - set(other)
    return includes, new


def download_includes(repo, revision, cfiles, downdir=None, knowndirs=None):
    if knowndirs is None:
        knowndirs = set()
    repo = _cpython.resolve_repo(repo)
    downdir, *_ = _resolve_directories(downdir)
    return _download_includes(repo, revision, cfiles, downdir, knowdirs)


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


#def _download_includes(repo, revision, cfiles, downdir, knowndirs):
#    debug('analyzing public headers (Python.h)')
#    public, new = _list_public_headers(repo, revision)
#    if new:
#        for path in sorted(new):
#            status = ' (ignored)' if path in PUBLIC_NOT_USED else ''
#            warn(f' public header not in 3.12: {path}{status}')
#        debug('')
#
#    files = {}
#
#    _download = _cpython.get_downloader(repo, revision, downdir,
#                                        files=files,
#                                        knowndirs=knowndirs)
#
#    def download(path, parent=None):
#        target = _download(path)
#        copy = 'copy'
#        if path in USE_SHIM:
#            copy = 'dummy'
#        elif parent:
#            _, parent_copy = files[parent]
#            if parent_copy != 'copy':
#                copy = 'ignore'
#        files[path] = (target, copy)
#        return target
#
#    seen = {}
#
#    debug('.h files (new):')
#    for path in sorted(new):
#        if path not in PUBLIC_NOT_USED:
#            target = download(path)
#            seen[path] = target
#
#    debug('')
#    debug('.h files (direct):')
#    for filename in cfiles:
#        for path in _cpython.iter_includes(filename, seen):
#            if path == '/Include/Python.h':
#                seen.pop(path)
#                continue
#            if '/' not in path.lstrip('/Include/') and path not in new:
#                seen.pop(path)
#                continue
#            assert path.startswith('/Include/internal/'), repr(path)
#            target = download(path)
#            seen[path] = target
#
#    # For now, don't download the indirect includes.
#    return files
#
#    debug('')
#    debug('.h files (indirect):')
#    remainder = sorted(seen.items())
#    while remainder:
##        import pprint; pprint.pprint(remainder, indent=2, width=200)
#        path, filename = remainder.pop(0)
#        assert filename, repr(path)
#        for indirect in _cpython.iter_includes(filename):
#            if indirect == '/Include/Python.h':
#                continue
#            if '/' not in indirect.lstrip('/Include/') and indirect not in new:
#                continue
#            if indirect in seen:
#                assert indirect in files, (indirect, filename)
#                target, copy = files[indirect]
#                if indirect in USE_SHIM:
#                    assert copy == 'dummy'
#                else:
#                    assert copy != 'dummy'
#            else:
#                target = download(indirect, parent=path)
#                seen[indirect] = target
#                remainder.append((indirect, target))
#
#        for indirect in PUBLIC_USED.get(path) or ():
#            if indirect in seen:
#                target, copy = files[indirect]
#                if indirect in USE_SHIM:
#                    assert copy == 'dummy'
#                else:
#                    assert copy != 'dummy'
#            else:
#                target = download(indirect, parent=path)
#                seen[indirect] = target
#                remainder.append((indirect, target))
#
#    return files


def _resolve_src_target(srcdir, incldir, path):
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


def apply_downloads(files, srcdir=None):
    _, srcdir, incldir = _resolve_directories(srcdir=srcdir)
    return _apply_downloads(files, srcdir, incldir)


def _apply_downloads(files, srcdir, incldir):
    for path, (downloaded, copy) in files.items():
        target = _resolve_src_target(srcdir, incldir, path)
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


def _fix_file(filename, fix):
    with open(filename, 'r') as infile:
        text = infile.read()
    with open(f'{filename}.orig', 'w') as orig:
        orig.write(text)
    text = fix(text)
    if text is None:
        raise Exception(f'"fix" func {fix} returned None, expected str')
    with open(filename, 'w') as outfile:
        outfile.write(text)


def fix_all(files):
    def fix__interpretersmodule_c(text):
        text = text.replace(
            '#define MODULE_NAME _xxsubinterpreters',
            '#define MODULE_NAME _interpreters',
        )
        text = text.replace(
            '_PyInterpreterState_LookUpID(',
            '_PyInterpreterState_LookUpIDFixed(',
        )
        return text

    def fix__interpchannelsmodule_c(text):
        text = text.replace(
            '#define MODULE_NAME _xxinterpchannels',
            '#define MODULE_NAME _interpchannels',
        )
        return text

    def fix__interpchannelsmodule_c(text):
        text = text.replace(
            '#define MODULE_NAME _xxinterpchannels',
            '#define MODULE_NAME _interpchannels',
        )
        return text

    def fix_crossinterp_c(text):
        text = text.replace(
            '_PyInterpreterState_LookUpID(',
            '_PyInterpreterState_LookUpIDFixed(',
        )
        return text

    def fix_pycore_crossinterp_h(text):
        # s/^struct _xid {/struct _xid_new {/
        text = text.replace('struct _xid {', 'struct _xid_new {')

        text = text.replace(
            'PyAPI_DATA(PyObject *) PyExc_InterpreterError;',
            textwrap.dedent('''\
            extern PyObject * _get_exctype(PyInterpreterState *, const char *);
            #define GET_EXC_TYPE(TYPE) \
                _get_exctype(PyInterpreterState_Get(), #TYPE)
            #define PyExc_InterpreterError \
                GET_EXC_TYPE(PyExc_InterpreterError)
            ''').rstrip(),
        )
        text = text.replace(
            'PyAPI_DATA(PyObject *) PyExc_InterpreterNotFoundError;',
            textwrap.dedent('''\
            #define PyExc_InterpreterNotFoundError \
                GET_EXC_TYPE(PyExc_InterpreterNotFoundError)

            PyInterpreterState * _PyInterpreterState_LookUpIDFixed(int64_t);
            ''').rstrip(),
        )
        return text

    def fix_typeobject_h(text):
        text = text.replace(
            'PyAPI_FUNC(PyObject *) _PyType_GetModuleName(PyTypeObject *);',
            ('#define _PyType_GetModuleName(cls) '
             '    PyObject_GetAttrString((PyObject *)cls, "__module__")'),
        )
        return text

    for filename in files:
        basename = os.path.basename(filename)
        if basename == '_interpreters.c':
            fix = fix__interpretersmodule_c
        elif basename == '_interpqueues.c':
            fix = fix__interpqueuesmodule_c
        elif basename == '_interpchannels.c':
            fix = fix__interpchannelsmodule_c
        elif basename == 'crossinterp.c':
            fix = fix_crossinterp_c
        elif basename == 'pycore_crossinterp.h':
            fix = fix_pycore_crossinterp_h
        elif basename == 'pycore_typeobject.h':
            fix = fix_typeobject_h
        else:
            continue
        debug(f'+ fixing ./{os.path.relpath(filename)}')
        _fix_file(filename, fix)


def write_metadata(repo, revision, files, branch=None, filename=None):
    if not repo:
        repo = REPO_URL
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

    revision, branch = repo.resolve_revision(revision, fallback=False)

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

#    debug('analyzing C dependencies')
#    deps, includes = _analyze_dependencies(cfiles)
#    debug()

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

    fix_all(copied)
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
