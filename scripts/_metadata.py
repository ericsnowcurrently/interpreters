from collections import namedtuple
import logging
#import os
import os.path
import textwrap

import _cpython
import _git
import _utils
from _utils import INDENT


logger = logging.getLogger('_metadata')


ROOT = os.path.abspath(
        os.path.dirname(
            os.path.dirname(__file__)))
METADATA = 'METADATA'
METADATA_FILE = os.path.join(ROOT, METADATA)


def write(repo, revision, downloaded, branch=None, filename=None):
    metadata = Metadata.from_values(repo, revision, downloaded, branch=branch)
    return metadata.write(filename)


class Metadata(namedtuple('Metadata', 'repourl revision branch files')):

    @classmethod
    def from_values(cls, repo, revision, downloaded, *, branch=None):
        repo = _cpython.resolve_repo(repo)
        files = MetadataFiles(downloaded)
        self = cls(repo, revision, branch, files)
        self._repo = repo
        return self

    def __new__(cls, repourl, revision, branch, files):
        if not repourl:
            raise ValueError('missing repourl')
        repourl = _utils.normalize_url_str(repourl)
        _git.validate_revision(revision)
        if branch:
            _git.validate_branch(branch)
        files = MetadataFiles.from_raw(files)

        self = super().__new__(
            cls,
            repourl=repourl,
            revision=revision,
            branch=branch or None,
            files=files,
        )
        return self

    def render(self, fmt=None):
        if fmt is None:
            fmt = CSVFormat()
        else:
            fmt = normalize_format(fmt)
        yield from fmt.render(self)

    def write(self, filename=None, fmt=None, timestamp=None):
        if not filename:
            filename = METADATA_FILE
        elif filename.endswith(('/', os.path.sep)):
            filename += METADATA
        timestamp = _utils.normalize_timestamp(timestamp)

        lines = iter(self.render(fmt))
        with open(filename, 'w', encoding='utf-8') as outfile:
            outfile.write(next(lines))
            for line in lines:
                outfile.write('\n')
                outfile.write(line)


class MetadataFiles(namedtuple('MetadataFiles', 'downloaded')):

    @classmethod
    def from_raw(cls, raw):
        if not raw:
            raise ValueError('missing files')
        elif isinstance(raw, cls):
            return raw
        elif isinstance(raw, str):
            raise TypeError(f'unsupported files {raw!r}')
        else:
            try:
                downloaded = list(raw)
            except TypeError:
                raise TypeError(f'unsupported files {raw!r}')
            return cls(downloaded=downloaded)

    @classmethod
    def _normalize_downloaded(cls, downloaded):
        if not downloaded:
            raise ValueError('missing downloaded')
        try:
            items = downloaded.items()
        except AttributeError:
            items = downloaded
        norm = []
        try:
            for path, target in items:
                _utils.validate_path(path)
                filename = _utils.normalize_filename(target)
                norm.append((path, filename))
        except Exception:
            raise ValueError(f'invalid downloaded {downloaded!r}')
        return tuple(norm)

    def __new__(cls, downloaded):
        downloaded = cls._normalize_downloaded(downloaded)
        self = super().__new__(
            cls,
            downloaded=downloaded,
        )
        return self


#######################################
# formats

def normalize_format(fmt):
    if fmt is None:
        raise ValueError('missing fmt')
    elif isinstance(fmt, Format):
        return fmt
    elif isinstance(fmt, str):
        raise NotImplementedError(fmt)
    else:
        raise TypeError(f'unsupported fmt {fmt!r}')


class Format:
    pass


class CSVFormat(Format, namedtuple('CSVFormat', 'files indent timestamp')):

    TIMESTAMP = '%Y-%m-%d %H:%M:%S'

    TEMPLATE = textwrap.dedent("""
        [DEFAULT]
        timestamp = {{timestamp:{}}}

        [upstream]
        repo = {{repo}}
        revision = {{revision}}
        branch = {{branch}}

        [files]
        downloaded = {{downloaded}}
        """)

    def __new__(cls, files=None, indent=INDENT, timestamp=TIMESTAMP):
        indent = _utils.normalize_indent(indent)
        if files is None:
            files = FilesFormat(indent=indent)
        else:
            files = FilesFormat.from_raw(files)
        if not timestamp:
            timestamp = cls.TIMESTAMP
        elif not isinstance(timestamp, str):
            raise TypeError(f'unsupported timestamp format {timestamp!r}')

        self = super().__new__(cls, files, indent, timestamp)
        self._template = cls.TEMPLATE.format(timestamp)
        return self

    def render(self, metadata, downdir=None, filesfmt=None, timestamp=None):
        files = self.files.render_as_dict(metadata.files, filesfmt,
                                          downdir=downdir)
        timestamp = _utils.normalize_timestamp(timestamp)
        text = self._template.format(
            timestamp=timestamp,
            repo=metadata.repourl,
            revision=metadata.revision,
            branch=metadata.branch or '',
            downloaded='',
        )

        lines = iter(text.splitlines())
        for line in lines:
            yield line
            if line == '[files]':
                break

        # render the files section
        for line in lines:
            key, sep, after = line.partition(' = ')
            assert sep and not after, (line,)
            fileslines = iter(files.pop(key))
            first = next(fileslines)
            yield line + first
            # XXX Apply indents here instead of in FilesFormat?
            for line in fileslines:
                yield line
        assert not files, files


class FilesFormat(namedtuple('FilesFormat', 'fmt indent downfile')):

    FORMATS = {
        'dict-raw',
    }
    DOWNFILE_FORMATS = {
        'dict-raw': 'directed-raw',
    }

    def __new__(cls, fmt='dict-raw', indent=None, downfile=None):
        if not fmt:
            fmt = 'dict-raw'
        elif fmt not in cls.FORMATS:
            raise ValuError(f'unsupported fmt {fmt!r}')
        indent = _utils.normalize_indent(indent)
        if downfile is None:
            downfile = DownfileFormat(
                fmt=cls.DOWNFILE_FORMATS.get(fmt),
                indent=indent,
            )

        self = super().__new__(
            cls,
            fmt=fmt,
            indent=indent,
            downfile=downfile,
        )
        return self

    def render(self, files, downroot=None, depth=0):
        files = MetadataFiles.from_raw(files)

    def render_as_dict(self, files, fmt='dict-raw', *,
                       downdir=None,
                       depth=0,
                       indent=INDENT,
                       ):
        if not fmt:
            fmt = 'dict-raw'
        if downdir is not None:
            downroot = downdir
            downdir = os.path.relpath(downdir, ROOT)
        else:
            downroot = ROOT

        rendered = dict(
            downloaded=None,
        )

        # downloaded
        lines = []
        if fmt == 'dict-raw':
            lines.append('{')
            for path, target in sorted(files.downloaded):
                lines.append(
                    self.downfile.format(path, target, downroot, depth+1),
                )
            lines.append((self.indent * depth) + '}')
        rendered['downloaded'] = lines

        return rendered


class DownfileFormat(namedtuple('DownfileFormat', 'fmt indent relroot pathwidth')):

    FORMATS = {
        'directed-raw',
    }
    FORMAT = 'directed-raw'
    PATH_WIDTH = 45

    def __new__(cls, fmt=FORMAT, indent=INDENT, relroot=None, pathwidth=PATH_WIDTH):
        if not fmt:
            fmt = 'directed-raw'
        elif fmt not in cls.FORMATS:
            raise ValuError(f'unsupported fmt {fmt!r}')
        indent = _utils.normalize_indent(indent)
        if relroot:
            if not isinstance(relroot, str):
                raise TypeError(f'unsupported relroot {relroot!r}')
        if pathwidth is None:
            pass
        elif not isinstance(pathwidth, int):
            raise TypeError(f'unsupported pathwidth {pathwidth!r}')
        elif pathwidth <= 0:
            pathwidth = None
        self = super().__new__(
            cls,
            fmt=fmt,
            indent=indent,
            relroot=relroot or ROOT,
            pathwidth=pathwidth or cls.PATHWIDTH,
        )
        return self

    def format(self, path, target, relroot=True, depth=0):
        _utils.validate_path(path)
        if relroot is True:
            relroot = self.relroot
        relfile = _utils.normalize_filename(target, relroot or None)
        depth = _utils.normalize_depth(depth)

        if self.fmt == 'directed-raw':
            return f'{depth * self.indent}{path:{self.pathwidth}} -> {relfile}'
        else:
            raise NotImplementedError(repr(fmt))
