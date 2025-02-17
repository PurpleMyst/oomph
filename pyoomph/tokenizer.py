import re
from typing import Iterator, List, Tuple

import more_itertools

TOKEN_REGEX = r'''
(?P<keyword>
    \b (
        # Please keep oomph_pygments_lexer.py up to date with this list
        let
        | import
        | as
        | export
        | func
        | meth
        | class
        | typedef
        | switch
        | case
        | auto
        | generic
        | new
        | return
        | pass
        | mod
        | and
        | or
        | not
        | in
        | if
        | elif
        | else
        | while
        | for
        | foreach
        | of
        | continue
        | break
    ) \b
)
| (?P<identifier>
    [A-Za-z_] [A-Za-z0-9_]* ( :: [A-Za-z_] [A-Za-z0-9_]* )?
)
| (?P<float>
    ( [1-9][0-9]* | 0 ) \. [0-9]+
)
| (?P<int>
    [1-9][0-9]* | 0
)
# There are slight differences between multiline_string and oneline_string.
# See docs/syntax.md.
| (?P<multiline_string>
    """ (
        [^{}\\]             # Non-special character
        | \\[{}t\\]         # \{ and friends, but no \n since that's confusing
        | { [^{}\n\\]* }    # Code between braces
    )*? """
)
| (?P<oneline_string>
    " (
        [^{}"\n\\]          # Non-special character
        | \\[{}"nt\\]       # \{ and friends
        | { [^{}"\n\\]* }   # Code between braces
    )* "
)
| (?P<op>
    == | !=
    | <= | >=
    | < | >
    | ->
    | =
    | \|
    | \+ | - | \* | /
    | \( | \)
    | \[ | \]
    | \n
    | \. | , | : | ;
)
| (?P<indent>
    # Spaces in beginning of some line other than first line
    # Must be followed by something else than comment or more space
    (?<=\n) [ ]+ (?=[^ #\n])
)
| (?P<ignore>
    # Ignore space not in start of file
    # Ignore comments
    (?<=[\S\s])[ ] | [#].*
)
| (?P<error> .{1,15} )
'''


def raw_tokenize(code: str) -> Iterator[Tuple[str, str]]:
    if not code.endswith("\n"):
        code += "\n"

    for match in re.finditer(TOKEN_REGEX, code, flags=re.VERBOSE):
        tokentype = match.lastgroup
        assert tokentype is not None
        value = match.group()
        assert tokentype != "error", repr(value)
        if tokentype != "ignore":
            # TODO: this is a "temporary" hack to track line numbers in asserts
            if tokentype == "identifier" and value == "assert":
                lineno = code[: match.start()].count("\n") + 1
                tokentype = f"assert_{lineno}"
            # Add this for very verbose tokenizing or parsing debugging:
            # print(repr(match.group()))
            yield (tokentype, match.group())


def _ignore_whitespace_in_parens(
    tokens: Iterator[Tuple[str, str]]
) -> Iterator[Tuple[str, str]]:
    paren_stack: List[str] = []
    for token in tokens:
        if token == ("op", "("):
            paren_stack.append(")")
        elif token == ("op", "["):
            paren_stack.append("]")
        elif token == ("op", ")") or token == ("op", "]"):
            popped = paren_stack.pop()
            assert token == ("op", popped)

        if token[1].strip(" \n") or not paren_stack:
            yield token

    assert not paren_stack


def _combine_not_in(tokens: Iterator[Tuple[str, str]]) -> Iterator[Tuple[str, str]]:
    while True:
        head, tokens = more_itertools.spy(tokens, 2)
        if not head:
            break

        if head == [("keyword", "not"), ("keyword", "in")]:
            yield ("keyword", "not in")
            next(tokens)
            next(tokens)
        else:
            yield next(tokens)


def _find_blocks(tokens: Iterator[Tuple[str, str]]) -> Iterator[Tuple[str, str]]:
    indent_level = 0
    while True:
        head, tokens = more_itertools.spy(tokens, 3)
        if not head:
            break

        if (
            len(head) >= 3
            and head[:2] == [("op", ":"), ("op", "\n")]
            and head[2][0] == "indent"
        ):
            indent_level += 1
            assert head[2][1] == " " * 4 * indent_level
            yield ("begin_block", ":")
            next(tokens)
            next(tokens)
            next(tokens)
            continue

        yield next(tokens)

        if head[0] == ("op", "\n"):
            if len(head) >= 2 and head[1][0] == "indent":
                new_level = len(head[1][1]) // 4
                assert head[1][1] == " " * 4 * new_level
                next(tokens)  # skip indent
            else:
                new_level = 0
            assert new_level <= indent_level
            while indent_level != new_level:
                yield ("end_block", "")
                indent_level -= 1


def _clean_newlines(tokens: Iterator[Tuple[str, str]]) -> Iterator[Tuple[str, str]]:
    token_iter = more_itertools.peekable(tokens)

    # Ignore newlines in beginning
    while token_iter.peek(None) == ("op", "\n"):
        next(token_iter)

    while True:
        try:
            token = next(token_iter)
        except StopIteration:
            break

        # Ignore newlines after beginning of block, end of block, or another newline
        # https://github.com/psf/black/issues/2007
        # fmt: off
        while (token in {('op', '\n'), ('begin_block', ':'), ('end_block', '')} and
               token_iter.peek(None) == ('op', '\n')):
            next(token_iter)
        # fmt: on

        yield token


def tokenize(code: str) -> Iterator[Tuple[str, str]]:
    tokens = raw_tokenize(code)
    tokens = _ignore_whitespace_in_parens(tokens)
    tokens = _combine_not_in(tokens)
    tokens = _clean_newlines(tokens)
    tokens = _find_blocks(tokens)
    tokens = _clean_newlines(tokens)
    return tokens
