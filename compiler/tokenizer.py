import re
from typing import Iterator, Tuple

_TOKEN_REGEX = (
    r'(?P<keyword>\blet\b|\bfunc\b|\bvoid\b)|'
    r'(?P<var>[A-Za-z_][A-Za-z0-9_]*)|'
    r'(?P<int>[1-9][0-9]*|0)|'
    r'(?P<op>[=+(),{}\n]|->)|'
    r'(?P<ignore> |#.*)|'
    r'(?P<error>.)'
)


def _raw_tokenize(code: str) -> Iterator[Tuple[str, str]]:
    if not code.endswith('\n'):
        code += '\n'

    for match in re.finditer(_TOKEN_REGEX, code):
        tokentype = match.lastgroup
        assert tokentype is not None
        value = match.group()
        assert tokentype != 'error', value
        if tokentype != 'ignore':
            yield (tokentype, match.group())
    yield ('end', '')


def _clean_newlines(tokens: Iterator[Tuple[str, str]]) -> Iterator[Tuple[str, str]]:
    previous_value = None
    for tokentype, value in tokens:
        # Skip newline in beginning of file and double newlines
        if value != '\n' or (previous_value is not None and previous_value != '\n'):
            yield (tokentype, value)
        previous_value = value


def tokenize(code: str) -> Iterator[Tuple[str, str]]:
    return _clean_newlines(_raw_tokenize(code))
