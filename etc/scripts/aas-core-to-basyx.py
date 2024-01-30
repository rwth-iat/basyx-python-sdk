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
    common_path = paths.aas_core_path / 'aas_core3' / 'common.py'
    target_basyx_path = paths.basyx_path / 'aas' / 'util' / 'common.py'
    # Copy common.py to basyx/aas/utils/common.py
    try:
        target_basyx_path.write_text(common_path.read_text(encoding='utf-8'), encoding='utf-8')
    except Exception as exception:
        errors = [f"Failed to copy {common_path} to {target_basyx_path}: {exception}"]
    else:
        errors = []
    return errors


def apply_patches(
        patches: List[Tuple[ast.AST, str]],
        text: str
) -> str:
    """Apply the patches by replacing the text correspond to a node with the new text."""
    if len(patches) == 0:
        return text

    sorted_patches = sorted(
        patches,
        key=lambda patch: patch[0].first_token.startpos
    )

    # region Assert no overlaps
    prev_node: Optional[ast.AST] = None
    for node, _ in sorted_patches:
        if prev_node is None:
            prev_node = node
            continue

        if prev_node.last_token.endpos >= node.first_toke.startpos:
            raise AssertionError(
                f"The patch for the node {ast.dump(prev_node)} overlaps with the node {ast.dump(node)}"
            )

        prev_node = node
    # endregion

    parts: List[str] = []

    last_node: Optional[ast.AST] = None

    for node, new_text in sorted_patches:
        if last_node is None:
            parts.append(
                text[0:node.first_token.startpos]
            )
        else:
            parts.append(
                text[last_node.last_token.endpos:node.first_token.startpos]
            )

        parts.append(new_text)
        last_node = node

    assert last_node is not None
    parts.append(text[last_node.last_token.endpos:])

    return "".join(parts)


class ImportFixVisitor(ast.NodeVisitor):
    def __init__(self):
        self.patches: List[Tuple[ast.AST, str]] = []


def adapt_types(paths: AASBaSyxPaths) -> List[str]:
    types_path = paths.aas_core_path / "types.py"

    atok, error = parse_file(types_path)
    if error is not None:
        return [error]

    errors: List[str] = []

    assert atok.tree is not None
    assert isinstance(atok.tree, ast.Module)

    visitor = ImportFixVisitor()
    visitor.visit(atok.tree)
    new_text = apply_patches(patches=visitor.patches, text=atok.text)

    target_path = paths.basyx_path / "aas" / "model" / "types.py"
    if not target_path.parent.exists() or not target_path.parent.is_dir():
        errors.append(
            f"The model module does not exist or is not a directory: {target_path.parent}"
        )
        return errors

    target_path.write_text(new_text, encoding='utf-8')

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

    paths = AASBaSyxPaths(
        aas_core_path=pathlib.Path(args.aas_core_path),
        basyx_path=pathlib.Path(args.basyx_path)
    )

    aas_core_init_path = paths.aas_core_path / "__init__.py"
    if not aas_core_init_path.exists():
        print(
            f"--aas_core_path does not point to a module: the __init__.py is missing: {aas_core_init_path}",
            file=sys.stderr
        )
        return 1

    basyx_init_path = paths.basyx_path / "__init__.py"
    if not basyx_init_path.exists():
        print(
            f"--basyx_path does not point to a module: the __init__.py is missing: {basyx_init_path}",
            file=sys.stderr
        )
        return 1

    errors = aas_core_to_basyx(
        paths=paths
    )
    if len(errors) > 0:
        print("There were errors :(", file=sys.stderr)
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
