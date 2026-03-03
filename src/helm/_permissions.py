from __future__ import annotations

from helm._types import Permission, PermissionPolicy


class PermissionDeniedError(Exception):
    def __init__(self, qualified_name: str) -> None:
        super().__init__(f"Permission denied: {qualified_name}")
        self.qualified_name = qualified_name


def resolve_permission(
    qualified_name: str,
    operation_default: Permission | None,
    policy: PermissionPolicy,
    global_default: Permission,
) -> Permission:
    # 1. Exact match in policy
    if qualified_name in policy:
        return policy[qualified_name]

    # 2. Wildcard match (e.g. "git.*")
    dot_index = qualified_name.find(".")
    if dot_index != -1:
        wildcard = qualified_name[:dot_index] + ".*"
        if wildcard in policy:
            return policy[wildcard]

    # 3. Operation's own default
    if operation_default is not None:
        return operation_default

    # 4. Global default
    return global_default
