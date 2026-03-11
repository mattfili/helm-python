from __future__ import annotations

from fairlead._permissions import resolve_permission
from fairlead._types import Permission, PermissionPolicy, SearchResult, Skill


def _score_match(query: str, result: SearchResult) -> int:
    q = query.lower()

    # Exact qualified name match
    if result.qualified_name.lower() == q:
        return 100

    # Qualified name contains query
    if q in result.qualified_name.lower():
        return 80

    # Operation name contains query
    if q in result.operation.lower():
        return 70

    # Skill name contains query
    if q in result.skill.lower():
        return 60

    # Description contains query
    if q in result.description.lower():
        return 40

    # Tag match
    if any(q in t.lower() for t in result.tags):
        return 30

    return 0


def search(
    query: str,
    registry: dict[str, Skill],
    policy: PermissionPolicy,
    global_default: Permission,
) -> list[SearchResult]:
    results: list[SearchResult] = []

    for skill in registry.values():
        for op_name, op_def in skill.operations.items():
            qualified_name = f"{skill.name}.{op_name}"
            permission = resolve_permission(
                qualified_name,
                op_def.default_permission,
                policy,
                global_default,
            )

            results.append(
                SearchResult(
                    skill=skill.name,
                    operation=op_name,
                    qualified_name=qualified_name,
                    description=op_def.description,
                    signature=op_def.signature,
                    tags=list(op_def.tags),
                    permission=permission,
                )
            )

    scored = [(r, _score_match(query, r)) for r in results]
    scored = [(r, s) for r, s in scored if s > 0]
    scored.sort(key=lambda x: x[1], reverse=True)

    return [r for r, _ in scored]
