from collections import namedtuple
import logging
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

    def write(self, filename=None, timestamp=None):
        if not filename:
            filename = METADATA_FILE
        elif filename.endswith(('/', os.path.sep)):
            filename += METADATA
        timestamp = _utils.normalize_timestamp(timestamp)

        text = textwrap.dedent(f"""
            [DEFAULT]
            timestamp = {timestamp:%Y-%m-%d %H:%M:%S}

            [upstream]
            repo = {self.repourl}
            revision = {self.revision}
            branch = {self.branch or ''}

            [files]
            downloaded = {{}}
            """)

        # downloads
        lines = ['{']
        for path, target in sorted(self.files.downloaded):
            reltarget = os.path.relpath(target, ROOT)
            lines.append(f'{INDENT}{path:45} -> {reltarget}')
        lines.append(INDENT + '}')
        text = text.format(os.linesep.join(lines))

        # write the file
        logger.debug(f'writing metadata to {filename}')
        with open(filename, 'w', encoding='utf-8') as outfile:
            outfile.write(text)
        return filename


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
