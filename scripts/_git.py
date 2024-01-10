from collections import namedtuple
import os.path
import re
import shutil
import types

import _utils


GIT = shutil.which('git')

# meta revisions
HEAD = 'HEAD'
LOCAL = '<LOCAL>'
STAGED = '<STAGED>'


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


def split_relpath(path):
    return list(_iter_relpath(path))


def _iter_relpath(path):
    if isinstance(path, str):
        assert isinstance(first, str)
        if path.startswith('/'):
            assert not path.startswith('//'), (path,)
            if path.endswith('/'):
                assert not path.endsswith('//'), (path,)
                path = path[1:-1]
            else:
                path = path[1:]
        yield from path.split('/')
    else:
        for p in path:
            assert isinstance(p, str), (p,)
            assert not p.startswith('/'), (p,)
            assert not p.endswith('/'), (p,)
            yield from p.split('/')


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


#############################
# repos

class RevisionNotFoundError(KeyError):
    ...


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
    TREE = 'https://api.github.com/repos/{ORG}/{REPO}/git/trees/{SHA}'

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
        data = _utils.read_url(url, encoding='json')
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
        # XXX Raise RevisionNotFoundError when appropriate.
        target, url, path = _utils.download_path(baseurl, path, target,
                                                 altpath=altpath,
                                                 makedirs=makedirs,
                                                 dummies=dummies)
        return target, url, path, revision, branch

    def read(self, path, revision=None, *, encoding=None):
        baseurl = self.DOWNLOAD.format(
            ORG=self.org,
            REPO=self.name,
            REVISION=revision,
            PATH='',
        )
        # XXX Raise RevisionNotFoundError when appropriate.
        return _utils.read_path(baseurl, path, encoding=encoding)


class Repo:

    REVISION = HEAD
    META_REVISIONS = types.MappingProxyType({
        HEAD: None,
        # staged changes:
        STAGED: None,
        # local changes:
        LOCAL: None,
    })
    FALLBACK_REVISIONS = types.MappingProxyType({
        'main': 'master',
    })

    def __init_subclass__(cls):
        if 'META_REVISIONS' in cls.__dict__:
            cls._normalize_meta_revisions()

    @classmethod  # class-only
    def _normalize_meta_revisions(cls):
        ns = cls.META_REVISIONS
        for key, value in cls.META_REVISIONS.items():
            if key:
                normkey = cls._normalize_meta_revision(key)
                if normkey is not key:
                    if isinstance(ns, types.MappingProxyType):
                        ns = dict(ns)
                    del ns[key]
                    ns[normalized] = value
                    key = normalized
            if value:
                normvalue = cls._normalize_meta_revision(value)
                if normvalue is not value:
                    if isinstance(ns, types.MappingProxyType):
                        ns = dict(ns)
                    ns[key] = normvalue
                    value = normvalue
            if key == value:
                ns[key] = key
        if ns is not cls.META_REVISIONS:
            assert not isinstance(cls.META_REVISIONS, types.MappingProxyType)
            cls.META_REVISIONS = types.MappingProxyType(ns)

    @classmethod
    def _normalize_meta_revision(cls, ref):
        for metaref in Repo.META_REVISIONS:
            if ref == metaref:
                return metaref
        return ref

    @classmethod
    def _resolve_meta_revision(cls, ref):
        # The last item in the returned list is the final resolution.
        assert ref
        seen = set()
        resolved = [ref]
        meta = ref
        while meta in cls.META_REVISIONS:
            mnext = cls.META_REVISIONS[meta]
            if mnext is None:
                raise ValueError(f'meta ref {ref!r} not supported')
            elif mnext == meta:
                break
            meta = mnext
            assert meta not in seen, (meta, seen)
            seen.add(meta)
            resolved.append(meta)
        return resolved

    @classmethod
    def _resolve_revisions(cls, ref):
        if not ref:
            ref = cls.REVISION

        metarefs = cls._resolve_meta_revision(ref)
        assert metarefs, (ref,)
        refs = [metarefs[-1]]
        seen = set(refs)

        return refs

    # "public" methods

    def resolve_revision(self, ref):
        _, res = self._try_resolved_revisions(ref, self._resolve_revision)
        return res

    def download(self, path, target, revision=None, *,
                 altpath=None,
                 makedirs=True,
                 dummies=None,
                 ):
        def download(ref):
            return self._download(path, target, ref,
                                  altpath, makedirs, dummies)
        _, res = self._try_resolved_revisions(revision, download)
        return res

    def read(self, path, revision=None, *, encoding=None):
        def read(ref):
            return self._read(path, ref, encoding)
        _, res = self._try_resolved_revisions(revision, read)
        return res

    def listdir(self, path=None, revision=None):
        def listdir(ref):
            return self._listdir(path, ref)
        _, res = self._try_resolved_revisions(revision, listdir)
        return res

    # implemented by subclasses

    def _resolve_revision(self, ref):
        raise NotImplementedError

    def _download(self, path, target, revision,
                  altpath=None, makedirs=True, dummies=None):
        raise NotImplementedError

    def _read(self, path, revision=None, encoding=None):
        raise NotImplementedError

    def _listdir(self, path=None, revision=None):
        raise NotImplementedError

    # internal implementation

    def _try_resolved_revisions(self, revision, task):
        firstexc = None
        revisions = self._resolve_revisions(revision)
        while revisions:
            ref = revisions.pop(0)
            try:
                return ref, task(ref)
            except RevisionNotFoundError as exc:
                if firstexc is None:
                    if not revisions:
                        raise  # re-raise
                    firstexc = exc
                elif not revisions:
                    # XXX Raise ExceptionGroup instead of the first exc.
                    raise firstexc
        assert 0, 'unreachable!'


class RemoteRepo(Repo):

    META_REVISIONS = {
        HEAD: 'main',
        # Remote repos don't expose a staging area.
        STAGED: 'main',
        # Remote repos don't expose local changes.
        LOCAL: 'main',
    }

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

    # Repo method implementations

    def _resolve_revision(self, ref):
        gh = self._resolve_github()
        if gh:
            _, rev, branch = gh.get_commit(ref)
        else:
            raise NotImplementedError
        return rev, branch

    def _download(self, path, target, revision,
                  altpath=None, makedirs=True, dummies=None):
        gh = self._resolve_github()
        if gh:
            return gh.download(path, target, revision,
                               altpath=altpath,
                               makedirs=makedirs,
                               dummies=dummies)
        else:
            raise NotImplementedError

    def _read(self, path, revision=None, encoding=None):
        gh = self._resolve_github()
        if gh:
            return gh.read(path, revision, encoding=encoding)
        else:
            raise NotImplementedError

    def _listdir(self, path=None, revision=None):
        raise NotImplementedError

    # remote-specific methods

    def clone(self, root, branch=None):
        return Local.from_url(self.url, root, branch=branch)

    # internal implementation

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


class LocalRepo(Repo):

    _GIT = GIT

    #STAGED_ONLY = '<STAGED-ONLY>'
    META_REVISIONS = {
        HEAD: HEAD,
        STAGED: STAGED,
        LOCAL: LOCAL,
        #STAGED_ONLY: STAGED_ONLY,
    }

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

    # Repo method implementations

    def _resolve_revision(self, ref):
        if revision in (STAGED, LOCAL):
            revision = HEAD
        raise NotImplementedError

    def _download(self, path, target, revision,
                  altpath=None, makedirs=True, dummies=None):
        filename = self._resolve_filename(path)
        # XXX Raise RevisionNotFoundError when appropriate.
        if revision == '<STAGED>':
            # Use HEAD with staged files included.
            raise NotImplementedError
        elif revision == '<LOCAL>':
            # Use the current directory.
            raise NotImplementedError
        else:
            raise NotImplementedError

    def _read(self, path, revision=None, encoding=None):
        filename = self._resolve_filename(path)
        # XXX Raise RevisionNotFoundError when appropriate.
        if revision == '<STAGED>':
            # Read directly from the filesystem if no unstaged changes.
            # Otherwise read the staged file, if staged, else HEAD.
            raise NotImplementedError
        elif revision == '<LOCAL>':
            # Read the file directly from the filesystem.
            raise NotImplementedError
        else:
            # Read 
            raise NotImplementedError

    def _listdir(self, path=None, revision=None):
        if path:
            reldir = self._resolve_relfile(path)
            dirname = os.path.join(self.root, reldir)
        else:
            reldir = '.'
            dirname = self.root

        # XXX Raise RevisionNotFoundError when appropriate.
        if revision is LOCAL or revision is STAGED:
            text = self._run_text(
#                'ls-tree', '--name-only', '--full-name', HEAD, reldir)
                'ls-tree', '--name-only', HEAD, reldir)
            files = text.splitlines()

            text = self._run_text('diff', '--name-status', '--cached')
            for ds in FileDiffStat.parse_all(text, fmt='--name-status'):
                ds.apply_to_dir_listing(files)

            if revision is LOCAL:
                text = self._run_text('diff', '--name-status')
                for ds in FileDiffStat.parse_all(text, fmt='--name-status'):
                    ds.apply_to_dir_listing(files)

            return files
        else:
            text = self._run_text(
                'ls-tree', '--name-only', revision, reldir)
            return text.splitlines()

    # local-specific methods

    def resolve_filename(self, *path):
        return self._resolve_absfile(path)

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

    # internal implementation

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
        return stdout

    def _resolve_relfile(self, path):
        return os.path.join(
            *_iter_relpath(path),
        )

    def _resolve_absfile(self, path):
        return os.path.join(
            self.root,
            *_iter_relpath(path),
        )
