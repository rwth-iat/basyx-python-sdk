import pathlib
import sys
from typing import List, Optional, Tuple, Union
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


def copy_file(source_path: pathlib.Path, target_path: pathlib.Path) -> List[str]:
    try:
        target_path.write_text(source_path.read_text(encoding='utf-8'), encoding='utf-8')
    except Exception as exception:
        errors = [f"Failed to copy {source_path} to {target_path}: {exception}"]
    else:
        errors = []
    return errors

@dataclasses.dataclass
class Patch:
    node: ast.AST
    prefix: Optional[str] = None
    replacement: Optional[str] = None
    suffix: Optional[str] = None

def adapt_common(paths: AASBaSyxPaths) -> List[str]:
    common_path = paths.aas_core_path / 'aas_core3' / 'common.py'
    target_basyx_path = paths.basyx_path / 'aas' / 'util' / 'common.py'
    return copy_file(source_path=common_path, target_path=target_basyx_path)


def apply_patches(
        patches: List[Patch],
        text: str
) -> str:
    """Apply the patches by replacing the text correspond to a node with the new text."""
    if len(patches) == 0:
        return text

    sorted_patches = sorted(
        patches,
        key=lambda patch: patch.node.first_token.startpos
    )

    # region Assert no overlaps
    prev_node: Optional[ast.AST] = None
    for patch in sorted_patches:
        if prev_node is None:
            prev_node = patch.node
            continue

        if prev_node.last_token.endpos >= patch.node.first_toke.startpos:
            raise AssertionError(
                f"The patch for the node {ast.dump(prev_node)} overlaps with the node {ast.dump(patch.node)}"
            )

        prev_node = patch.node
    # endregion

    parts: List[str] = []

    last_node: Optional[ast.AST] = None

    for patch in sorted_patches:
        if last_node is None:
            parts.append(
                text[0:patch.node.first_token.startpos]
            )
        else:
            parts.append(
                text[last_node.last_token.endpos:patch.node.first_token.startpos]
            )

        if patch.prefix is not None:
            parts.append(patch.prefix)

        if patch.replacement is not None:
            parts.append(patch.replacement)
        else:
            parts.append(
                text[patch.node.first_token.startpos:patch.node.last_token.endpos]
            )

        if patch.suffix is not None:
            parts.append(patch.suffix)

        last_node = patch.node

    assert last_node is not None
    parts.append(text[last_node.last_token.endpos:])

    return "".join(parts)


class ImportFixVisitor(ast.NodeVisitor):
    def __init__(self):
        self.patches: List[Tuple[ast.AST, str]] = []


@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def patch_types_to_import_provider(module: ast.Module) -> Tuple[Optional[List[Patch]], Optional[str]]:
    last_import: Optional[Union[ast.Import, ast.ImportFrom]] = None

    for stmt in module.body:
        if isinstance(stmt, ast.Import) or isinstance(stmt, ast.ImportFrom):
            last_import = stmt

    if last_import is None:
        return None, "No import statements, so we do not know where to append our own import"

    return [
        Patch(
            node=last_import,
            suffix="\n\nfrom . import provider"
        )
    ], None


def adapt_types(paths: AASBaSyxPaths) -> List[str]:
    types_path = paths.aas_core_path / "types.py"

    atok, error = parse_file(types_path)
    if error is not None:
        return [error]

    errors: List[str] = []

    assert atok.tree is not None
    assert isinstance(atok.tree, ast.Module)

    patches: List[Patch] = []

    import_patches, error = patch_types_to_import_provider(module=atok.tree)
    if error is not None:
        errors.append(error)
    else:
        assert import_patches is not None
        patches.extend(import_patches)

    if len(errors) > 0:
        return errors

    target_path = paths.basyx_path / "aas" / "model" / "types.py"
    if not target_path.parent.exists() or not target_path.parent.is_dir():
        errors.append(
            f"The model module does not exist or is not a directory: {target_path.parent}"
        )
        return errors

    new_text = apply_patches(patches=patches, text=atok.text)

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
