from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Literal, Union

Permission = Literal["allow", "ask", "deny"]


@dataclass(frozen=True)
class OperationDef:
    description: str
    handler: Callable[..., Any]
    signature: str | None = None
    tags: list[str] = field(default_factory=list)
    default_permission: Permission | None = None


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    operations: dict[str, OperationDef]


PermissionPolicy = dict[str, Permission]

OnPermissionRequest = Callable[[str, list[Any]], Union[bool, Awaitable[bool]]]


@dataclass(frozen=True)
class FairleadOptions:
    permissions: PermissionPolicy = field(default_factory=dict)
    on_permission_request: OnPermissionRequest | None = None
    default_permission: Permission = "ask"


@dataclass(frozen=True)
class SearchResult:
    skill: str
    operation: str
    qualified_name: str
    description: str
    tags: list[str]
    permission: Permission
    signature: str | None = None
