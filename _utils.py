import glob
import os
import os.path
import shutil
import subprocess
from urllib.parse import urlparse
from urllib.request import urlretrieve
from urllib.error import HTTPError


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

    print(f' + ./{reltarget:{minwidth}}  <- {url}')

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
            print('-- remote file not found, falling back to alt URL --')
            if alttarget:
                target = alttarget
                print(f' - ./{relalttarget:{minwidth}}  <- {url}')
            else:
                print(f'     {" "*minwidth}  <- {alturl}')
            url = alturl
            urlretrieve(url, target)

    return target, url
