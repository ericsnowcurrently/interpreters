import glob
import hashlib
import io
import json
import logging
import os
import os.path
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlparse
from urllib.request import urlretrieve, urlopen
from urllib.error import HTTPError


logger = logging.getLogger('_utils')


#######################################
# logging

VERBOSITY = 3  # logging.INFO
MAX_LEVEL = logging.CRITICAL  # 50
LEVEL_PER_VERBOSITY = 10


def init_logger(logger, verbosity=VERBOSITY, *, propagate=True):
    level = min(MAX_LEVEL,
                max(1,  # 0 would disable logging.
                    (MAX_LEVEL) - verbosity * LEVEL_PER_VERBOSITY))

    # init the formatter
    formatter = logging.Formatter()

    # init the handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(formatter)

    # XXX Use a different handler (with sys.stderr) for WARN/ERROR/CRITICAL?

    # init the logger
    logger.addHandler(handler)
    if not logger.isEnabledFor(level):
        logger.setLevel(level)
    logger.propagate = propagate


#######################################
# run commands

def run(cmd, *argv, capture=False, **kwargs):
    argv = [cmd, *argv]
    if capture:
        kwargs.update(dict(
            capture_output=True,
            encoding='utf-8',
        ))
    proc = subprocess.run(
        argv,
        **kwargs,
    )
    return proc.returncode, proc.stdout, proc.stderr


#######################################
# filesystem

def _maybe_make_parent_dir(filename, makedirs=True, *, _knowndirs=set()):
    if makedirs is True:
        knowndirs = _knowndirs
    elif isinstance(makedirs, set):
        knowndirs = makedirs 
        makedirs = True
    else:
        knowndirs = ()
    if makedirs:
        dirname = os.path.dirname(filename)
        if dirname not in knowndirs:
            os.makedirs(dirname, exist_ok=True)
            knowndirs.add(dirname)


def clear_directory(dirname):
    try:
        names = os.listdir(dirname)
    except FileNotFoundError:
        return
    for basename in names:
        filename = os.path.join(dirname, basename)
        if os.path.isdir(filename):
            shutil.rmtree(filename)
        else:
            os.unlink(filename)


def rm_files(*globs):
    for pat in globs:
        for filename in glob.iglob(pat):
            try:
                os.unlink(filename)
            except FileNotFoundError:
                pass


def copy_file(source, target, *, makedirs=True):
    with open(source) as infile:
        text = infile.read()
    _maybe_make_parent_dir(target, makedirs)
    with open(target, 'w') as outfile:
        outfile.write(text)


def touch(filename, *, makedirs=True):
    _maybe_make_parent_dir(filename, makedirs)
    with open(filename, 'w'):
        pass


def normalize_backup(backup):
    if callable(backup):
        return backup
    elif not backup:
        return None
    elif isinstance(backup, str):
        if backup.startswith(('.', '-')):
            suffix = backup
            def backup(filename, *, _suffix=suffix):
                if _suffix[1:] == '<NOW>':
                    timestamp = datetime.datetime.utcnow()
                    _suffix=f'{suffix[0]}{timestamp:%Y%m%d-%H%M%S}'
                target = f'{filename}{_suffix}'
                logger.debug(f'backup up {filename} to {target}')
                shutil.copyfile(filename, target)
                shutil.copymode(filename, target)
            return backup
        else:
            raise NotImplementedError((backup,))
    else:
        raise TypeError(f'unsupported backup {backup!r}')


class BlobFileOverwriter:

    def __init__(self, filename, backup=None):
        self._filename = filename
        self._closed = False
        self._infile = None
        self._outfile = None
        self._backup = normalize_backup(backup)

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.close()

    def __iter__(self):
        while True:
            line = self.readline()
            yield line
            if not line:
                break

    @property
    def name(self):
        return self._filename

    def readline(self):
        if self._closed:
            raise ValueError('operation on closed file')
        if self._infile is None:
            with open(self._filename, encoding='utf-8') as infile:
                text = infile.read()
            self._infile = io.StringIO(text)
        return self._infile.readline()

    def read(self):
        if self._closed:
            raise ValueError('operation on closed file')
        if self._infile is None:
            with open(self._filename, encoding='utf-8') as infile:
                text = infile.read()
            self._infile = io.StringIO(text)
        return self._infile.read()

    def overwrite(self, text):
        if self._closed:
            raise ValueError('operation on closed file')
        if self._outfile is None:
            self._outfile = io.StringIO()
        return self._outfile.write(text)

    def overwritelines(self, lines):
        if self._closed:
            raise ValueError('operation on closed file')
        if self._outfile is None:
            self._outfile = io.StringIO()
        return self._outfile.writelines(lines)

    def close(self):
        if self._closed is None:
            return
        self._closed = None

        if self._outfile is None:
            return
        intext = self._infile.getvalue() if self._infile is not None else None
        outtext = self._outfile.getvalue()
        if outtext != intext:
            if self._backup is not None:
                self._backup(self._filename)
            with open(self._filename, 'w', encoding='utf-8') as outfile:
                outfile.write(outtext)


class LinesFileOverwriter:

    @classmethod
    def open(cls, filename, backup=None):
        file = open(filename, encoding='utf-8')
        try:
            self = cls(file, backup)
        except Exception:
            file.close()
            raise  # re-raise
        self._owned = True
        return self

    def __init__(self, file, backup=None):
        self._filename = self._infile.name
        self._closed = False
        self._owned = False
        self._infile = file
        self._inhash = hashlib.sha256()
        self._outfile = None
        self._outhash = hashlib.sha256()
        self._backup = normalize_backup(backup)

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.close()

    def __iter__(self):
        try:
            for line in self._infile:
                self._inhash.update(line.encode('utf-8'))
                yield line
        except Exception:
            if self._infile.closed:
                self.close()
            raise  # re-raise

    @property
    def name(self):
        return self._filename

    def readline(self):
        try:
            line = self._infile.readline()
        except Exception:
            if self._infile.closed:
                self.close()
            raise  # re-raise
        self._inhash.update(line.encode('utf-8'))
        return line

    def read(self):
        try:
            text = self._infile.read()
        except Exception:
            if self._infile.closed:
                self.close()
            raise  # re-raise
        self._inhash.update(text.encode('utf-8'))
        return text

    def overwrite(self, text):
        if self._closed:
            raise ValueError('operation on closed file')
        if self._outfile is None:
            self._outfile = tempfile.NamedTemporaryFile('w', encoding='utf-8')
        self._outhash.update(text)
        return self._outfile.write(text)

    def overwritelines(self, lines):
        if self._closed:
            raise ValueError('operation on closed file')
        if self._outfile is None:
            self._outfile = tempfile.NamedTemporaryFile('w', encoding='utf-8')
        for line in lines:
            self._outhash.update(line)
            self._outfile.write(line)

    def close(self):
        if self._closed is None:
            return
        self._closed = None

        if self._owned:
            self._infile.close()
        if self._outfile is None:
            # never overwritten
            return
        self._outfile.close()
        if self._outhash.digest() != self._inhash.digest():
            if self._backup is not None:
                self._backup(self._filename)
            target = self._outfile.name
            shutil.copymode(self._filename, target)
            os.rename(target, self._filename)


#######################################
# text transformation

class TextFix:

    @classmethod
    def apply_all_to_file(cls, fixes, file, *, backup=None):
        if isinstance(file, str):
            filename = file
            file = BlobFileOverwriter(filename, backup)
        else:
            file = LinesFileOverwriter(file, backup)
        with file:
            cls._apply_to_file_overwriter(fixes, file)

    @classmethod
    def _apply_to_file_overwriter(cls, fixes, file):
        text = file.read()
        for fix in fixes:
            text = fix.apply_to_text(text)
        file.overwrite(text)

    def apply_to_text(self, text):
        if not isinstance(text, str):
            raise TypeError(f'expected str, got {text!r}')
        text = self._apply_to_text(text)
        if text is None:
            raise ValueError('self._apply_to_text() returned None, expected str')
        elif not isinstance(text, str):
            raise TypeError(f'self._apply_to_text() should return str, got {text!r}')
        return text

    def apply_to_lines(self, lines):
        if isinstance(lines, str):
            raise TypeError('expected lines, got a str')
        lines = self._apply_to_lines(lines)
        if lines is None:
            raise ValueError('should return lines, got None')
        elif isinstance(lines, str):
            raise TypeError('should return lines, got a str')
        for line in lines:
            # XXX Validate each line?
            yield line

    def apply_to_file(self, file, *, backup=None):
        self.apply_all_to_file([self], file, backup=backup)
#        backup = normalize_backup(backup)
#        if isinstance(file, str):
#            filename = file
#            if backup is not None:
#                backup(filename)
#            self._apply_to_filename(filename)
#        else:
#            if backup is not None:
#                raise NotImplementedError
#            self._apply_to_file(file)

    # implemented by subclasses

    def _apply_to_text(self, text):
        raise NotImplementedError

    def _apply_to_lines(self, lines):
        raise NotImplementedError


class TextBlobFix(TextFix):

    @classmethod
    def from_text_func(cls, textfix):
        self = cls()
        self._apply = textfix
        return self

    # TextFix implementation

    def _apply_to_text(self, text):
        return self._apply(text)

    def _apply_to_lines(self, lines):
        # XXX Supprt custom EOL?
        text = os.linesep.join(lines)
        text = self._apply(text)
        yield from text.splitlines()

    # implemented by subclasses and instances

    def _apply(self, text):
        raise NotImplementedError


class TextLinesFix(TextFix):

    @classmethod
    def from_lines_func(cls, textfix):
        self = cls()
        self._apply = textfix
        return self

    @classmethod
    def _apply_to_file_overwriter(cls, fixes, file):
        lines = file
        for fix in fixes:
            lines = fix.apply_to_lines(lines)
        file.overwritelines(lines)

    # TextFix implementation

    def _apply_to_text(self, text):
        # XXX Support custom EOL?
        lines = text.splitlines()
        lines = self._apply(lines)
        return os.linesep.join(lines)

    def _apply_to_lines(self, lines):
        yield from self._apply(lines)

    # implemented by subclasses and instances

    def _apply(self, text):
        raise NotImplementedError


class FileFix:

    @classmethod
    def _normalize_match(cls, match):
        if isinstance(match, str):
            # XXX Support other strings?
            return cls._match_from_filename(match)
        elif callable(match):
            return match
        # XXX regex, ...
        else:
            raise TypeError(f'unsupported matcher {match!r}')

    @classmethod
    def _match_from_filename(cls, match):
        # XXX glob, ...
        filename = match
        normfile = os.path.normpath(filename)
        if '*' in normfile:
            raise NotImplementedError(filename)
        elif os.path.isabs(normfile):
            raise NotImplementedError(filename)
        elif normfile.endswith(os.path.sep):
            raise NotImplementedError(filename)
        elif os.path.sep in normfile:
            raise NotImplementedError(filename)
        else:
            def match(filename):
                return os.path.basename(filename) == normfile
        return match

    @classmethod
    def _normalize_textfix(cls, textfix):
        if isinstance(textfix, TextFix):
            return textfix
        elif callable(textfix):
            return TextBlobFix.from_text_func(textfix)
        else:
            raise TypeError(f'unsupported textfix, got {textfix!r}')

    def __init__(self, match, textfix):
        cls = type(self)
        self._match = cls._normalize_match(match)
        self._textfix = cls._normalize_textfix(textfix)

    def __repr__(self):
        return f'{type(self).__name__}(match={self._match!r}, textfix={self._textfix!r})'

    def match(self, filename):
        return self._match(filename)

    def apply_to_text(self, text):
        return self._textfix.apply_to_text(text)


class FileFixes:

    def __init__(self):
        self._fixes = []

    def __repr__(self):
        return f'{type(self).__name__}(<{self._fixes}>)'

    def add(self, match, textfix):
        fix = FileFix(match, textfix)
        self._fixes.append(fix)
        return fix

    def register(self, filename):
        def decorator(func):
            self.add(filename, func)
            return func
        return decorator

    def match_one(self, filename, *, allowmultiple=False):
        if not isinstance(filename, str):
            raise TypeError(f'expected str, got {filename!r}')
        filename = os.path.normpath(filename)
        try:
            fix, *extra = self._match_all(filename)
        except ValueError:
            return None
        if not allowmultiple and extra:
            raise Exception(f'expected 1 match, got {len(extra)+1}')
        return fix

    def apply_to_file(self, filename, backup=None):
        # XXX Support limiting how many fixes to apply?
        filename = os.path.normpath(filename)
        backup = normalize_backup(backup)

        fixes = list(self._match_all(filename))
        if not fixes:
            return

        logger.debug(f'+ fixing ./{os.path.relpath(filename)}')
        TextBlobFix.apply_all_to_file(fixes, filename, backup=backup)

    # internal implementation

    def _match_all(self, filename):
        for fix in self._fixes:
            if fix.match(filename):
                yield fix


#######################################
# network

def parse_url(url):
    filename = None
    parsed = urlparse(url)
    if parsed.scheme == 'file':
        filename = url[7:]
        url = None
    elif not parsed.scheme:
        if parsed.netloc:
            url = f'https://{url}'
        else:
            filename = url
            url = None
    return url, filename


def resolve_download_url(baseurl, path, dummies=None):
    dummy = False
    if dummies is not None and path in dummies:
        url = f'<dummy: {path}>'
        dummy = True
    else:
        url = '/'.join([baseurl.rstrip('/'), path.lstrip('/')])
    return url, dummy


def resolve_download_target(target, path):
    basename = os.path.basename(target)
    if basename == '...':
        target = os.path.join(
            os.path.dirname(target),
            path.lstrip('/'),
        )
    elif not os.path.basename(target) or os.path.isdir(target):
        basename = path.rpartition('/')[-1]
        target = os.path.join(target, basename)
    return target


def download_path(baseurl, path, target, altpath=None, *,
                  makedirs=True,
                  dummies=None,
                  ):
    url, dummy = resolve_download_url(baseurl, path, dummies)
    if altpath:
        alturl, _ = resolve_download_url(baseurl, altpath)
        alttarget = resolve_download_target(target, altpath)
    else:
        alturl = None
        alttarget = None
    target = resolve_download_target(target, path)
    target, url = download(url, target,
                           alturl=alturl,
                           alttarget=alttarget,
                           dummy=dummy,
                           makedirs=makedirs)
    if alturl and url == alturl:
        path = altpath
    return target, url, path


def download(url, target=None, *,
             alturl=None,
             alttarget=None,
             dummy=None,
             makedirs=True,
             ):
    if not target:
        target = url.rpartition('/')[-1]
        assert target, repr(url)
    reltarget = os.path.relpath(target)
    minwidth = max(55, len(reltarget))
    if alturl and alttarget:
        relalttarget = os.path.relpath(alttarget)
        minwidth = max(minwidth, len(relalttarget))

    log = logger.debug
    log(f' + ./{reltarget:{minwidth}}  <- {url}')

    _maybe_make_parent_dir(target, makedirs)
    if dummy:
        with open(target, 'w'):
            pass
    else:
        assert not url.startswith('<dummy: '), repr(url)
        try:
            urlretrieve(url, target)
        except HTTPError:
            if not alturl:
                raise  # re-raise
            if alttarget:
                target = alttarget
                _maybe_make_parent_dir(target, makedirs)
            log('-- remote file not found, falling back to alt URL --')
            if alttarget:
                target = alttarget
                log(f' - ./{relalttarget:{minwidth}}  <- {url}')
            else:
                log(f'     {" "*minwidth}  <- {alturl}')
            url = alturl
            urlretrieve(url, target)

    return target, url


def read_path(baseurl, path, *, encoding=None):
    url, _ = resolve_download_url(baseurl, path)
    return read_url(url, encoding=encoding)


def read_url(url, *, encoding=None):
    if encoding == 'json':
        read = json.load
        encoding = None
    else:
        read = (lambda r: r.read())

    with urlopen(url) as resp:
        data = read(resp)

    if encoding:
        data = data.decode(encoding)
    return data
