import pathlib
import sys
from typing import List, Optional, Tuple
import dataclasses
import argparse
import ast
import asttokens
from icontract import ensure


@ensure(lambda result: (result[0] is None) ^ (result[1] is None))
def source_to_atok(
    source: str,
) -> Tuple[Optional[asttokens.ASTTokens], Optional[str]]:
    """
    Parse the Python code.

    :param source: Python code as text
    :return: parsed module or error, if any
    """
    try:
        atok = asttokens.ASTTokens(source, parse=True)
    except Exception as exception:
        return None, str(exception)

    return atok, None


@ensure(lambda result: (result[0] is None) ^ (result[1] is None))
def parse_file(path: pathlib.Path) -> Tuple[Optional[asttokens.ASTTokens], Optional[str]]:
    source = path.read_text(encoding='utf-8')

    atok, error = source_to_atok(source=source)
    if error is not None:
        return None, f"Failed to parse {path}: {error}"

    assert atok is not None

    return atok, None


@dataclasses.dataclass
class AASBaSyxPaths:
    aas_core_path: pathlib.Path
    basyx_path: pathlib.Path


def adapt_common(paths: AASBaSyxPaths) -> List[str]:
    errors: List[str] = []
    return errors


def adapt_types(paths: AASBaSyxPaths) -> List[str]:
    errors: List[str] = []
    return errors


def adapt_constants(paths: AASBaSyxPaths) -> List[str]:
    errors: List[str] = []
    return errors


def adapt_verification(paths: AASBaSyxPaths) -> List[str]:
    errors: List[str] = []
    return errors


def adapt_jsonization(paths: AASBaSyxPaths) -> List[str]:
    errors: List[str] = []
    return errors


def adapt_xmlization(paths: AASBaSyxPaths) -> List[str]:
    errors: List[str] = []
    return errors


def adapt_stringification(paths: AASBaSyxPaths) -> List[str]:
    errors: List[str] = []
    return errors


def aas_core_to_basyx(paths: AASBaSyxPaths) -> List[str]:
    """
    :returns: List of error messages
    """
    errors: List[str] = []
    errors.extend(adapt_common(paths))
    errors.extend(adapt_types(paths))
    errors.extend(adapt_constants(paths))
    errors.extend(adapt_verification(paths))
    errors.extend(adapt_jsonization(paths))
    errors.extend(adapt_xmlization(paths))
    errors.extend(adapt_stringification(paths))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--aas_core_path", required=True, help="Path to the aas-core Python module")
    parser.add_argument("--basyx_path", required=True, help="Path to the BaSyx module")
    args = parser.parse_args()
    errors = aas_core_to_basyx(
        paths=AASBaSyxPaths(
            aas_core_path=pathlib.Path(args.aas_core_path),
            basyx_path=pathlib.Path(args.basyx_path)
        )
    )
    if len(errors) > 0:
        print("There were errors :(", file=sys.stderr)
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
