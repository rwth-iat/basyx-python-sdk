from typing import Optional, Tuple, List, Union
import ast

from icontract import ensure

from common import Error
from patching import Patch


def extract_property_from_self_dot_property(node: ast.expr) -> Optional[str]:
    # Given an expression `self.foo = bar`, returns `"foo"`
    if not isinstance(node, ast.Attribute):
        return None
    if not isinstance(node.value, ast.Name) and node.value.id != "self":
        return None
    return node.attr


def find_class_def(module: ast.Module, class_name: str) -> Optional[ast.ClassDef]:
    """
    Find an AST class node by its name, if it exists in the given module
    """
    for stmt in module.body:
        if isinstance(stmt, ast.ClassDef) and stmt.name == class_name:
            return stmt
    return None


@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def add_attribute_to_class_body(cls: ast.ClassDef, attribute_def: str) -> Tuple[Optional[List[Patch]], Optional[Error]]:
    """
    Adds a given attribute string to a classes body. For example with `attribute_def='example: int'`:

    class Foo:
        bar: str

    becomes

    class Foo:
        bar: str
        example: int
    """
    patches: List[Patch] = []
    errors: List[Error] = []

    # Find the last AnnAssign to append the new attribute
    for stmt in reversed(cls.body):
        if isinstance(stmt, ast.AnnAssign):
            patches.append(Patch(
                node=stmt,
                suffix=f"\n    {attribute_def}"
            ))
            return patches, None
    # If we ended up here, there are no AnnAssigns, so we add the attribute as the first element
    # (2024-02-01, s-heppner):
    # I won't implement this right now, since I am not sure this case exists in practice
    return None, Error(f"Could not add attribute_def {attribute_def} to class {ast.dump(cls)}")


@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def add_import_statement(
        module: ast.Module,
        import_statement: str
) -> Tuple[Optional[List[Patch]], Optional[Error]]:
    """
    Adds an import statement behind the last import statement of the module

    :ivar import_statement: The full import statement string e.g. `import Namespace` plus additional `\n`s
    """
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
            suffix=f"\n{import_statement}"
        )
    ], None


class VisitorReplaceListWith(ast.NodeVisitor):
    """
    Adds patches to replace List with the given string
    """
    def __init__(self, replace_with: str) -> None:
        self.patches: List[Patch] = []
        self.replace_with: str = replace_with

    def visit_Name(self, node: ast.Name) -> None:
        if node.id == "List":
            self.patches.append(Patch(node=node, replacement=self.replace_with))


@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def add_inheritance_to_class(cls: ast.ClassDef, inherit_from: str) -> Tuple[Optional[List[Patch]], Optional[Error]]:
    """
    Adds the given string to the inheritances of the given class.
    Adds behind the last inheritance
    Note, that we assume no `,` is present behind the last class
    """
    if len(cls.bases) == 0:
        return None, Error("Expected the class to already inherit from other classes, but no inheritance found.")

    return [
        Patch(
                node=cls.bases[-1],
                suffix=f", {inherit_from}"
            )
    ], None
