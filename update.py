#! /usr/bin/env python3

import datetime
import json
import os
import os.path
import re
import sys
import textwrap
from urllib.request import urlretrieve, urlopen
from urllib.error import HTTPError


ROOT = os.path.abspath(os.path.dirname(__file__))
METADATA_FILE = os.path.join(ROOT, 'METADATA')
SRC_DIR = os.path.join(ROOT, 'src')

REPO = 'https://github.com/python/cpython'
GH_DOWNLOAD = 'https://raw.github.com/{ORG}/{REPO}/{REVISION}/{PATH}'
GH_COMMIT = 'https://api.github.com/repos/{ORG}/{REPO}/commits/{REF}'
#GH_BRANCH = 'https://api.github.com/repos/{ORG}/{REPO}/branches/{BRANCH}'

SRC_PY = [
    '/Lib/test/support/interpreters/__init__.py',
    '/Lib/test/support/interpreters/queues.py',
    '/Lib/test/support/interpreters/channels.py',
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
INCLUDES_DUMMY = set([
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
SRC_C = [
    '/Modules/_interpretersmodule.c',
    '/Modules/_interpqueuesmodule.c',
    '/Modules/_interpchannelsmodule.c',
    '/Python/crossinterp.c',
]
# Before PEP 734 is accepted and the impl. merged:
SRC_C_OLD = {
    '/Modules/_interpretersmodule.c': '/Modules/_xxsubinterpretersmodule.c',
    '/Modules/_interpqueuesmodule.c': '/Modules/_xxinterpqueuesmodule.c',
    '/Modules/_interpchannelsmodule.c': '/Modules/_xxinterpchannelsmodule.c',
}


def write_metadata(repo, revision, files, branch=None, filename=None):
    if not repo:
        repo = REPO
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


def resolve_revision(repo, revision):
    m = re.match('^https://github.com/(\w+)/(\w+)', repo)
    if not m:
        raise ValueError(f'unsupported repo {repo!r}')
    org, repo_ = m.groups()

    # https://docs.github.com/en/rest/commits/commits?apiVersion=2022-11-28#get-a-commit
    url = GH_COMMIT.format(ORG=org, REPO=repo_, REF=revision)
    with urlopen(url) as resp:
        data = json.load(resp)
    rev = data['sha']
    assert rev
    branch = None if rev.startswith(revision) else revision
    return rev, branch


def _resolve_download_url(org, repo, revision, path):
    assert path.startswith('/'), repr(path)
    if path.startswith('/Include/') and path in INCLUDES_DUMMY:
        return f'<{path}>'
    return GH_DOWNLOAD.format(ORG=org, REPO=repo, REVISION=revision,
                              PATH=path.lstrip('/'))


def _resolve_download_target(srcdir, path):
    assert path.startswith('/'), repr(path)
    if path.endswith('.py'):
        assert '/interpreters/' in path, repr(path)
        basename = path.split('/')[-1]
        reltarget = f'interpreters/{basename}'
    elif path.endswith('.c'):
        reltarget = path.split('/')[-1]
    elif path.startswith('/Include/'):
        reltarget = path[1:]
    else:
        raise NotImplementedError(repr(path))
    return os.path.join(srcdir, reltarget)


def _download(url, target, *, _knowndirs=set()):
    print(' + {:60}  <- {}'.format(target, url))

    targetdir = os.path.dirname(target)
    if targetdir not in _knowndirs:
        os.makedirs(targetdir, exist_ok=True)
        _knowndirs.add(targetdir)

    if url.startswith('<'):
        assert url.endswith('>'), repr(url)
        with open(target, 'w'):
            pass
    else:
        urlretrieve(url, target)


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


def clear_all(srcdir=None):
    if srcdir is None:
        srcdir = SRC_DIR

    for path in SRC_PY + INCLUDES + SRC_C:
        target = _resolve_download_target(srcdir, path)
        try:
            os.unlink(target)
        except FileNotFoundError:
            pass
        target += '.orig'
        try:
            os.unlink(target)
        except FileNotFoundError:
            pass


def download_all(repo, revision, srcdir=None):
    if srcdir is None:
        srcdir = SRC_DIR

    m = re.match('^https://github.com/(\w+)/(\w+)', repo)
    if not m:
        raise ValueError(f'unsupported repo {repo!r}')
    org, repo_ = m.groups()

    files = {}

    for path in SRC_PY:
        assert path not in files, files
        url = _resolve_download_url(org, repo_, revision, path)
        target = _resolve_download_target(srcdir, path)
        _download(url, target)
        files[path] = target

    print()
    dummies = []
    for path in INCLUDES:
        assert path not in files, files
        url = _resolve_download_url(org, repo_, revision, path)
        target = _resolve_download_target(srcdir, path)
        if url.startswith('<'):
            dummies.append((url, target))
        else:
            _download(url, target)
            files[path] = target

    print()
    for path in INCLUDES_INDIRECT:
        assert path not in files, files
        url = _resolve_download_url(org, repo_, revision, path)
        target = _resolve_download_target(srcdir, path)
        if url.startswith('<'):
            dummies.append((url, target))
        else:
            _download(url, target)
            files[path] = target

    print()
    for url, target in dummies:
        _download(url, target)
        files[path] = target

    print()
    maybe_old = dict(SRC_C_OLD)
    old = []
    for path in SRC_C:
        assert path not in files, files
        url = _resolve_download_url(org, repo_, revision, path)
        target = _resolve_download_target(srcdir, path)
        if path in maybe_old:
            oldpath = maybe_old.pop(path)
            try:
                _download(url, target)
            except HTTPError:
                print('-- "new" file not found, falling back to old file --')
                old.append(path)
                path = oldpath
                assert path not in files, files
                url = _resolve_download_url(org, repo_, revision, path)
                _download(url, target)
            files[path] = target
            continue
        _download(url, target)
        files[path] = target
    assert not maybe_old, (maybe_old, old)
    assert not old or sorted(old) == sorted(SRC_C_OLD), (maybe_old, old)

    return files


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
        print(f'+ fixing {filename}')
        _fix_file(filename, fix)


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
        repo = REPO

    revision, branch = resolve_revision(repo, revision)

    print('downloading...')
    clear_all()
    files = download_all(repo, revision)
    print('...done')

    print('applying fixes...')
    fix_all(list(files.values()))
    print('...done')

    print('writing metadata...')
    write_metadata(repo, revision, files, branch)
    print('...done')


if __name__ == '__main__':
    revision = parse_args()
    main(revision)
