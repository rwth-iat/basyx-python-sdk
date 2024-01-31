from typing import Optional, Tuple, List, Union
import ast

from icontract import ensure

from basic import Error
from patching import Patch


def extract_property_from_self_dot_property(node: ast.expr) -> Optional[str]:
    # Given an expression `self.foo = bar`, returns `"foo"`
    if not isinstance(node, ast.Attribute):
        return None
    if not isinstance(node.value, ast.Name) and node.value.id != "self":
        return None
    return node.attr


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
