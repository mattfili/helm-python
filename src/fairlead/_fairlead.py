from __future__ import annotations

import inspect
import time
from typing import Any

from fairlead._permissions import PermissionDeniedError, resolve_permission
from fairlead._trace import TraceEntry, get_trace, record_entry
from fairlead._search import search
from fairlead._types import (
    FairleadOptions,
    Permission,
    PermissionPolicy,
    SearchResult,
    Skill,
)


def _make_bound(
    qn: str,
    op_default: Permission | None,
    handler: Any,
    owner: Fairlead,
) -> Any:
    async def _wrapped(*args: Any, **kwargs: Any) -> Any:
        tracing = get_trace() is not None
        permission = resolve_permission(
            qn, op_default, owner._policy, owner._global_default
        )

        if permission == "deny":
            if tracing:
                record_entry(TraceEntry(
                    operation=qn,
                    args=kwargs,
                    error="PermissionDeniedError",
                    permission="deny",
                ))
            raise PermissionDeniedError(qn)

        if permission == "ask":
            if owner._on_permission_request is None:
                if tracing:
                    record_entry(TraceEntry(
                        operation=qn,
                        args=kwargs,
                        error="PermissionDeniedError",
                        permission="ask",
                    ))
                raise PermissionDeniedError(qn)

            result = owner._on_permission_request(qn, list(args))
            if inspect.isawaitable(result):
                allowed = await result
            else:
                allowed = result

            if not allowed:
                if tracing:
                    record_entry(TraceEntry(
                        operation=qn,
                        args=kwargs,
                        error="PermissionDeniedError",
                        permission="ask",
                    ))
                raise PermissionDeniedError(qn)

        if not tracing:
            result = handler(*args, **kwargs)
            if inspect.isawaitable(result):
                return await result
            return result

        t0 = time.monotonic()
        try:
            result = handler(*args, **kwargs)
            if inspect.isawaitable(result):
                result = await result
        except Exception as exc:
            duration_ms = (time.monotonic() - t0) * 1000
            record_entry(TraceEntry(
                operation=qn,
                args=kwargs,
                error=repr(exc),
                permission=permission,
                duration_ms=duration_ms,
            ))
            raise
        else:
            duration_ms = (time.monotonic() - t0) * 1000
            record_entry(TraceEntry(
                operation=qn,
                args=kwargs,
                result=result,
                permission=permission,
                duration_ms=duration_ms,
            ))
            return result

    return _wrapped


class _BoundNamespace:
    """Provides attribute access to bound operations for a registered skill."""

    def __init__(self, ops: dict[str, Any]) -> None:
        self._ops = ops

    def __getattr__(self, name: str) -> Any:
        try:
            return self._ops[name]
        except KeyError:
            raise AttributeError(
                f"Operation '{name}' not found in skill"
            ) from None


class Fairlead:
    def __init__(self, options: FairleadOptions | None = None) -> None:
        opts = options or FairleadOptions()
        self._policy: PermissionPolicy = dict(opts.permissions)
        self._global_default: Permission = opts.default_permission
        self._on_permission_request = opts.on_permission_request
        self._registry: dict[str, Skill] = {}
        self._namespaces: dict[str, _BoundNamespace] = {}

    def use(self, skill: Skill) -> Fairlead:
        bound_ops: dict[str, Any] = {}

        for op_name, op_def in skill.operations.items():
            qualified_name = f"{skill.name}.{op_name}"
            bound_ops[op_name] = _make_bound(
                qualified_name, op_def.default_permission, op_def.handler, self
            )

        self._registry[skill.name] = skill
        self._namespaces[skill.name] = _BoundNamespace(bound_ops)
        return self

    async def call(self, qualified_name: str, kwargs: dict[str, Any] | None = None) -> Any:
        parts = qualified_name.split(".", 1)
        if len(parts) != 2:
            raise ValueError(
                f"Invalid qualified name '{qualified_name}': expected 'skill.operation'"
            )
        skill_name, op_name = parts
        ns = self._namespaces.get(skill_name)
        if ns is None:
            raise AttributeError(
                f"Skill '{skill_name}' not registered. Use .use() to register skills."
            )
        try:
            bound_op = ns._ops[op_name]
        except KeyError:
            raise AttributeError(
                f"Operation '{op_name}' not found in skill '{skill_name}'"
            ) from None
        return await bound_op(**(kwargs or {}))

    async def run(self, code: str) -> Any:
        """Execute a code block with this instance available as ``agent``.

        Works identically whether called directly from Python (agent SDKs,
        LangChain, etc.) or dispatched via the MCP ``run`` tool.
        """
        from fairlead._exec import exec_code

        result = await exec_code(self, code)
        return result

    def search(self, query: str) -> list[SearchResult]:
        return search(query, self._registry, self._policy, self._global_default)

    def __getattr__(self, name: str) -> Any:
        try:
            return self._namespaces[name]
        except KeyError:
            raise AttributeError(
                f"Skill '{name}' not registered. Use .use() to register skills."
            ) from None


def create_fairlead(options: FairleadOptions | None = None) -> Fairlead:
    return Fairlead(options)
