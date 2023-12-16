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
SRC_C = [
    '/Modules/_interpretersmodule.c',
    '/Modules/_interpqueuesmodule.c',
    '/Modules/_channelsmodule.c',
]
# Before PEP 734 is accepted and the impl. merged:
SRC_C_OLD = [
    '/Modules/_xxsubinterpretersmodule.c',
    '/Modules/_xxinterpqueuesmodule.c',
    '/Modules/_xxinterpchannelsmodule.c',
]


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


def _gh_download(org, repo, revision, path, srcdir, reltarget=None, *,
                 _knowndirs=set()):
    path = path.lstrip('/')
    url = GH_DOWNLOAD.format(ORG=org, REPO=repo, REVISION=revision, PATH=path)
    if reltarget:
        target = os.path.join(srcdir, reltarget)
        targetdir = os.path.dirname(target)
    else:
        target = os.path.join(srcdir, os.path.basename(path))
        targetdir = srcdir
    print(' + {}  <- {}'.format(target, url))
    if targetdir not in _knowndirs:
        os.makedirs(targetdir, exist_ok=True)
        _knowndirs.add(targetdir)
    urlretrieve(url, target)
    return target


def download_all(repo, revision, srcdir=None):
    if srcdir is None:
        srcdir = SRC_DIR

    m = re.match('^https://github.com/(\w+)/(\w+)', repo)
    if not m:
        raise ValueError(f'unsupported repo {repo!r}')
    org, repo_ = m.groups()

    pyfiles = {}
    for path in SRC_PY:
        base = f'interpreters/{os.path.basename(path)}'
        target = _gh_download(org, repo_, revision, path, srcdir, base)
        assert path not in pyfiles, pyfiles
        pyfiles[path] = target

    print()
    cfiles = {}
    try:
        for path in SRC_C:
            target = _gh_download(org, repo_, revision, path, srcdir)
            assert path not in cfiles, cfiles
            cfiles[path] = target
    except HTTPError:
        print('-- "new" files not found, falling back to old files --')
        for path, base in zip(SRC_C_OLD, SRC_C):
            base = os.path.basename(base)
            target = _gh_download(org, repo_, revision, path, srcdir, base)
            assert path not in cfiles, cfiles
            cfiles[path] = target

    return dict(**pyfiles, **cfiles)


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
    files = download_all(repo, revision)
    print('...done')

    print('writing metadata...')
    write_metadata(repo, revision, files, branch)
    print('...done')


if __name__ == '__main__':
    revision = parse_args()
    main(revision)
