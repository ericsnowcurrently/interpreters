import re
import sys
from textwrap import dedent


#######################################
# fixers

def parse_ops(raw):
    if isinstance(raw, str):
        raw = [raw]
    for ops in raw:
        for opstr in ops.split(';'):
            opstr = opstr.strip()
            if not opstr:
                continue
            if opstr.startswith('#'):
                continue
            op, *args = opstr.split(':')
            yield op, args


class FixFailed(Exception):
    pass


class Fixer:

    def apply(self, text):
        raise NotImplementedError

    def apply_to_file(self, filename):
        with open(filename, encoding='utf-8') as infile:
            text = infile.read()
        text = self.apply(text)
        with open(filename, 'w', encoding='utf-8') as outfile:
            outfile.write(text)


class SwapName(Fixer):

    def __init__(self, orig, replace):
        self.orig = orig
        self.replace = replace
        self.regex = re.compile(rf'\b{self.orig}\b', re.MULTILINE)

    def apply(self, text):
        if not self.regex.search(text):
            raise FixFailed(f'name {self.orig!r} not found')
        fixed = self.regex.sub(self.replace, text)
        return fixed


class SwapBoundedLiteral(Fixer):

    def __init__(self, orig, replace):
        self.orig = orig
        self.replace = replace

    def apply(self, text):
        if self.orig not in text:
            raise FixFailed(f'literal {self.orig!r} not found')
        fixed = text.replace(self.orig, self.replace)
        return fixed


class RemoveMacro(Fixer):

    def __init__(self, name):
        self.name = name
        self.regex = re.compile(
                rf'^\s*#\s*define {self.name}\b.*$', re.MULTILINE)

    def apply(self, text):
        m = self.regex.search(text)
        if not m:
            raise FixFailed(f'macro {self.name!r} not found')
        if m[0].endswith('\\'):
            fixed = text[:m.start(0)]
            remainder = text[start(0):]
            while True:
                line, remainder = remainder.split('\n', 1)
                fixed += '\n'
                if not line.endswith('\\'):
                    break
            fixed += remainder
        else:
            fixed = self.regex.sub('', text)
        return fixed


class PyFixer(Fixer):

    def apply_to_file(self, filename):
        if not filename.endswith('.py'):
            raise FixFailed(f'expected a .py file, got {filename}')
        return super().apply_to_file(filename)


class AddFallbackImport(PyFixer):

    def __init__(self, modname, fallbackpkg):
        self.modname = modname
        self.fallbackpkg = fallbackpkg
        self.regex = re.compile(
                rf'^import {self.modname}(?: as (\w+))?$', re.MULTILINE)


    def apply(self, text):
        m = self.regex.search(text)
        if not m:
            raise FixFailed(f'"import {self.modname}" not found')
        alias, = m.groups()
        if not alias:
            alias = self.modname
        fixed = self.regex.sub(
            dedent(rf"""
                try:
                    \g<0>
                except ModuleNotFoundError:
                    from {self.fallbackpkg} \g<0>
                    import sys
                    assert '{self.modname}' not in sys.modules, {alias}
                    sys.modules['{self.modname}'] = {alias}
                """).strip(),
            text,
        )
        return fixed


FIXERS = {
    'swap-name': SwapName,
    'swap-bounded-literal': SwapBoundedLiteral,
    'remove-macro': RemoveMacro,
    'add-fallback-import': AddFallbackImport,
}


def get_fixer(op, args=()):
    try:
        new_fixer = FIXERS[op]
    except KeyError:
        raise ValueError(f'unsupported op {op!r}')
    return new_fixer(*args)


#######################################
# the script

def parse_args(argv=sys.argv[1:], prog=sys.argv[0]):
    import argparse
    parser = argparse.ArgumentParser(prog=prog)

    parser.add_argument('ops', metavar='OP', nargs='+')
    parser.add_argument('filename')

    args = parser.parse_args(argv)
    ns = vars(args)

    return ns


def main(filename, ops):
    for op, args in parse_ops(ops):
        fixer = get_fixer(op, args)
        #print(f'# {filename}: {op} {" ".join(args)}')
        fixer.apply_to_file(filename)


if __name__ == '__main__':
    kwargs = parse_args()
    try:
        main(**kwargs)
    except FixFailed as exc:
        sys.exit(f'ERROR: {exc}')
