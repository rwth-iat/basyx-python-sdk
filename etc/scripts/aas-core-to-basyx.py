import itertools
import pathlib
import sys
import textwrap
from typing import List, Optional, Tuple, Union, Sequence, Dict, Iterable, Iterator, TypeVar, NoReturn, Set
import dataclasses
import argparse
import ast

import asttokens
from icontract import ensure, require

_FRAGMENTS_DIR = pathlib.Path(__file__).parent / "fragments"

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
def source_to_atok(
        source: str,
) -> Tuple[Optional[asttokens.ASTTokens], Optional[Error]]:
    """
    Parse the Python code.

    :param source: Python code as text
    :return: parsed module or error, if any
    """
    try:
        atok = asttokens.ASTTokens(source, parse=True)
    except Exception as exception:
        return None, Error(str(exception))

    return atok, None


@ensure(lambda result: (result[0] is None) ^ (result[1] is None))
def parse_file(path: pathlib.Path) -> Tuple[Optional[asttokens.ASTTokens], Optional[Error]]:
    source = path.read_text(encoding='utf-8')

    atok, error = source_to_atok(source=source)
    if error is not None:
        return None, Error(f"Failed to parse {path}", underlying_errors=[error])

    assert atok is not None
    assert atok.tree is not None
    assert isinstance(atok.tree, ast.Module)

    return atok, None


@dataclasses.dataclass
class AASBaSyxPaths:
    aas_core_path: pathlib.Path
    basyx_path: pathlib.Path


def copy_file(source_path: pathlib.Path, target_path: pathlib.Path) -> Optional[Error]:
    try:
        target_path.write_text(source_path.read_text(encoding='utf-8'), encoding='utf-8')
    except Exception as exception:
        return Error(f"Failed to copy {source_path} to {target_path}: {exception}")
    return None


@dataclasses.dataclass
class Patch:
    node: ast.AST
    prefix: Optional[str] = None
    replacement: Optional[str] = None
    suffix: Optional[str] = None


@dataclasses.dataclass
class InsertPrefix:
    text: str
    position: int

    @property
    def end(self) -> int:
        return self.position


@dataclasses.dataclass
class InsertSuffix:
    text: str
    position: int

    @property
    def end(self) -> int:
        return self.position


@dataclasses.dataclass
class Replace:
    text: str
    position: int
    end: int


Action = Union[InsertPrefix, InsertSuffix, Replace]


def check_replaces_do_not_overlap(actions: Sequence[Action]) -> Optional[Error]:
    previous_replace: Optional[Replace] = None
    for action in actions:
        if not isinstance(action, Replace):
            continue

        if previous_replace is None:
            previous_replace = action
            continue

        if previous_replace.end >= action.position:
            return Error(
                f"The text to be replaced, {previous_replace}, "
                f"overlaps with another text to be replaced, {action}."
            )

        previous_replace = action

    return None


@require(lambda actions: check_replaces_do_not_overlap(actions) is None)
@require(lambda actions: actions == sorted(actions, key=lambda action: action.position))
@ensure(
    lambda result:
    all(
        previous_action.position < action.position for previous_action, action in pairwise(result)
    )
)
def merge_actions(actions: Sequence[Action]) -> List[Action]:
    result: List[Action] = []

    previous_prefix: Optional[InsertPrefix] = None
    previous_suffix: Optional[InsertSuffix] = None

    for action in actions:
        if isinstance(action, InsertPrefix):
            if previous_prefix is not None and previous_prefix.position == action.position:
                previous_prefix.text = f"{action.text}{previous_prefix.text}"
            else:
                prefix_copy = dataclasses.replace(action)
                result.append(prefix_copy)
                previous_prefix = prefix_copy

        elif isinstance(action, InsertSuffix):
            if previous_suffix is not None and previous_suffix.position == action.position:
                previous_suffix.text = f"{previous_suffix.text}{action.text}"
            else:
                suffix_copy = dataclasses.replace(action)
                result.append(suffix_copy)
                previous_suffix = suffix_copy

        elif isinstance(action, Replace):
            result.append(dataclasses.replace(action))

        else:
            assert_never(action)

    return result


def adapt_common(paths: AASBaSyxPaths) -> Optional[Error]:
    common_path = paths.aas_core_path / 'common.py'
    target_basyx_path = paths.basyx_path / 'aas/util/common.py'
    return copy_file(source_path=common_path, target_path=target_basyx_path)


def apply_patches(
        patches: List[Patch],
        text: str
) -> str:
    """Apply the patches by replacing the text correspond to a node with the new text."""
    if len(patches) == 0:
        return text

    actions: List[Action] = []
    for patch in patches:
        if patch.prefix is not None:
            actions.append(InsertPrefix(text=patch.prefix, position=patch.node.first_token.startpos))

        if patch.suffix is not None:
            actions.append(InsertSuffix(text=patch.suffix, position=patch.node.last_token.endpos))

        if patch.replacement is not None:
            actions.append(Replace(text=patch.replacement, position=patch.node.first_token.startpos, end=patch.node.last_token.endpos))

    actions = sorted(actions, key=lambda action: action.position)

    error = check_replaces_do_not_overlap(actions)
    if error is not None:
        raise AssertionError(error)

    actions = merge_actions(actions)

    parts: List[str] = []
    previous_action: Optional[Action] = None

    for action in actions:
        if previous_action is None:
            parts.append(
                text[0:action.position]
            )
        else:
            parts.append(
                text[previous_action.end:action.position]
            )
        parts.append(
            action.text
        )
        previous_action = action
    assert previous_action is not None
    parts.append(
        text[previous_action.end:]
    )

    return "".join(parts)


@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def patch_types_to_import_provider(module: ast.Module) -> Tuple[Optional[List[Patch]], Optional[Error]]:
    last_import: Optional[Union[ast.Import, ast.ImportFrom]] = None

    for stmt in module.body:
        if isinstance(stmt, ast.Import) or isinstance(stmt, ast.ImportFrom):
            last_import = stmt

    if last_import is None:
        return None, Error(
            "No import statements, so we do not know where to append our own import of the provider module"
        )

    return [
        Patch(
            node=last_import,
            suffix="\n\nfrom . import provider"
        )
    ], None


@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def patch_types_to_add_namespace_classes(module: ast.Module) -> Tuple[Optional[List[Patch]], Optional[Error]]:
    # We need to copy the classes Namespace, OrderedNamespaceSet, UniqueIdShortNamespaceSet
    # and UniqueSemanticIdNamespaceSet into types.py
    last_import: Optional[Union[ast.Import, ast.ImportFrom]] = None
    for stmt in module.body:
        if isinstance(stmt, ast.Import) or isinstance(stmt, ast.ImportFrom):
            last_import = stmt

    if last_import is None:
        return None, Error("No import statements, so we do not know where to append the Namespace* classes")

    return [
        Patch(
            node=last_import,
            suffix="\n\n" + (_FRAGMENTS_DIR / "namespace.py").read_text(encoding='utf-8')
        )
    ], None


class VisitorReplaceListWithNamespaceSet(ast.NodeVisitor):
    def __init__(self) -> None:
        self.patches: List[Patch] = []

    def visit_Name(self, node: ast.Name) -> None:
        if node.id == "List":
            self.patches.append(Patch(node=node, replacement="NamespaceSet"))


class VisitorReplaceListWithIterable(ast.NodeVisitor):
    def __init__(self) -> None:
        self.patches: List[Patch] = []

    def visit_Name(self, node: ast.Name) -> None:
        if node.id == "List":
            self.patches.append(Patch(node=node, replacement="Iterable"))


def extract_property_from_self_dot_property(node: ast.expr) -> Optional[str]:
    # Given an expression `self.foo = bar`, returns `"foo"`
    if not isinstance(node, ast.Attribute):
        return None
    if not isinstance(node.value, ast.Name) and node.value.id != "self":
        return None
    return node.attr


@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def patch_class_to_inherit_from_namespace(cls: ast.ClassDef) -> Tuple[Optional[List[Patch]], Optional[Error]]:
    if len(cls.bases) == 0:
        return None, Error("Expected the class to already inherit from other classes, but no inheritance found.")

    return [
        Patch(
                node=cls.bases[-1],
                suffix=", Namespace"
            )
    ], None


@require(lambda cls: cls.name == "HasExtensions")
@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def patch_class_has_extension_for_namespace(
        cls: ast.ClassDef
) -> Tuple[Optional[List[Patch]], Optional[Error]]:
    patches: List[Patch] = []
    errors: List[Error] = []

    sub_patches, sub_error = patch_class_to_inherit_from_namespace(cls)
    if sub_error is not None:
        errors.append(sub_error)
    else:
        assert sub_patches is not None
        patches.extend(sub_patches)
    
    # Adapt property definitions
    for stmt in cls.body:
        if isinstance(stmt, ast.AnnAssign) and stmt.target.id == "extensions":
            visitor = VisitorReplaceListWithNamespaceSet()
            visitor.visit(stmt)
            patches.extend(visitor.patches)

        if isinstance(stmt, ast.FunctionDef) and stmt.name == "__init__":
            visitor = VisitorReplaceListWithIterable()

            for arg in itertools.chain(stmt.args.args, stmt.args.kwonlyargs, stmt.args.posonlyargs):
                if arg.arg == "extensions":
                    if arg.annotation is not None:
                        visitor.visit(arg.annotation)

            patches.extend(visitor.patches)

    # Adapt constructor body
    # (`self.extensions = extensions` => `self.extensions = NamespaceSet(self, [("name", True)], extension)`)
    for stmt in cls.body:
        if isinstance(stmt, ast.FunctionDef) and stmt.name == "__init__":
            for node in stmt.body:
                if not isinstance(node, ast.Assign):
                    continue

                if len(node.targets) != 1:
                    errors.append(Error(f"Unexpected targets in assignment in the constructor: {ast.dump(node)}"))
                    continue

                property_name = extract_property_from_self_dot_property(node.targets[0])
                if property_name is None:
                    continue

                if property_name != "extensions":
                    continue

                patches.append(
                    Patch(
                        node=node.value,
                        replacement=f'NamespaceSet(self, [("name", True)], extensions)'
                    )
                )

    if len(errors) > 0:
        return None, Error(f"Failed to patch the class {cls.name} for Namespace", underlying_errors=errors)

    return patches, None

@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def patch_types_to_use_namespace(module: ast.Module) -> Tuple[Optional[List[Patch]], Optional[Error]]:
    patches: List[Patch] = []
    errors: List[Error] = []

    for stmt in module.body:
        # HasExtensions and Qualifiable inherit from basyx.Namespace
        if isinstance(stmt, ast.ClassDef) and stmt.name == "HasExtensions":
            sub_patches, error = patch_class_has_extension_for_namespace(
                cls=stmt
            )

            if error is not None:
                errors.append(error)
            else:
                assert sub_patches is not None
                patches.extend(sub_patches)

        # TODO
        # if isinstance(stmt, ast.ClassDef) and stmt.name == "Qualifiable":
        #     last_node = stmt.bases[-1]  # These are the classes that are inherited from
        #     patches.append(
        #         Patch(
        #             node=last_node,
        #             suffix=", Namespace"
        #         )
        #     )

    if len(errors) > 0:
        return None, Error("Failed to patch types.py for Namespace", underlying_errors=errors)

    return patches, None


def adapt_types(paths: AASBaSyxPaths) -> Optional[Error]:
    types_path = paths.aas_core_path / "types.py"
    atok, sub_error = parse_file(types_path)
    if sub_error is not None:
        return sub_error

    patches: List[Patch] = []
    errors: List[Error] = []

    import_patches, error = patch_types_to_import_provider(module=atok.tree)
    if error is not None:
        errors.append(error)
    else:
        assert import_patches is not None
        patches.extend(import_patches)

    namespace_class_patches, error = patch_types_to_add_namespace_classes(module=atok.tree)
    if error is not None:
        errors.append(error)
    else:
        assert namespace_class_patches is not None
        patches.extend(namespace_class_patches)


    sub_patches, error = patch_types_to_use_namespace(module=atok.tree)
    if error is not None:
        errors.append(error)
    else:
        assert sub_patches is not None
        patches.extend(sub_patches)

    # Handle applying patches
    if len(errors) > 0:
        return Error("Could not adapt types.py", underlying_errors=errors)

    target_path = paths.basyx_path / "aas" / "model" / "types.py"
    if not target_path.parent.exists() or not target_path.parent.is_dir():
        errors.append(
            Error(f"The model module does not exist or is not a directory: {target_path.parent}")
        )
        return Error("Could not adapt types.py", underlying_errors=errors)

    new_text = apply_patches(patches=patches, text=atok.text)

    target_path.write_text(new_text, encoding='utf-8')

    return None


def adapt_constants(paths: AASBaSyxPaths) -> Optional[Error]:
    return None


def adapt_verification(paths: AASBaSyxPaths) -> Optional[Error]:
    return None


def adapt_jsonization(paths: AASBaSyxPaths) -> Optional[Error]:
    jsonization_path = paths.aas_core_path / 'jsonization.py'
    target_basyx_path = paths.basyx_path / 'aas/adapter/json/jsonization.py'
    return copy_file(source_path=jsonization_path, target_path=target_basyx_path)


def adapt_xmlization(paths: AASBaSyxPaths) -> Optional[Error]:
    xmlization_path = paths.aas_core_path / 'xmlization.py'
    target_basyx_path = paths.basyx_path / 'aas/adapter/xml/xmlization.py'
    return copy_file(source_path=xmlization_path, target_path=target_basyx_path)


def adapt_stringification(paths: AASBaSyxPaths) -> Optional[Error]:
    # Todo
    return None


def aas_core_to_basyx(paths: AASBaSyxPaths) -> Optional[Error]:
    """
    :returns: List of error messages
    """
    errors: List[Error] = []

    error = adapt_common(paths)
    if error is not None:
        errors.append(error)

    error = adapt_types(paths)
    if error is not None:
        errors.append(error)
    error = adapt_constants(paths)
    if error is not None:
        errors.append(error)

    error = adapt_verification(paths)
    if error is not None:
        errors.append(error)

    error = adapt_jsonization(paths)
    if error is not None:
        errors.append(error)

    error = adapt_xmlization(paths)
    if error is not None:
        errors.append(error)

    error = adapt_stringification(paths)
    if error is not None:
        errors.append(error)

    if len(errors) > 0:
        return Error("Could not adapt aas-core to BaSyx", underlying_errors=errors)

    return None


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

    error = aas_core_to_basyx(
        paths=paths
    )
    if error is not None:
        print(str(error))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
