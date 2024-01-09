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
# diff

#class DiffLine(namedtuple('DiffLine', 'kind a b')):
#
#class DiffHunk(namedtuple('DiffHunk', 'range_a range_b kind lines')):
#
#    KINDS = {
#        'a': 'added',
#        'd': 'deleted',
#        'c': 'changed',
#    }
#
#    def __str__(self):
#        return self._text
#
#    def __repr__(self):
#        raise NotImplementedError
#
#    @property
#    def lines(self):
#        try:
#            return list(self._lines)
#        except AttributeError:
#            self._lines = self.render().splitlines()
#            return list(self._lines)
#
#    @property
#    def total(self):
#        return self.additions + self.deletions
#
#    @property
#    def additions(self):
#        try:
#            return self._additions
#        except AttributeError:
#            raise NotImplementedError
#            return self._additions
#
#    @property
#    def deletions(self):
#        try:
#            return self._deletions
#        except AttributeError:
#            raise NotImplementedError
#            return self._deletions
#
#    def lines_a(self):
#        ...
#
#    def lines_b(self):
#        ...
#
#    def iter_lines(self, start=None):
#        if self.kind == 'a':
#        for line in 
#        ...
#
#    def render(self, fmt=None):
#        if not fmt:
#            fmt = 'traditional'
#
#        if fmt == 'traditional':
#            ...
#        elif fmt == 'context':
#            ...
#        elif fmt == 'git':
#            ...
#        else:
#            raise ValueError(f'unsupported fmt {fmt!r}')
#
#
#class Diff:
#
#    def __init__(self, hunks):
#
#class FileDiffCounts(namedtuple('FileDiffCounts', 'insertions deletions')):
#
#    _lineart = None
#
#    def 
#
#    @property
#    def total(self):
#        return self.insertions + self.deletions
#
#    def format_diffstat(self, filename, width=None):
#        # e.g. "NNN {self.lineart(width-3}"
#        raise NotImplementedError
#
#
#class FileDiffStat(namedtuple('FileDiffStat', 'status insertions deletions')):
#
#    _raw = None
#
#    STATUSES = {
#        'A': 'added',
#        'C': 'copied',
#        'D': 'deleted',
#        'M': 'modified',
#        'R': 'renamed',  # moved
#        'T': 'file type changed',
#        'U': 'unmerged',
#        #'X': '<unknown>,
#    }
#
#    def __str__(self):
#        ...
#
#
#class FileDiff:
#
#    _raw = None
#    _text = None
#    _parts = None
#
#    def __init__(self, filename, status, diffstat=None, parts=None):
#        self.filename = filename
#        self.status = status
#        self.diffstat = FileDiffStat.from_raw(diffstat)
#        self.parts = FileDiffPart
#
#    def render(self, fmt=None):
#        # --name-only
#        # --name-status


class FileDiffStat(namedtuple('FileDiffStat',
                              'name oldname status additions deletions')):

    STATUSES = {
        'A': 'added',
        'C': 'copied',
        'D': 'deleted',
        'M': 'modified',
        'R': 'renamed',  # moved
        'T': 'file type changed',
        'U': 'unmerged',
        #'X': '<unknown>,
    }

    @classmethod
    def parse_all(cls, lines, fmt=None):
        if isinstance(lines, str):
            lines = lines.splitlines()
        if not fmt:
            fmt = '<default>'

        if fmt == '<default>':
            lines = iter(lines)
            for count, line in enumerate(lines):
                m = re.match(r'^ *(\d+) file', line)
                if m:
                    break
                yield cls._parse(line, fmt)

            else:
                raise NotImplementedError
            expected, = m.groups()
            assert count == expected, (count, expected)
            try:
                next(lines)
            except StopIteration:
                pass

        else:
            for line in lines:
                ...


    @classmethod
    def parse(cls, line, fmt=None):
        if not fmt:
            fmt = '<default>'
        return cls._parse(line, fmt)

    @classmethod
    def _parse(cls, line, fmt):
        oldname = status = additions = deletions = total = None

        if fmt == '<default>':
            name, _, changed = line.partition('|')
            name = name.strip()
            if ' => ' in name:
                oldname, name = split(' => ')
                assert oldname and name, (line,)
            total, lineart = changed.split()
            total = int(total)
            if '+' in lineart:
                if '-' in lineart:
                    status = 'M'
                else:
                    # XXX or 'M'?
                    status = 'A'
            elif '-' in lineart:
                # XXX or 'M'?
                status = 'D'
            else:
                raise NotImplementedError((line,))
            if oldname:
                # XXX What about the old status?
                status = 'R'
        elif fmt == '--name-only':
            name = line
        elif fmt == '--name-status':
            status, name = line.split()
        else:
            raise ValueError(f'unsupported fmt {fmt!r}')

        self = cls(name, status, additions, deletions)
        if total is not None:
            self._total = total
        return self

    @property
    def total(self):
        try:
            return self._total
        except AttributeError:
            if self.additions is None:
                if self.deletions is None:
                    self._total = None
                else:
                    # XXX Is this okay?
                    self._total = self.additions
            elif self.deletions is None:
                # XXX Is this okay?
                self._total = self.deletions
            else:
                self._total = self.additions + self.deletions
            return self._total

    def apply_to_dir_listing(self, names):
        name = os.path.relpath(self.name, reldir)
        if os.path.sep in name:
            return
        elif self.status == 'A':
            assert name not in files, self
            files.append(name)
        elif self.status == 'R':
            assert self.oldname, self
            oldname = os.path.relpath(self.oldname, reldir)
            if os.path.sep not in name:
                assert name not in files, self
                files.append(name)
                if os.path.sep not in oldname:
                    assert oldname in files, self
                    files.remove(oldname)
            else:
                assert os.path.sep not in oldname, self
                assert oldname in files, self
                files.remove(oldname)
        else:
            assert name in files, self
            if self.status == 'D':
                files.remove(name)
            elif self.status in 'MT':
                pass
            elif self.status == 'C':
                raise NotImplementedError(self)
            elif self.status == 'U':
                raise NotImplementedError(self)
            elif self.status == 'X':
                raise NotImplementedError(self)
            else:
                raise NotImplementedError(self)


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
    def _resolve_fallback_revisions(cls, ref, seen=None):
        candidate = cls.FALLBACK_REVISIONS.get(ref)
        if not candidate:
            return []
        if seen is None:
            seen = set()
        elif candidate in seen:
            return []
        fallbacks = []

        candidates = [candidate]
        while candidates:
            candidate = candidates.pop(0)
            fallbacks.append(candidate)

            candidate = cls.FALLBACK_REVISIONS.get(candidate)
            if candidate in seen:
                continue
            seen.add(candidate)
            candidates.append(candidate)

        return fallbacks

    @classmethod
    def _resolve_revisions(cls, ref, fallback=True):
        if not ref:
            ref = cls.REVISION

        metarefs = cls._resolve_meta_revision(ref)
        assert metarefs, (ref,)
        refs = [metarefs[-1]]
        seen = set(refs)

        if fallback:
            for metaref in metarefs:
                fallbacks = cls._resolve_fallback_revisions(metaref, seen)
                refs.extend(fallbacks)
        assert len(refs) == len(seen), (refs, seen)

        return refs

    # "public" methods

    def resolve_revision(self, ref, *, fallback=True):
        _, res = self._try_resolved_revisions(ref, self._resolve_revision, fallback)
        return res

    def download(self, path, target, revision=None, *,
                 altpath=None,
                 makedirs=True,
                 dummies=None,
                 fallback=True,
                 ):
        def download(ref):
            return self._download(path, target, ref,
                                  altpath, makedirs, dummies)
        _, res = self._try_resolved_revisions(revision, download, fallback)
        return res

    def read(self, path, revision=None, *, encoding=None, fallback=True):
        def read(ref):
            return self._read(path, ref, encoding)
        _, res = self._try_resolved_revisions(revision, read, fallback)
        return res

    def listdir(self, path=None, revision=None, *, fallback=True):
        def listdir(ref):
            return self._listdir(path, ref)
        _, res = self._try_resolved_revisions(revision, listdir, fallback)
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

    def _try_resolved_revisions(self, revision, task, fallback):
        firstexc = None
        revisions = self._resolve_revisions(revision, fallback)
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

#    def _get_filename(self, path, revision, force=False):
#        # XXX
#        raise NotImplementedError
#        filename = self._resolve_filename(path)
#        if force:
#            return filename
#        elif revision is LOCAL:
#            return filename
#        elif revision is STAGED:
#            if 
#            ...
