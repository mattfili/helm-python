from __future__ import annotations

from fairlead._types import OperationDef, Skill


def define_skill(
    *,
    name: str,
    description: str,
    operations: dict[str, OperationDef],
) -> Skill:
    return Skill(name=name, description=description, operations=operations)
