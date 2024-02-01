import itertools
import pathlib
import sys
from typing import List, Optional, Tuple, Union
import dataclasses
import argparse
import ast

from icontract import ensure, require

from common import (
    Error,
    parse_file,
    copy_file,
)
from patching import (
    Patch,
    apply_patches
)
from ast_building_blocks import (
    add_import_statement,
    extract_property_from_self_dot_property,
    VisitorReplaceListWith,
    add_inheritance_to_class,
    find_class_def,
    add_attribute_to_class_body
)


_FRAGMENTS_DIR = pathlib.Path(__file__).parent / "fragments"


@dataclasses.dataclass
class AASBaSyxPaths:
    aas_core_path: pathlib.Path  # Path to the aas-core module (with __init__.py)
    basyx_path: pathlib.Path  # Path to the BaSyx module (with __init__.py)


def adapt_common(paths: AASBaSyxPaths) -> Optional[Error]:
    common_path = paths.aas_core_path / 'common.py'
    target_basyx_path = paths.basyx_path / 'aas/util/common.py'
    return copy_file(source_path=common_path, target_path=target_basyx_path)


@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def patch_types_to_add_namespace_classes(module: ast.Module) -> Tuple[Optional[List[Patch]], Optional[Error]]:
    """
    The Namespace classes allow for accessing AAS objects with O(1), since they use Dicts internally.
    However, in order to make them work, they need to be deeply interwoven with the objects themselves.
    Therefore, we patch the classes
        - Namespace,
        - OrderedNamespaceSet,
        - UniqueIdShortNamespaceSet
        - UniqueSemanticIdNamespaceSet
    into the types.py from the fragment Python file
    """
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


@require(lambda cls: cls.name == "AnnotatedRelationshipElement")
@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def patch_class_annotated_relationship_element_for_namespace(
        cls: ast.ClassDef
) -> Tuple[Optional[List[Patch]], Optional[Error]]:
    patches: List[Patch] = []
    errors: List[Error] = []

    # (2024-02-01, s-heppner)
    # Note, we do not have to adapt the inheritance, since Referable objects automatically inherit from Namespace via
    # `HasExtension`

    # Adapt property definitions
    for stmt in cls.body:
        if isinstance(stmt, ast.AnnAssign) and stmt.target.id == "annotations":
            visitor = VisitorReplaceListWith(replace_with="NamespaceSet")
            visitor.visit(stmt)
            patches.extend(visitor.patches)

        if isinstance(stmt, ast.FunctionDef) and stmt.name == "__init__":
            visitor = VisitorReplaceListWith(replace_with="Iterable")

            for arg in itertools.chain(stmt.args.args, stmt.args.kwonlyargs, stmt.args.posonlyargs):
                if arg.arg == "annotations":
                    if arg.annotation is not None:
                        visitor.visit(arg.annotation)

            patches.extend(visitor.patches)

    # Adapt constructor body
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

                if property_name != "annotations":
                    continue

                patches.append(
                    Patch(
                        node=node.value,
                        replacement=f'NamespaceSet(self, [("id_short", True)], annotations)'
                    )
                )

    return patches, None


@require(lambda cls: cls.name == "Entity")
@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def patch_class_entity_for_namespace(
        cls: ast.ClassDef
) -> Tuple[Optional[List[Patch]], Optional[Error]]:
    patches: List[Patch] = []
    errors: List[Error] = []

    # (2024-02-01, s-heppner)
    # Note, we do not have to adapt the inheritance, since Referable objects automatically inherit from Namespace via
    # `HasExtension`

    # Adapt property definitions
    for stmt in cls.body:
        if isinstance(stmt, ast.AnnAssign) and stmt.target.id == "statements":
            visitor = VisitorReplaceListWith(replace_with="NamespaceSet")
            visitor.visit(stmt)
            patches.extend(visitor.patches)

        if isinstance(stmt, ast.FunctionDef) and stmt.name == "__init__":
            visitor = VisitorReplaceListWith(replace_with="Iterable")

            for arg in itertools.chain(stmt.args.args, stmt.args.kwonlyargs, stmt.args.posonlyargs):
                if arg.arg == "statements":
                    if arg.annotation is not None:
                        visitor.visit(arg.annotation)

            patches.extend(visitor.patches)

    # Adapt constructor body
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

                if property_name != "statements":
                    continue

                patches.append(
                    Patch(
                        node=node.value,
                        replacement=f'NamespaceSet(self, [("id_short", True)], statements)'
                    )
                )

    return patches, None


@require(lambda cls: cls.name == "Operation")
@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def patch_class_operation_for_namespace(
        cls: ast.ClassDef
) -> Tuple[Optional[List[Patch]], Optional[Error]]:
    patches: List[Patch] = []
    errors: List[Error] = []

    # (2024-02-01, s-heppner)
    # Note, we do not have to adapt the inheritance, since Referable objects automatically inherit from Namespace via
    # `HasExtension`

    # Adapt property definitions
    for stmt in cls.body:
        if isinstance(stmt, ast.AnnAssign) and stmt.target.id in [
            "input_variables",
            "output_variables",
            "inoutput_variables"
        ]:
            visitor = VisitorReplaceListWith(replace_with="NamespaceSet")
            visitor.visit(stmt)
            patches.extend(visitor.patches)

        if isinstance(stmt, ast.FunctionDef) and stmt.name == "__init__":
            visitor = VisitorReplaceListWith(replace_with="Iterable")

            for arg in itertools.chain(stmt.args.args, stmt.args.kwonlyargs, stmt.args.posonlyargs):
                if arg.arg in [
                    "input_variables",
                    "output_variables",
                    "inoutput_variables"
                ]:
                    if arg.annotation is not None:
                        visitor.visit(arg.annotation)

            patches.extend(visitor.patches)

    # Adapt constructor body
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

                if property_name == "input_variables":
                    patches.append(
                        Patch(
                            node=node.value,
                            replacement=f'NamespaceSet(self, [("id_short", True)], input_variables)'
                        )
                    )
                    continue

                if property_name == "output_variables":
                    patches.append(
                        Patch(
                            node=node.value,
                            replacement=f'NamespaceSet(self, [("id_short", True)], output_variables)'
                        )
                    )
                    continue

                if property_name == "inoutput_variables":
                    patches.append(
                        Patch(
                            node=node.value,
                            replacement=f'NamespaceSet(self, [("id_short", True)], inoutput_variables)'
                        )
                    )
                    continue

    return patches, None


@require(lambda cls: cls.name == "Submodel")
@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def patch_class_submodel_for_namespace(
        cls: ast.ClassDef
) -> Tuple[Optional[List[Patch]], Optional[Error]]:
    patches: List[Patch] = []
    errors: List[Error] = []

    # (2024-02-01, s-heppner)
    # Note, we do not have to adapt the inheritance, since Referable objects automatically inherit from Namespace via
    # `HasExtension`

    # Adapt property definitions
    for stmt in cls.body:
        if isinstance(stmt, ast.AnnAssign) and stmt.target.id == "submodel_elements":
            visitor = VisitorReplaceListWith(replace_with="NamespaceSet")
            visitor.visit(stmt)
            patches.extend(visitor.patches)

        if isinstance(stmt, ast.FunctionDef) and stmt.name == "__init__":
            visitor = VisitorReplaceListWith(replace_with="Iterable")

            for arg in itertools.chain(stmt.args.args, stmt.args.kwonlyargs, stmt.args.posonlyargs):
                if arg.arg == "submodel_elements":
                    if arg.annotation is not None:
                        visitor.visit(arg.annotation)

            patches.extend(visitor.patches)

    # Adapt constructor body
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

                if property_name != "submodel_elements":
                    continue

                patches.append(
                    Patch(
                        node=node.value,
                        replacement=f'NamespaceSet(self, [("id_short", True)], submodel_elements)'
                    )
                )

    return patches, None


@require(lambda cls: cls.name == "SubmodelElementCollection")
@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def patch_class_submodel_element_collection_for_namespace(
        cls: ast.ClassDef
) -> Tuple[Optional[List[Patch]], Optional[Error]]:
    patches: List[Patch] = []
    errors: List[Error] = []

    # (2024-02-01, s-heppner)
    # Note, we do not have to adapt the inheritance, since Referable objects automatically inherit from Namespace via
    # `HasExtension`

    # Adapt property definitions
    for stmt in cls.body:
        if isinstance(stmt, ast.AnnAssign) and stmt.target.id == "value":
            visitor = VisitorReplaceListWith(replace_with="NamespaceSet")
            visitor.visit(stmt)
            patches.extend(visitor.patches)

        if isinstance(stmt, ast.FunctionDef) and stmt.name == "__init__":
            visitor = VisitorReplaceListWith(replace_with="Iterable")

            for arg in itertools.chain(stmt.args.args, stmt.args.kwonlyargs, stmt.args.posonlyargs):
                if arg.arg == "value":
                    if arg.annotation is not None:
                        visitor.visit(arg.annotation)

            patches.extend(visitor.patches)

    # Adapt constructor body
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

                if property_name != "value":
                    continue

                patches.append(
                    Patch(
                        node=node.value,
                        replacement=f'NamespaceSet(self, [("id_short", True)], value)'
                    )
                )

    return patches, None


@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def patch_types_to_use_namespace_sets(module: ast.Module) -> Tuple[Optional[List[Patch]], Optional[Error]]:
    patches: List[Patch] = []
    errors: List[Error] = []

    for stmt in module.body:
        # HasExtension.extensions
        if isinstance(stmt, ast.ClassDef) and stmt.name == "HasExtensions":
            sub_patches, error = patch_class_has_extension_for_namespace(
                cls=stmt
            )

            if error is not None:
                errors.append(error)
            else:
                assert sub_patches is not None
                patches.extend(sub_patches)

        # Qualifiable.qualifiers
        if isinstance(stmt, ast.ClassDef) and stmt.name == "Qualifiable":
            sub_patches, error = patch_class_qualifiable_for_namespace(cls=stmt)
            if error is not None:
                errors.append(error)
            else:
                assert sub_patches is not None
                patches.extend(sub_patches)

        # AnnotatedRelationshipElement.annotations
        if isinstance(stmt, ast.ClassDef) and stmt.name == "AnnotatedRelationshipElement":
            sub_patches, error = patch_class_annotated_relationship_element_for_namespace(cls=stmt)
            if error is not None:
                errors.append(error)
            else:
                assert sub_patches is not None
                patches.extend(sub_patches)

        # Entity.statement
        if isinstance(stmt, ast.ClassDef) and stmt.name == "Entity":
            sub_patches, error = patch_class_entity_for_namespace(cls=stmt)
            if error is not None:
                errors.append(error)
            else:
                assert sub_patches is not None
                patches.extend(sub_patches)

        # Operation.variables
        if isinstance(stmt, ast.ClassDef) and stmt.name == "Operation":
            sub_patches, error = patch_class_operation_for_namespace(cls=stmt)
            if error is not None:
                errors.append(error)
            else:
                assert sub_patches is not None
                patches.extend(sub_patches)

        # Submodel.submodel_element
        if isinstance(stmt, ast.ClassDef) and stmt.name == "Submodel":
            sub_patches, error = patch_class_submodel_for_namespace(cls=stmt)
            if error is not None:
                errors.append(error)
            else:
                assert sub_patches is not None
                patches.extend(sub_patches)

        # SubmodelElementCollection.value
        if isinstance(stmt, ast.ClassDef) and stmt.name == "SubmodelElementCollection":
            sub_patches, error = patch_class_submodel_element_collection_for_namespace(cls=stmt)
            if error is not None:
                errors.append(error)
            else:
                assert sub_patches is not None
                patches.extend(sub_patches)

    if len(errors) > 0:
        return None, Error("Failed to patch types.py for Namespace", underlying_errors=errors)

    return patches, None


@require(lambda cls: cls.name == "HasExtensions")
@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def patch_class_has_extension_for_namespace(
        cls: ast.ClassDef
) -> Tuple[Optional[List[Patch]], Optional[Error]]:
    patches: List[Patch] = []
    errors: List[Error] = []

    sub_patches, sub_error = add_inheritance_to_class(cls, inherit_from="Namespace")
    if sub_error is not None:
        errors.append(sub_error)
    else:
        assert sub_patches is not None
        patches.extend(sub_patches)

    # Adapt property definitions
    for stmt in cls.body:
        if isinstance(stmt, ast.AnnAssign) and stmt.target.id == "extensions":
            visitor = VisitorReplaceListWith(replace_with="NamespaceSet")
            visitor.visit(stmt)
            patches.extend(visitor.patches)

        if isinstance(stmt, ast.FunctionDef) and stmt.name == "__init__":
            visitor = VisitorReplaceListWith(replace_with="Iterable")

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


@require(lambda cls: cls.name == "Qualifiable")
@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def patch_class_qualifiable_for_namespace(
        cls: ast.ClassDef
) -> Tuple[Optional[List[Patch]], Optional[Error]]:
    patches: List[Patch] = []
    errors: List[Error] = []

    sub_patches, sub_error = add_inheritance_to_class(cls, inherit_from="Namespace")
    if sub_error is not None:
        errors.append(sub_error)
    else:
        assert sub_patches is not None
        patches.extend(sub_patches)

    # Adapt property definitions
    for stmt in cls.body:
        if isinstance(stmt, ast.AnnAssign) and stmt.target.id == "qualifiers":
            visitor = VisitorReplaceListWith(replace_with="NamespaceSet")
            visitor.visit(stmt)
            patches.extend(visitor.patches)

        if isinstance(stmt, ast.FunctionDef) and stmt.name == "__init__":
            visitor = VisitorReplaceListWith(replace_with="Iterable")

            for arg in itertools.chain(stmt.args.args, stmt.args.kwonlyargs, stmt.args.posonlyargs):
                if arg.arg == "qualifiers":
                    if arg.annotation is not None:
                        visitor.visit(arg.annotation)

            patches.extend(visitor.patches)

    # Adapt constructor body
    # (`self.qualifiers = qualifiers` => `self.qualifiers = base.NamespaceSet(self, [("type", True)], qualifier)`)
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

                if property_name != "qualifiers":
                    continue

                patches.append(
                    Patch(
                        node=node.value,
                        replacement=f'NamespaceSet(self, [("type", True)], qualifiers)'
                    )
                )

    if len(errors) > 0:
        return None, Error(f"Failed to patch the class {cls.name} for Namespace", underlying_errors=errors)

    return patches, None


@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def patch_types_to_use_unique_id_short_namespace(
        module: ast.Module) -> Tuple[Optional[List[Patch]], Optional[Error]]:
    patches: List[Patch] = []
    errors: List[Error] = []
    # We need to add `parent: Optional[UniqueIdShortNamespace]` attribute to `Referable` and set it to `None' by default
    referable_node: Optional[ast.ClassDef] = find_class_def(module, class_name="Referable")
    if referable_node is None or not isinstance(referable_node, ast.ClassDef):
        return None, Error(f"Could not find class Referable in module {ast.dump(module)}")

    sub_patches, error = add_attribute_to_class_body(
        referable_node,
        attribute_def="parent: Optional[UniqueIdShortNamespace] = None"
    )
    if error is not None:
        errors.append(error)
    else:
        assert sub_patches is not None
        patches.extend(sub_patches)

    # (2024-02-01, s-heppner)
    # We decided not to include the parent parameter in the __init__ function, since it is actually not needed,
    # as it is only managed by Namespace

    return patches, None


@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def patch_types_datatypes(
        module: ast.Module) -> Tuple[Optional[List[Patch]], Optional[Error]]:
    """
    Adapt the types.py to include an attribute `_value_native` for all AAS-objects with `value` and `value_type`
    attributes.
    This new attribute allows for getting and setting native Python values additionally to the aas-core String values.

    Affected classes
        - Property.value
        - Range.min, Range.max
    """
    patches: List[Patch] = []
    errors: List[Error] = []

    return patches, None


def adapt_types(paths: AASBaSyxPaths) -> Optional[Error]:
    types_path = paths.aas_core_path / "types.py"
    atok, sub_error = parse_file(types_path)
    if sub_error is not None:
        return sub_error

    patches: List[Patch] = []
    errors: List[Error] = []

    # Patch types.py to import provider
    sub_patches, error = add_import_statement(
        module=atok.tree,
        import_statement="\nfrom . import provider"
    )
    if error is not None:
        errors.append(error)
    else:
        assert sub_patches is not None
        patches.extend(sub_patches)

    # Add the BaSyx classes Namespace, OrderedNamespaceSet, UniqueIdShortNamespaceSet
    # and UniqueSemanticIdNamespaceSet.
    namespace_class_patches, error = patch_types_to_add_namespace_classes(module=atok.tree)
    if error is not None:
        errors.append(error)
    else:
        assert namespace_class_patches is not None
        patches.extend(namespace_class_patches)

    # Patch aas-core to use NamespaceSets
    sub_patches, error = patch_types_to_use_namespace_sets(module=atok.tree)
    if error is not None:
        errors.append(error)
    else:
        assert sub_patches is not None
        patches.extend(sub_patches)

    # (2024-02-01, s-heppner)
    # We decided not to patch aas-core to use OrderedNamespaceSets,
    # since has only been used in `SubmodelElementList.value` and we decided for allowing accessing the elements
    # only via the aas-core methods

    # Patch aas-core to use UniqueIdShortNamespace
    sub_patches, error = patch_types_to_use_unique_id_short_namespace(module=atok.tree)
    if error is not None:
        errors.append(error)
    else:
        assert sub_patches is not None
        patches.extend(sub_patches)

    # Patch datatypes
    sub_patches, error = patch_types_datatypes(module=atok.tree)
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
    constants_path = paths.aas_core_path / 'constants.py'
    target_basyx_path = paths.basyx_path / 'aas/model/constants.py'
    return copy_file(source_path=constants_path, target_path=target_basyx_path)


def adapt_verification(paths: AASBaSyxPaths) -> Optional[Error]:
    verification_path = paths.aas_core_path / 'verification.py'
    target_basyx_path = paths.basyx_path / 'aas/model/verification.py'
    return copy_file(source_path=verification_path, target_path=target_basyx_path)


def adapt_jsonization(paths: AASBaSyxPaths) -> Optional[Error]:
    jsonization_path = paths.aas_core_path / 'jsonization.py'
    target_basyx_path = paths.basyx_path / 'aas/adapter/json/jsonization.py'
    return copy_file(source_path=jsonization_path, target_path=target_basyx_path)


def adapt_xmlization(paths: AASBaSyxPaths) -> Optional[Error]:
    xmlization_path = paths.aas_core_path / 'xmlization.py'
    target_basyx_path = paths.basyx_path / 'aas/adapter/xml/xmlization.py'
    return copy_file(source_path=xmlization_path, target_path=target_basyx_path)


def adapt_stringification(paths: AASBaSyxPaths) -> Optional[Error]:
    stringification_path = paths.aas_core_path / 'stringification.py'
    target_basyx_path = paths.basyx_path / 'aas/adapter/stringification.py'
    return copy_file(source_path=stringification_path, target_path=target_basyx_path)


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
