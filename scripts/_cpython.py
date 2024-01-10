#import re

import _git


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
                   ):
    repo = resolve_repo(repo)
    if knowndirs is None:
        knowndirs = set()

    def download(path):
        _assert_valid_path(path, files)
        target = f'{downdir}/...'
        target, _, _, _, _ = repo.download(path, target, revision,
                                           makedirs=knowndirs)
        if files is not None:
            files[path] = target
        return target

    return download


def get_alts_downloader(repo, revision, downdir, altpaths, *,
                        files=None,
                        knowndirs=None,
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
                                                  makedirs=knowndirs)
        if files is not None:
            files[path] = target
        return target, downpath, altpath

    return download, altpaths
