#import re

import _git
import _cparser


def _assert_valid_path(path, files):
    assert path.startswith('/'), repr(path)
    if files is not None:
        if __debug__:
            if path in files:
#                filestext = '{'+'\n'.join(f' {k}: {v}' for k, v in files.items())+'\n}'
                import pprint
                filestext = pprint.pformat(files, indent=2, width=200)
        assert path not in files, f'\n{path} in\n{filestext}'


#############################
# repo

REPO_URL = 'https://github.com/python/cpython'


def resolve_repo(repo=None):
    if repo is None:
        repo = REPO_URL
    return _git.resolve_repo(repo)


def get_downloader(repo, revision, downdir, *,
                   files=None,
                   knowndirs=None,
                   fallback=False,
                   ):
    repo = resolve_repo(repo)
    if knowndirs is None:
        knowndirs = set()

    def download(path):
        _assert_valid_path(path, files)
        target = f'{downdir}/...'
        target, _, _, _, _ = repo.download(path, target, revision,
                                           makedirs=knowndirs,
                                           fallback=fallback)
        if files is not None:
            files[path] = target
        return target

    return download


def get_alts_downloader(repo, revision, downdir, altpaths, *,
                        files=None,
                        knowndirs=None,
                        fallback=False,
                        ):
    repo = resolve_repo(repo)
    if altpaths is not None:
        altpaths = dict(altpaths)
    if knowndirs is None:
        knowndirs = set()

    def download(path):
        _assert_valid_path(path, files)
        target = f'{downdir}/...'
        if altpaths is not None:
            altpath = altpaths.pop(path, None)
            if altpath is not None:
                _assert_valid_path(altpath, files)
        else:
            altpath = None
        target, _, downpath, _, _ = repo.download(path, target, revision,
                                                  altpath=altpath,
                                                  makedirs=knowndirs,
                                                  fallback=fallback)
        if files is not None:
            files[path] = target
        return target, downpath, altpath

    return download, altpaths


#############################
# includes

def _resolve_include(include):
    if include.startswith('pycore_'):
        include = f'internal/{include}'
    #elif '/' not in include:
    return f'/Include/{include}'


#def iter_includes(filename, seen=None):
#    if seen is None:
#        seen = {}
#
#    path = _resolve_include('Python.h')
#    if path not in seen:
#        seen[path] = None
#        yield path
#
#    with open(filename) as infile:
#        for name, kind in _cparser.iter_used(infile, filename):
#            if kind == 'include':
#                path = _resolve_include(name)
#                if path in seen:
#                    continue
#                seen[path] = None
#                yield path
#            elif kind in _cparser.KINDS:
#                continue
#            else:
#                raise NotImplementedError((name, kind))


def iter_includes(filename, seen=None):
    if seen is None:
        seen = {}

    path = _resolve_include('Python.h')
    if path not in seen:
        seen[path] = None
        yield path

    with open(filename) as infile:
        for directive in _cparser.PreprocessorDirective.iter_from_lines(infile):
            if directive.kind != 'include':
                continue
            subkind, name = directive.value
            if subkind == 'system':
                continue
            path = _resolve_include(name)
            if path in seen:
                continue
            seen[path] = None
            yield path


def list_public_headers(repo=None, revision=None, *, fallback=False):
    repo = resolve_repo(repo)
    text = repo.read('/Include/Python.h', revision,
                     encoding='utf-8',
                     fallback=fallback)
    lines = text.splitlines()

    includes = []
    for directive in _cparser.PreprocessorDirective.iter_from_lines(lines):
        if directive.kind != 'include':
            continue
        subkind, name = directive.value
        if subkind == 'system':
            continue
        path = _resolve_include(name)
        if path not in includes:
            includes.append(path)
#    for name, kind in _cparser.iter_used(text.splitlines()):
#        if kind != 'include':
#            continue
#        path = _resolve_include(name)
#        if path not in includes:
#            includes.append(path)
    assert includes
    return includes


#############################
# dependencies

def analyze_dependencies(lines, filename=None, *,
                         download_include=None,
                         recurse=False,
                         ):
    # Python.h is always implied.
    dep = _cparser.CDependencyInclude.from_location(
                        'include-user', 'Python.h', filename)
    implied = [dep]

    yield from _cparser.analyze_dependencies(infile, filename, implied,
                                             download_include=download_include,
                                             recurse=recurse)
