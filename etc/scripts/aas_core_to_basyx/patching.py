from typing import Optional, Union, Sequence, List
import dataclasses
import ast

from icontract import ensure, require

from basic import Error, pairwise, assert_never


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

