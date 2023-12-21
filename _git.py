import json
import os.path
import re
import shutil
from urllib.request import urlopen

import _utils


GIT = shutil.which('git')


def run(cmd, *subargv,
        root=None,
        capture=False,
        _git=GIT,
        ):
    return _run(
        cmd, subargv, root, capture, _git,
        check=check,
    )


def run_stdout(cmd, *subargv,
               root=None,
               _git=GIT,
               ):
    capture = True
    _, stdout, _ = _run(
        cmd, subargv, root, capture, _git,
        check=True,
    )
    return stdout


def _run(cmd, subargv, root, capture, _git, **kwargs):
    return _utils.run(_git or GIT, cmd, *subargv,
                      capture=capture,
                      cwd=root,
                      **kwargs)


def parse_url(url):
    github = None
    url, localroot = _utils.parse_url(url)
    if url:
        m = re.match('^https://github.com/(\w+)/(\w+)', url)
        if m:
            org, repo = m.groups()
            github = (org, repo)
        else:
            m = re.match('git@github.com:(\w+)/(\w+).git', url)
            if m:
                org, repo = m.groups()
                github = (org, repo)
    return url, localroot, github


def resolve_repo(repo):
    if isinstance(repo, (LocalRepo, RemoteRepo)):
        return repo
    elif isinstance(repo, str):
        repo, localroot = _utils.parse_url(repo)
        if localroot:
            return LocalRepo.from_filename(localroot)
        else:
            return RemoteRepo(repo)
    else:
        raise NotImplementedError


class GitHubRepo:

    DOWNLOAD = 'https://raw.github.com/{ORG}/{REPO}/{REVISION}/{PATH}'
    COMMIT = 'https://api.github.com/repos/{ORG}/{REPO}/commits/{REF}'
    #BRANCH = 'https://api.github.com/repos/{ORG}/{REPO}/branches/{BRANCH}'

    @classmethod
    def from_url(cls, url):
        actual, localroot, github = parse_url(url)
        if localroot:
            raise ValueError(f'expected a URL, go {url!r}')
        if not github:
            raise ValueError(f'unsupported GitHub URL {url!r}')
        self = cls(*github)
        self._url = actual
        return self

    def __init__(self, org, name):
        self.org = org
        self.name = name

    def get_commit(self, ref):
        # https://docs.github.com/en/rest/commits/commits?apiVersion=2022-11-28#get-a-commit
        url = self.COMMIT.format(ORG=self.org, REPO=self.name, REF=ref)
        with urlopen(url) as resp:
            data = json.load(resp)
        rev = data['sha']
        assert rev
        branch = None if rev.startswith(ref) else ref
        return data, rev, branch

    def download(self, path, target, revision=None, *,
                 altpath=None,
                 makedirs=True,
                 dummies=None,
                 ):
        if not revision:
            branch = 'main'
            _, revision, _ = self.get_commit(branch)
        else:
            branch = None

        baseurl = self.DOWNLOAD.format(
            ORG=self.org,
            REPO=self.name,
            REVISION=revision,
            PATH='',
        )
        target, url, path = _utils.download_path(baseurl, path, target,
                                                 altpath=altpath,
                                                 makedirs=makedirs,
                                                 dummies=dummies)
        return target, url, path, revision, branch


class RemoteRepo:

    @classmethod
    def from_raw_url(cls, url, *, localremote=True):
        url, localroot, github = parse_url(url)

        local = None
        if localroot:
            if not localremote:
                raise ValueError('expected a remote URL, got {url!r}')
            url = None
            self = cls.from_local_remote(localroot, localremote)
        else:
            if not url.startswith('https://'):
                raise ValueError(f'unsupported repo scheme {url}')
            self = cls(url)

        if github:
            self._github = GitHubRepo(*github)
        return self

    @classmethod
    def from_local_remote(cls, localroot, remote=('upstream', 'origin')):
        if not remote:
            remotes = ('upstream', 'origin')
        elif isinstance(remote, str):
            remotes = (remote,)
        else:
            remotes = remote
        local = Local.from_filename(localroot)
        for remote in remotes:
            found = local.get_remote(remote)
            if found:
                url = found
                #url = found.url
                break
        else:
            raise Exception('could not determine remote URL from local repo {local.root!r}')

        self = cls(url)
        self._local = local
        return self

    def __init__(self, url):
        self.url = url

    def _resolve_github(self):
        try:
            return self._github
        except AttributeError:
            _, _, github = parse_url(self.url)
            if not github:
                self._github = None
                return None
            self._github = GitHubRepo(*github)
            return self._github

    def clone(self, root, branch=None):
        return Local.from_url(self.url, root, branch=branch)

    def resolve_revision(self, ref):
        gh = self._resolve_github()
        if gh:
            _, rev, branch = gh.get_commit(ref)
        else:
            raise NotImplementedError
        return rev, branch

    def download(self, path, target, revision=None, *,
                 altpath=None,
                 makedirs=True,
                 dummies=None,
                 ):
        if not revision:
            revision = 'main'

        gh = self._resolve_github()
        if gh:
            return gh.download(path, target, revision,
                               altpath=altpath,
                               makedirs=makedirs,
                               dummies=dummies)
        else:
            raise NotImplementedError


class LocalRepo:

    _GIT = GIT

    @classmethod
    def from_url(cls, url, root, *, branch=None):
        self = cls(root)

        branch = ('--branch', branch) if branch else ()
        ec = run('clone', *branch, url, root, _git=cls._GIT)
        if ec != 0:
            raise Exception(f'failed to clone {self.url}')

        return self

    @classmethod
    def from_filename(cls, filename):
        dirname, basename = os.path.split(filename)
        if basename and os.path.isdir(filename):
            dirname = filename
        root = run_text('root', root=dirname, _git=cls._GIT)
        return cls(root)

    def __init__(self, root):
        self.root = root

    def _run(self, cmd, *subargv, capture=False):
        return _run(
            cmd, subargv, self.root, capture, self._GIT,
            check=False,
        )

    def _run_text(self, cmd, *subargv):
        capture = True
        _, stdout, _ = _run(
            cmd, subargv, self.root, capture, self._GIT,
            check=True,
        )
        return ec, stdout

    def resolve_revision(self, ref):
        raise NotImplementedError

    def download(self, path, target, revision=None, *,
                 altpath=None,
                 makedirs=True,
                 dummies=None,
                 ):
        raise NotImplementedError

    def get_remote(self, name):
        raise NotImplementedError

    def get_remotes(self, *, httpsonly=True):
        ec, stdout, _ = self._run(
            'remote', ('-v'),
            capture=True,
        )
        if ec != 0:
            return {}

        remotes = {}
        for line in stdout.splitlines():
            if not line.endswith(' (fetch)'):
                continue
            try:
                remote, url, _ = line.split()
            except ValueError:
                continue
            assert remote not in remotes, repr(remote)
            if not url.startswith('https://'):
                if httpsonly:
                    continue
#            print(f'{remote:20} {url}')
            remotes[remote] = url
        return remotes
