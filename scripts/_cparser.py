from collections import namedtuple
import os
import re
import types


def _looks_like_file(text):
    raise NotImplementedError


def clean_lines(lines):
    """Remove comments and trailing whitespace."""
    for line in replace_comments(lines):
        yield line.rstrip()


#######################################
# C source lines

# This cannot inherit from StopIteration due to PEP 479.
class EndOfFile(EOFError):
    ...


def next_line(lines):
    try:
        return next(lines)
    except StopIteration:
        raise EndOfFile


class Location(namedtuple('Location', 'file lno chno')):

    @classmethod
    def from_raw(cls, raw):
        if isinstance(raw, cls):
            return raw
        elif not raw:
            raise ValueError('missing location')
        elif isinstance(raw, str):
            return cls.parse(raw)
        elif hasattr(raw, 'items'):
            raise TypeError(f'got unexpected mapping {raw!r}')
        else:
            try:
                return cls.from_values(*raw)
            except ValueError:
                raise ValueError(f'unsupported value {raw!r}')

    @classmethod
    def parse(cls, locstr):
        '''
        filename
        filename:lno
        filename:lno:chno
        filename:lno:chno:text
        filename:lno:text
        filename:text
        '''
        filename, _, text = locstr.partition(':')
        parts = []
        if text:
            part, _, remainder = text.partition(':')
            if part.isdigit():
                # lno
                parts.append(int(part))
                text = remainder
                if text:
                    part, _, remainder = text.partition(':')
                    if part.isdigit():
                        # chno
                        parts.append(int(part))
                        text = remainder
        if text.strip():
            parts.append(text)
        return cls.from_values(filename, *parts)

    @classmethod
    def from_values(cls, filename, lno=None, chno=None, text=None):
        if lno is not None:
            if isinstance(lno, str):
                if lno.isdigit():
                    lno = int(lno)
                elif chno is None and text is None:
                    text = lno
                    lno = None
        if chno is not None:
            if isinstance(chno, str):
                if chno.isdigit():
                    chno = int(chno)
                elif text is None:
                    text = chno
                    chno = None
        return cls(filename, lno, chno, text)

    def __new__(cls, file, lno=None, chno=None, text=None):
        if not lno and not isinstance(lno, int):
            lno = None
        if not chno and not isinstance(chno, int):
            chno = None
        self = super().__new__(cls, file or None, lno, chno)
        self._text = text if text and text.strip() else None
        return self

    def __init__(self, *args, **kwargs):
        if not self.file:
            raise ValueError('missing file')
        # XXX Validate self.file?

        if self.lno is not None:
            if not isinstance(self.lno, int):
                raise TypeError(f'expected int lno, got {self.lno!r}')
            if self.lno < 1:
                raise ValueError(f'expected positive lno, got {self.lno!r}')

        if self.chno is not None:
            if self.lno is None:
                raise ValueError('missing lno')
            if not isinstance(self.chno, int):
                raise TypeError(f'expected int chno, got {self.chno!r}')
            if self.chno < 1:
                raise ValueError(f'expected positive chno, got {self.chno!r}')

        if self.text is not None:
            if not isinstance(self.text, str):
                raise TypeError(f'text must be str, got {self.text!r}')

    @property
    def text(self):
        return self._text


class LinesInfo(namedtuple('LinesInfo', 'end endoffset lastoffset cont_end')):

    @classmethod
    def iter_lines(cls, lines, last_callback=None, *, regex=True):
        self, first, lines = cls.from_lines(lines, regex=regex)
        if self is None:
            assert first is None, repr(first)
            # XXX Warn that last_callback is ignored?
            return lines, None

        is_consistent = self._get_is_consistent()

        def iterate():
            line = first
            for nextline in lines:
                # This check will always succeed for the first line.
                assert is_consistent(line), (end, line)
                yield line
                line = nextline
            else:
                # We should not apply the check on the last line in the file.
                nextline = None
                yield line

                if last_callback:
                    if self.end and not line.endswith(self.end):
                        info = cls.from_end('')
                    else:
                        info = self
                    last_callback(info)

        return iterate(), self

    @classmethod
    def from_lines(cls, lines, *, regex=True):
        if isinstance(lines, str):
            raise NotImplementedError
        lines = iter(lines)
        try:
            line = next(lines)
        except StopIteration:
            line = None
        self = cls.from_first_line(line, regex=regex)
        return self, line, lines

    @classmethod
    def from_first_line(cls, line, *, regex=True):
        if line is None:
            return None
        if regex:
            end, = re.match(r'^.*?(\r?\n)?$', line).groups()
        else:
            if line.endswith('\r\n'):
                end = '\r\n'
            elif line.endswith('\n'):
                end = '\n'
            else:
                end = ''
        return cls.from_end(end)

    @classmethod
    def from_end(cls, end):
        if end:
            endoffset = -len(end)
        else:
            end = ''
            endoffset = 0
        return cls(
            end,
            endoffset or None,
            endoffset - 1,  # lastoffset
            '\\' + end,  # continuation_end
        )

    @property
    def continuation_end(self):
        return self.cont_end

    def _get_is_consistent(self):
        if self.end:
            def is_consistent(line, *, _end=self.end):
                return line.endswith(_end)
        else:
            def is_consistent(line):
                return not line.endswith('\n')
        return is_consistent

    def is_consistent(self, line):
        self.is_consistent = self._get_is_consistent()
        return self.is_consistent(line)


#def normalize_continuation(lines):
#    raise NotImplementedError
#    for line in lines:
#        yield re.sub(r'\(\s)', r'\1', line)


#def normalize_eol(lines, end=os.linesep):
#    raise NotImplementedError
#    assert end in ('', '\n', '\r\n'), repr(end)
#    lines = iter(lines)
#
#    # Inspect the first line.
#    try:
#        line = next(line)
#    except StopIteration:
#        return
#    if line.endswith('\n'):
#        first = '\n'
#    elif line.endswith('\r\n'):
#        first = '\r\n'
#    else:
#        first = ''
#
#    # A helper used only in (hot) asserts.
#    if __debug__:
#        def is_consistent(line):
#            if first:
#                return line.endswith(first)
#            else:
#                return not line.endswith('\n')
#
#    # Finish the first line and
#    # handle the remaining lines.
#    if first == end:
#        yield line
#        for line in lines:
#            assert is_consistent(line), (first, line)
#            yield line
#    elif first:
#        firstoffset = -len(first)
#        if end:
#            yield line[:firstoffset] + end
#            for line in lines:
#                assert is_consistent(line), (first, line)
#                yield line[:firstoffset] + end
#        else:
#            yield line[:firstoffset]
#            for line in lines:
#                assert is_consistent(line), (first, line)
#                yield line[:firstoffset]
#    elif end:
#        yield line + end
#        for line in lines:
#            assert is_consistent(line), (first, line)
#            yield line + end
#    else:
#        raise NotImplementedError('not reachable')


#######################################
# C comments

'''
// ...
// ... \

... // ...
... // ... \

/* ... */
/* ...
 ... */

... /* ... */
... /* ...

/* ... */ ...
... */ ...

... /* ... */ ...
 ... */ ...
'''


COMMENTS_RE = re.compile(r'''
    ^
    (
        [^/]*
        (?:
            [/] [^/*]
            [^/]*
         )*
     )  # <before>
    (?:
        # multi-line comments
        (?:
            (
                [/][*]
                (
                    [^*]*
                    (?:
                        [*]+ (?= [^/] )
                        [^*]*
                     )*
                 )  # <multi_body>
                ( [*][/] )?  # <multi_end>
             )  # <multi>
            ( .* )  # <after>
         )
        |
        # single-line comments
        (?:
            (
                [/][/]
                (
                    # Everything up to the line continuation, if any.
                    [^\\]*
                    (?:
                        [\\] .
                        [^\\]*
                     )*
                 )  # <single_body>
             )  # <single>
            (?:
                ( [\\] )  # <continuation>
                #(?: \n | \r\n )?
             )?
         )
     )
    $
''', re.VERBOSE)


def _replace_comments_regex(lines, clear_cont=False):
    end = endoffset = lastoffset = cont_end = None
    def last_callback(info):
        nonlocal end, endoffset, lastoffset, cont_end
        end, endoffset, lastoffset, cont_end = info
    lines, info = LinesInfo.iter_lines(lines, last_callback)

    line = next_line(lines)
    end, endoffset, lastoffset, cont_end = info
    while True:
        comment = None
        m = COMMENTS_RE.match(line[:endoffset])
        if m:
            (before,
             multi, multi_body, multi_end, after,
             single, single_body, continuation,
             ) = m.groups(default='')
            if multi:
                orig = line
                line = f'{before}{" "*len(multi)}{after}{end}'
                if multi_end:
                    continue
                else:
                    comment = 'multi'
            elif single:
                if continuation:
                    _end = end if clear_cont else cont_end
                    line = f'{before}{" "*len(single)}{_end}'
                    comment = 'single'
                else:
                    line = f'{before}{" "*len(single)}{end}'
            else:
                raise NotImplementedError(m.groups())
        yield line

        line = next_line(lines)

        if comment == 'single':
            while line and line[lastoffset] == '\\':
                _end = end if clear_cont else cont_end
                yield ' ' * len(line[:lastoffset]) + _end
                line = next_line(lines)
            comment = None
            yield ' ' * len(line[:endoffset]) + end
        elif comment == 'multi':
            while not (m := re.match(r'^([^*]*[*][/])(.*)$', line)):
                yield ' ' * len(line[:endoffset]) + end
                line = next_line(lines)
            comment = None
            multi, after = m.groups()
            line = f'{" "*len(multi)}{after}'
        elif not comment:
            pass
        else:
            raise NotImplementedError(repr(comment))


def _replace_comments_by_char(lines, clear_cont=False):
    ...
#    lines = iter(lines)
#    for line in lines:
#        chars = iter(enumerate(line))
#        for i, ch in chars:
#            if ch == '/':
#                try:
#                    ch = next(line)
#    comment = None
#    for line in lines:
#        if comment == 'multi
#        for ch in line:
#
#        chars = iter(line)
#        for ch in chars:
#            if ch == '/':
#                ch = next(
#                if ch =
#            if ch == '\\':
#                ...
#
#
#        for ch in chars:
#
#        try:
#            ch = next(chars)
#        e


def _replace_comments_partition(lines, clear_cont=False):
    end = endoffset = lastoffset = cont_end = None
    def last_callback(info):
        nonlocal end, endoffset, lastoffset, cont_end
        end, endoffset, lastoffset, cont_end = info
    #lines, info = LinesInfo.iter_lines(lines, last_callback)
    lines, info = LinesInfo.iter_lines(lines, last_callback, regex=False)

    line = next_line(lines)
    end, endoffset, lastoffset, cont_end = info
    while True:
        before, sep, after = line.partition('//')
        if sep and '/*' not in before:
            if after and after[lastoffset] == '\\':
                _end = end if clear_cont else cont_end
                yield f'{before}  {" "*len(after[:lastoffset])}{_end}'
                while True:
                    line = next_line(lines)
                    if line[lastoffset] != '\\':
                        break
                    yield f'{" "*len(line[:lastoffset])}{_end}'
                line = f'{" "*len(line[:endoffset])}{end}'
            else:
                line = f'{before}  {" "*len(after[:endoffset])}{end}'
        else:
            before, sep, body = line.partition('/*')
            if sep:
                body, sep, after = body.partition('*/')
                if sep:
                    line = f'{before}  {" "*len(body)}  {after}'
                else:
                    yield f'{before}  {" "*len(body[:endoffset])}{end}'
                    while True:
                        line = next_line(lines)
                        body, sep, after = line.partition('*/')
                        if sep:
                            break
                        yield f'{" "*len(line[:endoffset])}{end}'
                    line = f'{" "*len(line[:endoffset])}{end}'
                continue
        yield line
        line = next_line(lines)


def replace_comments(lines, *, clear_continuation=True):
    try:
        yield from _replace_comments_regex(lines, clear_continuation)
        #yield from _replace_comments_by_char(lines)
        #yield from _replace_comments_partition(lines)
    except EndOfFile:
        return


#######################################
# C preprocessor

class PreprocessorDirective(namedtuple('PreprocessorDirective',
                                       'kind name args value')):

    KINDS = {
        'include',
        'ifdef',
        'ifndef',
        'if',
        'elif',
        'else',
        'endif',
        'define',
        'undef',
        'error',
    }

    @classmethod
    def parse_kinds(cls, kinds):
        if kinds is None:
            return None
        elif not kinds:
            return None if isinstance(kinds, str) else ()

        if isinstance(kinds, str):
            _kinds = kinds
            kinds = kinds.replace(',', ' ').split()
        else:
            _kinds = ','.join(kinds)

        kinds = set(kinds)
        if kinds - cls.KINDS:
            unsupported = kinds - cls.KINDS
            kinds = ','.join(unsupported)
            if len(unsupported) == 1:
                raise ValueError(f'unsupported kind {kinds} in {_kinds!r}')
            else:
                kinds = ','.join(unsupported)
                raise ValueError(f'unsupported kinds {kinds} in {_kinds!r}')
        return kinds

    @classmethod
    def _validate(cls, directive, lines):
        if directive.kind == 'include':
            if len(lines) > 1:
                raise ValueError(f'include directives should only have one line, got {lines}')

    REGEX = re.compile(r'''
        ^
        \s*
        [#]
        \s*
        (?:
            (?:
                ( define )  # <define>
                \s+
                ( \w+ )  # <def_name>
                (
                    [(] [^)]* [)]
                 )?  # <def_args>
#\s+
#( .* )  # <def_body>
#/s*
                (?:
                    \s+
                    (
                        (?: \S+ \s+ )* \S* [^\s\\]
                     )  # <def_body>
                 )?
                \s*
                (?:
                    ( \\ )  # <def_continuation>
                    (?: \r? \n )?
                 )?
             )
            |
            (?:
                ( undef )  # <undef>
                \s+
                ( \w+ )  # <undef_name>
             )
            |
            (?:
                ( include )  # <include>
                \s+
                (?:
                    (?:
                        < \s*
                        ( \S+)  # <incl_system>
                        \s*
                        >
                     )
                    |
                    (?:
                        " \s*
                        ( \S+)  # <incl_user>
                        \s*
                        "
                     )
                    |
                    (?:
                        ( \S+ (?: \s+ \S+)* )  # <incl_other>
                     )
                 )
                \s*
             )
            |
            (?:
                ( ifn?def )  # <ifdef>
                \s+
                ( \w+ )  # <ifdef_name>
                \s*
             )
            |
            (?:
                ( (?: el )? if )  # <if>
                \s+
                (
                        (?: \S+ \s+ )* \S* [^\s\\]
                 )  # <if_cond>
                \s*
                (?:
                    ( \\ )  # <if_continuation>
                    (?: \r? \n )?
                 )?
             )
            |
            (?:
                ( else )  # <else>
                \s*
             )
            |
            (?:
                ( endif )  # <endif>
                \s*
             )
            |
            (?:
                ( error )  # <error>
                \s+
                ( .*? )  # <error_msg>
                \s*
             )
            |
            (?:
                ( \S+ (?: \s+ \S+ )* )  # <other>
                \s*
             )
         )
        $
    ''', re.VERBOSE)

    @classmethod
    def _iter_lines(cls, lines):
        # We expect "clean" lines here.
        lines = iter(lines)
        for lno, line in enumerate(lines, 1):
            m = cls.REGEX.match(line)
            if not m:
                yield line, None, None
                continue
            (kind, name, args, value, continuation,
             ) = cls._handle_match(m, line)
            dlines = [line]
            if continuation:
                body = [value]
                for line in lines:
                    dlines.append(line)
                    if not line.endswith('\\'):
                        value = f'{value} {line}'
                        body.append(line)
                        break
                    line = line[:-1].rstrip()
                    value = f'{value} {line}'
                    body.append(line)
                self._body = tuple(body)
            elif kind == 'define':
                self._body = (value,)
            self = cls(kind, name, args, value)
            self._lno = lno
            self._lines = dlines
            yield None, self, dlines

    @classmethod
    def _handle_match(cls, m, line):
        continuation = False

        (define, def_name, def_args, def_body, def_continuation,
         undef, undef_name,
         include, incl_system, incl_user, incl_other,
         ifdef, ifdef_name,
         ifdirective, if_cond, if_continuation,
         elsedirective,
         endifdirective,
         error, error_msg,
         other,
         ) = m.groups(default='')
        if define:
            kind = 'define'
            name = def_name
            if def_args:
                args = tuple(def_args.replace(',', ' ').split())
            else:
#                assert not def_continuation, repr(line)
                args = None
            value = def_body if def_body else None
            if def_continuation:
                continuation = True
        elif undef:
            kind = 'undef'
            name = undef_name
            args = None
            value = None
        elif include:
            kind = 'include'
            name = None
            args = None
            if incl_system:
                value = ('system', incl_system)
            elif incl_user:
                value = ('user', incl_user)
            elif incl_other:
                raise NotImplementedError(repr(incl_other))
            else:
                raise NotImplementedError(m.groups())
        elif ifdef:
            kind = ifdef
            name = None
            args = None
            value = ifdef_name
        elif ifdirective:
            kind = ifdirective
            name = None
            args = None
            value = if_cond
            if if_continuation:
#                raise NotImplementedError(repr(line))
                continuation = True
        elif elsedirective:
            kind = 'else'
            name = None
            args = None
            value = None
        elif endifdirective:
            kind = 'endif'
            name = None
            args = None
            value = None
        elif error:
            kind = 'error'
            name = None 
            args = None
            value = error_msg
        elif other:
            raise NotImplementedError(repr(line))
        else:
            raise NotImplementedError(m.groups())

        return kind, name, args, value, continuation

    @classmethod
    def from_lines(cls, lines, *, clean=True):
        """Return the next directive from the given lines.

        If "clean" is true, the lines will be cleaned.
        Otherwise, they are expected to be clean already
        (no comments, no trailing whitespace).
        """
        if clean:
            lines = clean_lines(lines)
        for line, directive, _ in cls._iter_lines(lines):
            if line is None:
                assert type(directive) is cls, repr(directive)
                return directive
        else:
            return None

    @classmethod
    def iter_from_lines(cls, lines, *, clean=True):
        """Yield each directive found in the given lines.

        If "clean" is true, the lines will be cleaned.
        Otherwise, they are expected to be clean already
        (no comments, no trailing whitespace).
        """
        if clean:
            lines = clean_lines(lines)
        for _, directive, _ in cls._iter_lines(lines):
            if directive is not None:
                yield directive

    @classmethod
    def iter_lines(cls, lines, on_match, *, clean=True):
        """Yield the sources lines, with each directive triggering on_match().

        args:

        * lines - the source lines to walk
        * on_match - a function that is called for each encountered directive;
          it is passed the directive object and the source corresponding lines
        * clean - (optional) whether or not the lines should be cleaned
          before replacing.  If false, the lines are expected to be
          clean (no comments, no trailing whitespace).
        """
        assert callable(on_match), repr(on_match)
        lines = iter(lines)
        if clean:
            lines = clean_lines(lines)
        for line, directive, dlines in cls._iter_lines(lines):
            if line is None:
                assert type(directive) is cls, repr(directive)
                yield from cls._handle_on_match(on_match, directive, dlines)
            else:
                yield line

    @classmethod
    def _handle_on_match(cls, on_match, directive, lines):
        if lines is None:
            lines = directive._lines
        numlines = len(lines)
        assert numlines > 0

        res = on_match(directive, lines)
        if res is None:
            return lines
        d, l = res

        if l is not None:
            lines = list(l)
            if len(lines) != numlines:
                raise Exception(f'expected {numlines} lines, got {lines})')
        elif d is None or d is directive:
            pass
        else:
            # XXX Verify any transformations are okay (e.g. changed kind).
            cls._validate(d, lines)
            lines = d.lines
            if len(lines) != numlines:
                raise Exception(f'expected {numlines} lines, got {lines})')
        return lines

    @classmethod
    def normalize_lines(cls, lines, on_match=None, kinds=None, *,
                        clean=True):
        """Yield the source lines with directive formatting normalized.

        Leading and unnecessary intermediate spaces are removed.

        args:

        * lines - the source lines to modify
        * on_match - (optional) a function that is called for each
          directive; it is passed the directive object and the
          replacement lines
        * kinds - (optional) only these directive kinds are normalized
        * clean - (optional) whether or not the lines should be cleaned
          before replacing.  If false, the lines are expected to be
          clean (no comments, no trailing whitespace).
        """
        kinds = cls.parse_kinds(kinds)

        def _on_match(directive, lines):
            if not kinds or directive.kind in kinds:
                assert directive._lines == lines, (directive._lines, lines)
                lines = directive.text.splitlines()
            if on_match is not None:
                return on_match(directive, lines)
            else:
                return directive, lines
            
        yield from cls.iter_lines(lines, _on_match, clean=ckean)

    @classmethod
    def replace_lines(cls, lines, on_match=None, *,
                      keep=None,
                      clean=True,
                      ):
        """Yield the source lines with directives replaced by spaces.

        args:

        * lines - the source lines to modify
        * on_match - (optional) a function that is called for each
          removed directive; it is passed the directive object and
          the replacement lines
        * keep - (optional) a list (or a comma-separated string) of the
          directive kinds that should not be replaced
        * clean - (optional) whether or not the lines should be cleaned
          before replacing.  If false, the lines are expected to be
          clean (no comments, no trailing whitespace).
        """
        # XXX Deal with splits due to #else branching.

        keep = cls.parse_kinds(keep)

        def _on_match(directive, lines):
            if not keep or directive.kind not in keep:
                lines = [' ' * len(l) for l in lines]
            if on_match is not None:
                return on_match(directive, lines)
            else:
                return directive, lines

        yield from cls.iter_lines(lines, _on_match, clean=clean)

    _lines = None
    _lno = None

    def __str__(self):
        return self.text

    @property
    def lines(self):
        if self._lines is None:
            text = d.text
            d._lines = text.splitlines()
        return list(d._lines)

    @property
    def lno(self):
        return self._lno

    @property
    def raw(self):
        try:
            return self._raw
        except AttributeError:
            raise NotImplementedError
            ...
            return self._raw

    @property
    def text(self):
        try:
            return self._text
        except AttributeError:
            lines = self._normalize()
            self._text = os.linesep.join(lines)
            return self._text

    def _normalize(self):
        if self.kind == 'define':
            assert self.name is not None, repr(self)
            if not self.args:
                if self.value:
                    assert '\n' not in self.value, repr(self)
                    lines = [f'#define {self.name} {self.value}']
                    if self._lines and len(self._lines) > 1:
                        lines += [''] * (len(self._lines) - 1)
                    # XXX continuations?
                    return lines
                else:
                    return [f'#define {self.name}']
            line = f'#define {self.name}({",".join(self.args)})'
            if not self.value:
                return [line]
            lines = [line + ' \\']
            if not self._lines or len(self._lines == 1):
                lines.append(f'    {self.value}')
            else:
                for line in self._body:
                    # XXX Fix up leading indent.
                    lines.append(f'{line.rstrip()} \\')
                lines[-1] = line
            return lines
        elif self.kind == 'undef':
            return [f'#undef {self.name}']
        elif self.kind == 'include':
            assert self.name is None, repr(self)
            assert self.args is None, repr(self)
            subkind, value = self.value
            if subkind == 'system':
                return [f'#include <{value}>']
            elif subkind == 'user':
                return [f'#include "{value}"']
            else:
                raise NotImplementedError(repr(self))
        elif self.kind == 'ifdef':
            assert self.name is None, repr(self)
            assert self.args is None, repr(self)
            return [f'#ifdef {self.value}']
        elif self.kind == 'ifndef':
            assert self.name is None, repr(self)
            assert self.args is None, repr(self)
            return [f'#ifndef {self.value}']
        elif self.kind == 'if':
            assert self.name is None, repr(self)
            assert self.args is None, repr(self)
            return [f'#if {self.value}']
        elif self.kind == 'elif':
            assert self.name is None, repr(self)
            assert self.args is None, repr(self)
            return [f'#elif {self.value}']
        elif self.kind == 'else':
            assert self.name is None, repr(self)
            assert self.args is None, repr(self)
            return ['#else']
        elif self.kind == 'endif':
            assert self.name is None, repr(self)
            assert self.args is None, repr(self)
            assert self.value is None, repr(self)
            return ['#endif']
        elif self.kind == 'error':
            return [f'#error {self.value}']
        else:
            raise NotImplementedError(repr(self))


#######################################
# C strings

def replace_strings(lines, *, clean=True, keepincludes=True):
    """Replace string literatls with empty strings.

    The removed text is filled with spaces after the close quote.
    """
    if clean:
        lines = clean_lines(lines)
    try:
        for line in _replace_strings_partition(lines, keepincludes):
            yield line
        #yield from _replace_strings_partition(lines, keepincludes)
    except EndOfFile:
        return


def _replace_strings_partition(lines, keepincludes):
    def split_literals(line):
        parts = []
        size = len(line)
        i = start = 0
        while i < size:
            ch = line[i]
            if ch == '"':
                parts.append(line[start:i])
                start = i + 1
            elif ch == "'":
                # Move to the closing single-quote.
                if i + 1 < size and line[i+1] == '\\':
                    i += 2
                else:
                    i += 1
            elif ch == '\\':
                i += 1
            i += 1
        parts.append(line[start:])
        return parts

    lines = iter(lines)
    for line in lines:
        parts = split_literals(line)
        assert parts, repr(line)
        if len(parts) == 1:
            yield line
            continue

        if ( keepincludes and line.lstrip().startswith('#')
                and line.replace(' ', '').startswith('#include"')):
            yield line
            continue

        if len(parts) % 2:
            line = ''
            for i in range(len(parts)):
                if i % 2:
                    line = f'{line}"{" "*len(parts[i])}"'
                else:
                    line += parts[i]
            yield line
            continue

        # a multi-line string literal
        line = ''
        for i in range(len(parts)-1):
            if i % 2:
                line = f'{line}"{" "*len(parts[i])}"'
            else:
                line += parts[i]
        yield f'{line}"{" "*len(parts[-1])}'

        for line in lines:
            parts = split_literals(line)
            if len(parts) > 1:
                assert len(parts) % 2 == 0, (parts, line)
                line = f'{" "*len(parts[0])}"'
                for i in range(1, len(parts)):
                    if i % 2:
                        line += parts[i]
                    else:
                        line = f'{line}"{" "*len(parts[i])}"'
                yield line
                break
            yield f'{" "*len(line)}'


#######################################
# declarations and function definitions

def iter_compiler_refs(lines, filename, load_include=None):
    seen = set()
    yield from _iter_compiler_refs(lines, filename, seen, load_include)


def _iter_compiler_refs(lines, filename, seen_includes, load_include=None):
    for line in lines:
        ref = ...
        yield ref

        if ref.kind == 'include-user':
            if load_include is not None and ref.name not in seen_includes:
                seen_includes.add(ref.name)
                inner_lines, inner_filename = load_include(ref.name)
                with inner_lines:
                    yield from _iter_compiler_refs(inner_lines, inner_filename,
                                                   seen_includes, load_include)
        elif ref.kind == 'include-system':
            if ref.name not in seen_includes:
                seen_includes.add(ref.name)
                yield from _expand_system_include(ref.name)
        elif ref.topkind == 'include':
            raise NotImplementedError(ref)


def _expand_system_include(include):
    # XXX ...
    return
    yield None

        

class CCompilerRefs:

    def __init__(self):
        # name -> (loc, context, inline, deps)
        self.macros = {}
        self.constants = {}
        self.structs = {}
        self.enums = {}
        self.enum_values = {}
        self.unions = {}
        self.functions = {}
        self.variables = {}

    # XXX Resolve individual struct/union fields?

        
class CCompilerRef(namedtuple('CCompilerRef', 'kind name loc text')):

    KINDS = {
#        # CInclude
#        'include-system',
#        'include-user',
        # CDefine
        'define-macro',
        'define-constant',
        # CDeclaration
        'typedef',
        'struct',
        'enum',
        'union',
        'symbol-function',
        'symbol-variable',
    }
    KIND_ALIASES = {
        # CDefine
        'macro': 'define-macro',
        'constant': 'define-constant',
        # CDeclaration
        'function': 'symbol-function',
        'variable': 'symbol-variable',
    }

    @classmethod
    def from_values(cls, kind, name, loc=None, text=None):
        kind = cls.normalize_kind(kind)
        cls._validate_name(name)
        if text and text.strip():
            cls._validate_text(text)
        else:
            text = None
        if loc:
            loc, text = cls.normalize_loc(loc, text)
        else:
            loc = None
        self = cls.__new__(cls, kind, name, loc, text)
        return self

    @classmethod
    def normalize_kind(cls, kind):
        if not kind:
            raise ValueError('missing kind')
        for k in cls.KINDS:
            if kind == k:
                return k
        else:
            try:
                return cls.KIND_ALIASES[kind]
            except KeyError:
                raise ValueError(f'unsupported kind {kind!r}')

    @classmethod
    def normalize_loc(cls, loc, text=None):
        if not loc:
            raise ValueError('missing loc')
        elif not isinstance(loc, Location):
            loc = Location.from_raw(loc)

        if text is None:
            text = loc.text
        elif loc.text is not None:
            # XXX Check for a mismatch.
            pass
        # XXX Make sure loc.lno and loc.chno are correct?

        return loc, text

    @classmethod
    def _validate_kind(cls, kind):
        if not kind:
            raise ValueError('missing kind')
        elif not any(kind is k for k in cls.KINDS):
            raise ValueError(f'unsupported kind {kind!r}')

    @classmethod
    def _validate_name(cls, name):
        if not name:
            raise ValueError('missing name')
        # XXX Validate name.

    @classmethod
    def _validate_loc(cls, loc):
        if not loc:
            raise ValueError('missing loc')
        elif not isinstance(loc, Location):
            raise TypeError(f'unsupported loc {loc!r}')

    @classmethod
    def _validate_text(cls, text):
        if not text:
            raise ValueError('missing text')
        elif isinstance(text, str):
            if not text.strip():
                raise ValueError('missing text')

    def __new__(cls, kind, name, loc=None, text=None):
        if cls is CCompilerRef:
            for subclass in (
#                CInclude,
                CDefine,
                CDeclaration,
            ):
                if kind in subclass.KINDS:
                    return subclass.__new__(cls, kind, name, loc, text)
        self = super().__new__(
            cls,
            kind=kind or None,
            name=name or None,
            loc=loc or None,
            text=text or None,
        )
        return self

    def __init__(self, *args, **kwargs):
        cls = type(self)
        cls._validate_kind(self.kind)
        cls._validate_name(self.name)
        if self.loc is not None:
            cls._validate_loc(self.loc)
        if self.text is not None:
            cls._validate_text(self.text)

    @property
    def deps(self):
        try:
            return list(self._deps)
        except AttributeError:
            raise NotImplementedError
            self._deps = ...
            return list(self._deps)

    @property
    def topkind(self):
        top, _, _ = self.kind.partition('-')
        return top

    @property
    def subkind(self):
        _, _, sub = self.kind.partition('-')
        return sub or None

    def match_kind(self, kind):
        if self.kind == kind:
            return True
        elif self.topkind == kind:
            return True
        elif self.kind == self.KIND_ALIASES.get(kind):
            return True
        else:
            return False


#class CInclude(CCompilerRef):
#
#    KINDS = {
#        'include-system',
#        'include-user',
#    }
#    KIND_ALIASES = {}


class CDefine(CCompilerRef):

    KINDS = {
        'define-macro',
        'define-constant',
    }
    KIND_ALIASES = {
        'macro': 'define-macro',
        'constant': 'define-constant',
    }


class CDeclaration(CCompilerRef):

    KINDS = {
        'typedef',
        'struct',
        'enum',
        'union',
        'symbol-function',
        'symbol-variable',
    }
    KIND_ALIASES = {
        'function': 'symbol-function',
        'variable': 'symbol-variable',
    }


def iter_definitions(lines, filename=None):
    raise NotImplementedError
    for lno, line in enumerate(lines, 1):
        ...
        yield name, kind, Location(filename, lno, text=text)


USED_RE = re.compile(r'''
    ^
    \s*
    (?:
        # include:
        (
            [#] \s* include \s+
            (?:
                (?:
                    <
                    ( \S+)  # <incl_system>
                    >
                 )
                |
                (?:
                    "
                    ( \S+)  # <incl_user>
                    "
                 )
                |
                (?:
                    ( \S+ (?: \s+ \S+)* )  # <incl_other>
                 )
             )
            \s*
         )  # <include>
        |
        # typedef:
        (
            typedef \s+
            (?:
                (?: 
                    ( struct | enum | union )  # <tp_inline_kind>
                    (?:
                        \s+
                        ( \w+ )  # <tp_inline_name>
                     )?
                    \s*
                    [{]
                    \s*
                    (?:
                        ( [^\s}]+ (?: \s+ [^\s}]+ )* )?  # <tp_inline_body>
                        \s*
                     )?
                    (?:
                        [}]
                        \s*
                        ( \w+ )  # <tp_inline_close>
                        \s*
                        ;
                        \s*
                     )?
                 )
                |
                (?:
                    (?:
                        (?:
                            (?:
                                (?:
                                    ( struct | enum | union )  # <tp_compound_kind>
                                    \s*
                                    ( \w+ )  # <tp_compound_name>
                                 )
                                |
                                ( \w+ )  # <tp_simple_alias>
                                |
                                ( \S+ (?: \s+ \S+ )* )  # tp_simple_other
                             )
                            \s+
                            ( \w+ )  # <tp_name>
                         )
                        |
                        ( \S+ (?: \s+ \S+ )* )  # <tp_other>
                            
                         )
                     )
                    \s*
                    ;
                    \s*
                 )
             )
         )  # <typedef>
        # struct:
        # union:
        # enum:
        # typedef:
        # name:
        # called:
        # decl:
    $
''', re.VERBOSE)


KINDS = {
    'include',
    'typedef',
    'struct-decl',
}


def iter_used(lines, filename=None):
    filename = f'{filename}:' if filename else ''
#    decls = {}

    directives = []
    def on_match_directive(directive, dlines):
        directives.append(directive)
        return directive, dlines

    lines = clean_lines(lines)
    lines = PreprocessorDirective.replace_lines(lines, clean=False)
    #lines = PreprocessorDirective.normalize_lines(lines, on_match_directive, clean=False)
    #lines = PreprocessorDirective.replace_lines(lines, keep='include', clean=False)
    lines = replace_strings(lines, clean=False)

    for lno, line in enumerate(lines):
        assert not line.endswith('\\'), (lno, line)
        m = USED_RE.match(line)
        if not m:
            if line.startswith('#include'):
                raise NotImplementedError(f'{filename}{lno}: {line.rstrip()!r}')
            elif 'typedef' in line:
                raise NotImplementedError(f'{filename}{lno}: {line.rstrip()!r}')
            continue

        (include, incl_system, incl_user, incl_other,
         typedef,
            tp_inline_kind, tp_inline_name, tp_inline_body, tp_inline_close,
            tp_compound_kind, tp_compund_name, tp_simple_alias, tp_simple_other, tp_name,
            tp_other,
         ) = m.groups()
        if include:
            if incl_system:
                kind = 'include-system'
                name = incl_system
            elif incl_user:
                kind = 'include-user'
                name = incl_user
            else:
                raise NotImplementedError(f'{filename}{lno}: {incl_other!r} ({line.rstrip()})')
            if not include.endswith('.h'):
                raise NotImplementedError(f'{filename}{lno}: {include!r} ({line.rstrip()})')
            yield CDependency.from_values(kind, name, parent)
        elif typedef:
            if tp_inline_kind:
                if tp_inline_name:
                    kind = tp_inline_kind
                    name = tp_inline_name
                    yield CDependency.from_values(kind, name, parent)
#                    yield (tp_inline_name, f'{tp_inline_kind}-decl')
                else:
                    raise NotImplementedError
                    yield (None, 'typedef')
                if tp_inline_body:
                    # XXX Analyze it.
                    ...
                if tp_inline_close:
                    raise NotImplementedError
                    yield (tp_inline_close, 'typedef')
            elif tp_name:
                ...
            elif tp_other:
                ...
            else:
                raise NotImplementedError(m.groups())
        else:
            raise NotImplementedError(m.groups())


#######################################
# C dependencies

def analyze_dependencies(lines, filename=None, implied=None, *,
                         download_include=None,
                         recurse=False,
                         ):
    if download_include is not None:
        if not callable(download_include):
            raise TypeError(f'download include must be callable, got {download_include!r}')
    elif recurse:
        raise ValueError('cannot recurse without download_include()')

    if implied:
        for dep in implied:
            yield dep
            if dep.kind == 'include-user' and download_include is not None:
                depfile = download_include(dep.name)
                if recurse:
                    with open(depfile) as infile:
                        yield from analyze_dependencies(
                            infile, depfile,
                            download_include=download_include,
                            recurse=recurse,
                        )

    raise NotImplementedError
    for line in lines:
        ...


class CDependency(namedtuple('CDependency', 'ref context')):

    @classmethod
    def from_location(cls, kind, name, loc, defined=None):
        kind = cls.normalize_kind(kind)
        cls._validate_name(name)
        parent = Location.from_raw(loc)
        if defined.strip():
            defined = cls.normalize_defined(defined, parent)
        else:
            defined = None
        self = cls.__new__(cls, kind, name, parent, defined)
        return self

    @classmethod
    def from_values(cls, kind, name, parent=None, defined=None):
        kind = cls.normalize_kind(kind)
        cls._validate_name(name)
        if parent.strip():
            parent = cls.normalize_parent(parent)
        else:
            parent = None
        if defined.strip():
            defined = cls.normalize_defined(defined, parent)
        else:
            defined = None
        self = cls.__new__(cls, kind, name, parent, defined)
        return self

    @classmethod
    def normalize_kind(cls, kind):
        if not kind:
            raise ValueError('missing kind')
        for k in cls.KINDS:
            if kind == k:
                return k
        else:
            try:
                return cls.KIND_ALIASES[kind]
            except KeyError:
                raise ValueError(f'unsupported kind {kind!r}')

    @classmethod
    def normalize_parent(cls, parent):
        if not parent:
            raise ValueError('missing parent')
        elif isinstance(parent, CDependency):
            return parent
        else:
            return Location.from_raw(parent)

    @classmethod
    def normalize_defined(cls, defined, parent=None):
        if not defined:
            raise ValueError('missing defined')
        elif isinstance(defined, Location):
            return defined
        elif isinstance(defined, str):
            filename, _, _ = defined.partition(':')
            if _looks_like_file(filename):
                return Location.from_raw(defined)
            while parent is not None:
                if isinstance(parent, Location):
                    return Location(parent.file, text=defined)
                assert isinstance(parent, CDependency), repr(parent)
                parent = parent.parent
            else:
                return defined
                #return Location('???', text=defined)
        else:
            raise TypeError(f'unsupported defined {defined!r}')

    @classmethod
    def _validate_kind(cls, kind):
        if not kind:
            raise ValueError('missing kind')
        elif not any(kind is k for k in cls.KINDS):
            raise ValueError(f'unsupported kind {kind!r}')

    @classmethod
    def _validate_name(cls, name):
        if not name:
            raise ValueError('missing name')
        # XXX Validate name.

    @classmethod
    def _validate_parent(cls, parent):
        if not parent:
            raise ValueError('missing parent')
        elif not isinstance(parent, (cls, Location)):
            raise TypeError(f'unsupported parent {parent!r}')

    @classmethod
    def _validate_defined(cls, defined):
        if not defined:
            raise ValueError('missing defined')
        elif isinstance(defined, str):
            if not defined.strip():
                raise ValueError('missing defined')
        elif not isinstance(defined, Location):
            raise TypeError(f'unsupported defined {defined!r}')

    def __new__(cls, kind, name, parent=None, defined=None):
        if cls is CDependency:
            for subclass in (
                CDependencyInclude,
                CDependencyDefine,
                CDependencyDeclaration,
            ):
                if kind in subclass.KINDS:
                    return subclass.__new__(cls, kind, name, parent, defined)
        self = super().__new__(
            cls,
            kind=kind or None,
            name=name or None,
            parent=parent or None,
            defined=defined or None,
        )
        return self

    def __init__(self, *args, **kwargs):
        cls = type(self)
        cls._validate_kind(self.kind)
        cls._validate_name(self.name)
        if self.parent is not None:
            cls._validate_parent(self.parent)
        if self.defined is not None:
            cls._validate_defined(self.defined)

    @property
    def kind(self):
        return self.ref.kind

    @property
    def name(self):
        return self.ref.name

    @property
    def topkind(self):
        return self.ref.topkind

    @property
    def subkind(self):
        return self.ref.subkind

    def match_kind(self, kind):
        return self.ref.match_kind(kind)


class CDependencyInclude(CDependency):

    KINDS = {
        'include-system',
        'include-user',
    }
    KIND_ALIASES = {}

    def download(self, download_include):
        if self.kind != 'include-user':
            raise NotImplementedError(repr(self.kind))
        return download_include('Python.h')


class CDependencyDefine(CDependency):

    KINDS = {
        'define-macro',
        'define-constant',
    }
    KIND_ALIASES = {
        'macro': 'define-macro',
        'constant': 'define-constant',
    }


class CDependencyDeclaration(CDependency):

    KINDS = {
        'typedef',
        'struct',
        'enum',
        'union',
        'symbol-function',
        'symbol-variable',
    }
    KIND_ALIASES = {
        'function': 'symbol-function',
        'variable': 'symbol-variable',
    }


#######################################
# as a script

if __name__ == '__main__':
    import sys
    from pycparser import c_parser

    parser = c_parser.CParser()

    filename = sys.argv[1]
    directives = []

    def on_match(directive, lines):
        directives.append(directive)
        return directive, lines

    with open(filename, encoding='utf-8') as infile:
        lines = clean_lines(infile)
        lines = PreprocessorDirective.replace_lines(lines, on_match, clean=False)
        lines = replace_strings(lines, clean=False)
        text = '\n'.join(lines)
    print(text)

    root = parser.parse(text, filename)
    print(root)
