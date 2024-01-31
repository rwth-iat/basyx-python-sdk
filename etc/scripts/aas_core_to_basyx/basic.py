from typing import Iterable, Iterator, Tuple, TypeVar, NoReturn, Optional, List
import itertools
import textwrap
import pathlib
import ast

import asttokens
from icontract import ensure


T = TypeVar("T")


def pairwise(iterable: Iterable[T]) -> Iterator[Tuple[T, T]]:
    """
    Iterate pair-wise over the iterator.

    >>> list(pairwise("ABCDE"))
    [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'E')]
    """
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)


def assert_never(value: NoReturn) -> NoReturn:
    """
    Signal to mypy to perform an exhaustive matching.

    Please see the following page for more details:
    https://hakibenita.com/python-mypy-exhaustive-checking
    """
    assert False, f"Unhandled value: {value} ({type(value).__name__})"


class Error:
    def __init__(self, message: str, underlying_errors: Optional[List["Error"]] = None) -> None:
        self.message = message
        self.underlying_errors = underlying_errors

    def __str__(self) -> str:
        if self.underlying_errors is None or len(self.underlying_errors) == 0:
            return self.message

        blocks = [self.message]
        for sub_error in self.underlying_errors:
            sub_message = textwrap.indent(str(sub_error), "  ")
            sub_message = "*" + sub_message[1:]

            blocks.append(sub_message)

        return "\n".join(blocks)


@ensure(lambda result: (result[0] is None) ^ (result[1] is None))
def parse_file(path: pathlib.Path) -> Tuple[Optional[asttokens.ASTTokens], Optional[Error]]:
    """
    Parse the given python file and return the abstract syntax tree tokens of the module
    """
    source = path.read_text(encoding='utf-8')

    try:
        atok = asttokens.ASTTokens(source, parse=True)
    except Exception as exception:
        return None, Error(f"Failed to parse {path}: {exception}")

    assert atok is not None
    assert atok.tree is not None
    assert isinstance(atok.tree, ast.Module)

    return atok, None


def copy_file(source_path: pathlib.Path, target_path: pathlib.Path) -> Optional[Error]:
    try:
        target_path.write_text(source_path.read_text(encoding='utf-8'), encoding='utf-8')
    except Exception as exception:
        return Error(f"Failed to copy {source_path} to {target_path}: {exception}")
    return None
