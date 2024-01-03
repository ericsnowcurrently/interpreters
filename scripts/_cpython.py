#import re

import _git
import _cparser


#############################
# repo

REPO_URL = 'https://github.com/python/cpython'


def resolve_repo(repo=None):
    if repo is None:
        repo = REPO_URL
    return _git.resolve_repo(repo)


#############################
# includes

def _resolve_include(include):
    if include.startswith('pycore_'):
        include = f'internal/{include}'
    #elif '/' not in include:
    return f'/Include/{include}'


def iter_includes(filename, seen=None):
    if seen is None:
        seen = {}

    path = _resolve_include('Python.h')
    if path not in seen:
        seen[path] = None
        yield path

    with open(filename) as infile:
        for name, kind in _cparser.iter_used(infile, filename):
            if kind == 'include':
                path = _resolve_include(name)
                if path in seen:
                    continue
                seen[path] = None
                yield path
            elif kind in _cparser.KINDS:
                continue
            else:
                raise NotImplementedError((name, kind))


def list_public_headers(repo=None, revision=None):
    repo = resolve_repo(repo)
    text = repo.read('/Include/Python.h', revision, encoding='utf-8')
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
