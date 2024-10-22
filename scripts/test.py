import os
import os.path
import re
import subprocess
import sys


SCRIPTS_DIR = os.path.dirname(__file__)
TEST_SCRIPT = os.path.join(SCRIPTS_DIR, 'test-installed.py')

DIST_REGEX = re.compile(r"""
    ^
    (?:
        (
#            .*\/ ( \w+ ) - ( \d+ \. \d+ \. \d+ ) \.tar\.gz
            .*/
            ( \w+ )  # <ar_name>
            -
            ( \d+ \. \d+ \. \d+ )  # <ar_version>
            (?:
                \.tar\.gz
                |
                .*.whl
             )
         )  # <archive>
        |
        (?:
            ( \w+)  # <name>
            :
            ( \d+ \. \d+ \. \d+ )  # <version>
         )
     )
    $
""", re.VERBOSE)


def resolve_dist(dist):
    m = DIST_REGEX.match(dist)
    if not m:
        raise ValueError(f'invalid dist {dist!r}')
    (archive, ar_name, ar_version,
     name, version,
     ) = m.groups()
    if archive:
        name = ar_name
        version = ar_version
    else:
        archive = f'dist/{name}-{version}.tar.gz'
    return archive, name, version


def run(cmd, *args, quiet=False):
    argv = [cmd, *args]
    if not quiet:
        print(f'+ {" ".join(argv)}')
    proc = subprocess.run(argv)
    return proc.returncode


def iter_venvs(venvsdir='.venvs'):
    if not venvsdir:
        venvsdir = '.venvs'
    major, minor, *_ = sys.version_info
    pyver = f'{major}.{minor}'

    baseroot = os.path.join(venvsdir, f'{pyver}')
    venvroot = baseroot

    count = 0
    while os.path.exists(venvroot):
        venvexe = os.path.join(venvroot, 'bin', 'python3')
        yield venvroot, venvexe, True
        count += 1
        venvroot = f'{baseroot}-{count}'

    venvexe = os.path.join(venvroot, 'bin', 'python3')
    yield venvroot, venvexe, False


def match_venv(venvroot, venvexe):
    with open(os.path.join(venvroot, 'pyvenv.cfg')) as infile:
        for line in infile:
            if line.startswith('executable = '):
                _, _, baseexe = line.strip().partition(' = ')
                break
        else:
            raise NotImplementedError(venvroot)
    return baseexe == os.path.realpath(sys.executable)


#############################
# the script

def parse_args(argv=sys.argv[1:], prog=sys.argv[0]):
    import argparse
    parser = argparse.ArgumentParser(prog=prog)

    parser.add_argument('dist')

    args = parser.parse_args(argv)
    ns = vars(args)

    return ns


def main(dist):
    target, pkgname, version = resolve_dist(dist)

    print(f'# testing {target}')
    print(f'# ({pkgname} - {version})')
    print()

    print('# finding venv')
    for venvroot, venvexe, exists in iter_venvs():
        if not exists:
            print('# creating venv')
            os.makedirs(os.path.dirname(venvroot), exist_ok=True)
            print(f'+ {sys.executable} -m venv {venvroot}')
            import venv
            venv.create(venvroot, with_pip=True)
            break
        elif match_venv(venvroot, venvexe):
            print('# found')
            run(venvexe, '-m', 'pip', 'install', '--upgrade', 'pip')
            break

    print()
    print(f'# installing {target}')

    run(venvexe, '-m', 'pip' ,'uninstall', '--yes', pkgname)
    rc = run(venvexe, '-m', 'pip' ,'install', target)
    if rc != 0:
        print('# failed!')
        return 1

    print()
    print(f'# running tests')

    if run(venvexe, TEST_SCRIPT) != 0:
        print('# failed!')
        return 1

    print('# passed!')
    return 0


if __name__ == '__main__':
    main_kwargs = parse_args()
    sys.exit(
        main(**main_kwargs))
