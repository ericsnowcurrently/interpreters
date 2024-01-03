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
#    '/Python/crossinterp.c',
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

#REQUIRED = [
#    *SRC_PY,
#    *SRC_C,
##    '/Include/internal/pycore_abstract.h',
#]
INCOMPATIBLE = set([
    '/Include/internal/pycore_crossinterp.h',
    '/Include/internal/pycore_lock.h',
])

PUBLIC_NOT_USED = set([
    '/Include/cpython/optimizer.h',
    '/Include/cpython/tracemalloc.h',
    '/Include/pystats.h',
])
PUBLIC_USED = {
    '/Include/object.h': ['/Include/pyatomic.h'],
    '/Include/internal/pycore_ceval.h': ['/Include/pyatomic.h'],
    '/Include/internal/pycore_interp.h': ['/Include/pyatomic.h'],
    '/Include/internal/pycore_lock.h': ['/Include/pyatomic.h'],
    '/Include/internal/pycore_object.h': ['/Include/pyatomic.h'],
    '/Include/internal/pycore_parking_lot.h': ['/Include/pyatomic.h'],
    '/Include/internal/pycore_runtime.h': ['/Include/pyatomic.h'],
}


def _resolve_directories(downdir=None, srcdir=None):
    if srcdir is None:
        srcdir = SRC_DIR
        if downdir is None:
            downdir = DOWNLOADS_DIR
    elif downdir is None:
        downdir = os.path.join(srcdir, 'orig')
    incldir = os.path.join(srcdir, 'Include')
    return downdir, srcdir, incldir


def _assert_valid_path(path, files):
    assert path.startswith('/'), repr(path)
    if __debug__:
        if path in files:
#            filestext = '{'+'\n'.join(f' {k}: {v}' for k, v in files.items())+'\n}'
            import pprint
            filestext = pprint.pformat(files, indent=2, width=200)
    assert path not in files, f'\n{path} in\n{filestext}'


def clear_all(downdir=None, srcdir=None):
    downdir, srcdir, incldir = _resolve_directories(downdir, srcdir)
    return _clear_all(downdir, srcdir, incldir)


def _clear_all(downdir, srcdir, incldir):
    srcglob = os.path.join(srcdir, '*.c')

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

    def download(path):
        _assert_valid_path(path, files)
        target = f'{downdir}/...'
        altpath = maybe_old.pop(path, None)
        _assert_valid_path(altpath, files)
        target, _, downpath, _, _ = repo.download(path, target, revision,
                                                  altpath=altpath,
                                                  makedirs=knowndirs)
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


def _list_public_headers(repo, revision=None):
    includes = _cpython.list_public_headers(repo, revision)
    other = _cpython.list_public_headers(repo, '3.12')
    new = set(includes) - set(other)
    return includes, new


def _iter_includes(filename, path, new, seen=None):
    for inclpath in _cpython.iter_includes(filename, seen):
        if inclpath == '/Include/Python.h':
            if seen:
                seen.pop(inclpath)
            continue
        if '/' not in inclpath.lstrip('/Include/') and inclpath not in new:
            if seen:
                seen.pop(inclpath)
            continue
        yield inclpath
    if path:
        for pubpath in PUBLIC_USED.get(path) or ():
            yield pubpath


def download_includes(repo, revision, cfiles, downdir=None, knowndirs=None):
    if knowndirs is None:
        knowndirs = set()
    repo = _cpython.resolve_repo(repo)
    downdir, *_ = _resolve_directories(downdir)
    return _download_includes(repo, revision, cfiles, downdir, knowdirs)


def _download_includes(repo, revision, cfiles, downdir, knowndirs):
    debug('analyzing public headers (Python.h)')
    public, new = _list_public_headers(repo, revision)
    if new:
        for path in sorted(new):
            status = ' (ignored)' if path in PUBLIC_NOT_USED else ''
            warn(f' public header not in 3.12: {path}{status}')
        debug('')

    files = {}

    def download(path, parent=None):
        _assert_valid_path(path, files)
        target = f'{downdir}/...'
        target, *_ = repo.download(path, target, revision, makedirs=knowndirs)

        copy = 'copy'
        if path in INCOMPATIBLE:
            copy = 'dummy'
        elif parent:
            _, parent_copy = files[parent]
            if parent_copy != 'copy':
                copy = 'ignore'
        files[path] = (target, copy)
        return target

    seen = {}

    debug('.h files (new):')
    for path in sorted(new):
        if path not in PUBLIC_NOT_USED:
            target = download(path)
            seen[path] = target

    debug('')
    debug('.h files (direct):')
    for filename in cfiles:
        for path in _iter_includes(filename, None, new, seen):
            assert path.startswith('/Include/internal/'), repr(path)
            target = download(path)
            seen[path] = target

    debug('')
    debug('.h files (indirect):')
    remainder = sorted(seen.items())
    while remainder:
#        import pprint; pprint.pprint(remainder, indent=2, width=200)
        path, filename = remainder.pop(0)
        assert filename, repr(path)
        for indirect in _iter_includes(filename, path, new):
            if indirect in seen:
                target, copy = files[indirect]
                if indirect in INCOMPATIBLE:
                    assert copy == 'dummy'
                else:
                    assert copy != 'dummy'
#                    _, parent_copy = files[path]
#                    if parent_copy == 'copy' and copy != 'copy':
#                         files[indirect] = (target, 'copy')
#                         remainder.append((indirect, target))
            else:
                target = download(indirect, parent=path)
#                print(f'      {path:30} -> {indirect}')
                seen[indirect] = target
                remainder.append((indirect, target))

    return files


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
            _utils.copy_file(downloaded, target)
        elif copy == 'dummy':
            assert path in INCOMPATIBLE, repr(path)
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
    def fix_crossinterp_h(text):
        # s/^struct _xid {/struct _xid_new {/
        text = text.replace('struct _xid {', 'struct _xid_new {')
        return text

    for filename in files:
        basename = os.path.basename(filename)
        if basename == 'pycore_crossinterp.h':
            fix = fix_crossinterp_h
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

    revision, branch = repo.resolve_revision(revision)

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
            debug(f' ./{reltarget:40}  <- ./{os.path.relpath(downloaded)}')
            copied.append(target)
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
