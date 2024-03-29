import datetime
import glob
import json
import logging
import os
import os.path
import shutil
import subprocess
import sys
from urllib.parse import urlparse
from urllib.request import urlretrieve, urlopen
from urllib.error import HTTPError


logger = logging.getLogger('_utils')


#######################################
# datetime

def normalize_timestamp(timestamp=None):
    if timestamp is None:
        return datetime.datetime.utcnow()
    else:
        raise NotImplementedError(repr(timestamp))


#######################################
# formatting

INDENT = ' ' * 4


def normalize_indent(indent):
    if isinstance(indent, str):
        return indent
    elif isinstance(indent, int):
        return ' ' * indent
    elif not indent:
        return ''
    else:
        raise TypeError(f'unsupported indent {indent!r}')


def normalize_depth(depth):
    if depth is None:
        return 0
    elif not isinstance(depth, int):
        raise TypeError(f'unsupported depth {depth!r}')
    elif depth < 0:
        return 0
    else:
        return depth


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

def normalize_filename(filename, relroot=None):
    if not filename:
        raise ValueError('missing filename')
    elif not isinstance(filename, str):
        orig = filename
        try:
            filename, *_ = filename
        except TypeError:
            raise TypeError(f'unsupported filename {filename!r}')
        if not filename or not isinstance(filename, str):
            raise ValueError(f'unsupported filename {orig!r}')
    if relroot is None:
        return filename
    elif not relroot:
        raise NotImplementedError(repr(filename))
    else:
        return os.path.relpath(filename, relroot)


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


#######################################
# network

def validate_path(path):
    if not path:
        raise ValueError('missing path')
    elif not isinstance(path, str):
        raise TypeError(f'expected str path, got {path!r}')
    elif not path.startswith('/'):
        raise ValueError('expected leading /, got {path!r}')


def normalize_url_str(url):
    if not url:
        raise ValueError('missing url')
    urlstr = str(url)
    if not urlstr:
        raise ValueError(f'invalid url {url!r}')
    # XXX Validate it further?
    return urlstr


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
