#! /usr/bin/env python3

import datetime
import os
import os.path
import sys
import textwrap

import _git
import _utils


ROOT = os.path.abspath(os.path.dirname(__file__))
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
]
INCLUDES_INDIRECT = [
    '/Include/internal/pycore_lock.h',
    '/Include/internal/pycore_time.h',
    '/Include/cpython/pyatomic.h',
    '/Include/cpython/pyatomic_gcc.h',
    '/Include/cpython/pyatomic_msc.h',
    '/Include/cpython/pyatomic_std.h',
    '/Include/internal/pycore_ceval.h',
    '/Include/internal/pycore_namespace.h',
    '/Include/internal/pycore_typeobject.h',
    '/Include/internal/pycore_weakref.h',
    '/Include/internal/pycore_moduleobject.h',
    '/Include/internal/pycore_critical_section.h',
    '/Include/internal/pycore_ast_state.h',
    '/Include/internal/pycore_atexit.h',
    '/Include/internal/pycore_ceval_state.h',
]
SRC_C = [
    '/Modules/_interpretersmodule.c',
    '/Modules/_interpqueuesmodule.c',
    '/Modules/_interpchannelsmodule.c',
    '/Python/crossinterp.c',
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
DUMMIES = set([
    # direct
    '/Include/internal/pycore_abstract.h',
    '/Include/internal/pycore_crossinterp.h',
    '/Include/internal/pycore_interp.h',
    '/Include/internal/pycore_initconfig.h',
    '/Include/internal/pycore_long.h',
    '/Include/internal/pycore_modsupport.h',
    '/Include/internal/pycore_pybuffer.h',
    '/Include/internal/pycore_pyerrors.h',
    '/Include/internal/pycore_pystate.h',
    # indirect
    '/Include/internal/pycore_lock.h',
    '/Include/internal/pycore_time.h',
    '/Include/cpython/pyatomic.h',
    '/Include/cpython/pyatomic_gcc.h',
    '/Include/cpython/pyatomic_msc.h',
    '/Include/cpython/pyatomic_std.h',
    '/Include/internal/pycore_ceval.h',
    '/Include/internal/pycore_namespace.h',
    '/Include/internal/pycore_typeobject.h',
    '/Include/internal/pycore_weakref.h',
    '/Include/internal/pycore_moduleobject.h',
    '/Include/internal/pycore_critical_section.h',
    '/Include/internal/pycore_ast_state.h',
    '/Include/internal/pycore_atexit.h',
    '/Include/internal/pycore_ceval_state.h',
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
    _utils.clear_directory(downdir)
    _utils.clear_directory(incldir)
    _utils.rm_files(os.path.join(srcdir, '*.c'))


def download_all(repo, revision, downdir=None):
    repo = _git.resolve_repo(repo)
    downdir, *_ = _resolve_directories(downdir)

    files = {}
    knownfiles = set()
    maybe_old = dict(PRE_PEP_734)
    old = []

    def download(path):
        assert path.startswith('/'), repr(path)
        assert path not in files, files
        target = f'{downdir}/...'
        altpath = maybe_old.pop(path, None)
        assert altpath not in files, files
        target, _, downpath, _, _ = repo.download(path, target, revision,
                                                  altpath=altpath,
                                                  makedirs=knownfiles)
        files[path] = target
        if downpath == altpath:
            old.append(path)

    for path in SRC_PY:
        download(path)

    print()
    for path in INCLUDES:
        download(path)

    print()
    for path in INCLUDES_INDIRECT:
        download(path)

    print()
    for path in SRC_C:
        download(path)

    assert not maybe_old or maybe_old == PRE_PEP_734, (maybe_old, old)
    assert not old or sorted(old) == sorted(PRE_PEP_734), (maybe_old, sorted(old), sorted(PRE_PEP_734))

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

    copied = []
    for path, downloaded in files.items():
        target = _resolve_src_target(srcdir, incldir, path)
        reltarget = os.path.relpath(target)
        if path in DUMMIES:
            print(f' ./{reltarget:40}  <- dummy')
            _utils.touch(target)
        else:
            print(f' ./{reltarget:40}  <- ./{os.path.relpath(downloaded)}')
            _utils.copy_file(downloaded, target)
            copied.append(target)
    return copied


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
        print(f'+ fixing ./{os.path.relpath(filename)}')
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
    for relfile, target in sorted(files.items()):
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
    if repo is None:
        repo = REPO_URL
    repo = _git.resolve_repo(repo)

    revision, branch = repo.resolve_revision(revision)

    print('####################')
    print('downloading...')
    clear_all()
    files = download_all(repo, revision)
    print('...done')

    print()
    print('####################')
    print('applying fixes...')
    copied = apply_downloads(files)
    fix_all(copied)
    print('...done')

    print()
    print('####################')
    print('writing metadata...')
    write_metadata(repo, revision, files, branch)
    print('...done')


if __name__ == '__main__':
    revision = parse_args()
    main(revision)
