from __future__ import annotations

import importlib
import inspect
import pkgutil
import re
from types import ModuleType
from typing import Any

from fairlead._skill import define_skill
from fairlead._types import OperationDef, Permission, Skill


def module(
    package: str | ModuleType,
    *,
    name: str | None = None,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    default_permission: Permission | None = None,
) -> Skill:
    """Create a Skill from a Python package by introspecting its public callables.

    Args:
        package: Package name (str) or already-imported module.
        name: Skill name, defaults to package name.
        include: Submodule allowlist (first component), e.g. ["ensemble", "metrics"].
        exclude: Submodule denylist, e.g. ["tests"].
        default_permission: Default permission for all operations.
    """
    pkg, pkg_name = _resolve_package(package)
    skill_name = name or pkg_name

    modules = _walk_package(pkg, pkg_name, include, exclude)
    entries = _discover_callables(modules, pkg_name)
    named = _disambiguate_names(entries)

    operations: dict[str, OperationDef] = {}
    for op_name, obj, rel_submod in named:
        operations[op_name] = _make_operation(obj, op_name, rel_submod, default_permission)

    return define_skill(
        name=skill_name,
        description=f"Python package: {pkg_name}",
        operations=operations,
    )


def _resolve_package(package: str | ModuleType) -> tuple[ModuleType, str]:
    if isinstance(package, str):
        pkg = importlib.import_module(package)
    else:
        pkg = package
    pkg_name = pkg.__name__
    if not hasattr(pkg, "__path__"):
        raise ValueError(f"{pkg_name} is not a package (no __path__)")
    return pkg, pkg_name


def _walk_package(
    pkg: ModuleType,
    pkg_name: str,
    include: list[str] | None,
    exclude: list[str] | None,
) -> list[ModuleType]:
    modules: list[ModuleType] = [pkg]
    for importer, mod_name, ispkg in pkgutil.walk_packages(
        pkg.__path__, prefix=pkg_name + "."  # type: ignore[arg-type]
    ):
        rel = mod_name[len(pkg_name) + 1 :]
        first_component = rel.split(".")[0]

        if include is not None and first_component not in include:
            continue
        if exclude is not None and first_component in exclude:
            continue

        try:
            modules.append(importlib.import_module(mod_name))
        except Exception:
            continue
    return modules


def _discover_callables(
    modules: list[ModuleType],
    pkg_name: str,
) -> list[tuple[str, Any, str]]:
    """Return (callable_name, obj, relative_submodule) for public callables."""
    seen_ids: set[int] = set()
    entries: list[tuple[str, Any, str]] = []

    for mod in modules:
        rel_submod = mod.__name__[len(pkg_name) :].lstrip(".")

        for attr_name, obj in inspect.getmembers(mod, callable):
            if attr_name.startswith("_"):
                continue

            obj_module = getattr(obj, "__module__", None)
            if obj_module is not None and not obj_module.startswith(pkg_name):
                continue

            if inspect.isabstract(obj):
                continue

            obj_id = id(obj)
            if obj_id in seen_ids:
                continue
            seen_ids.add(obj_id)

            # Classes become constructors; functions stay as-is
            if inspect.isclass(obj) and not inspect.isfunction(obj):
                pass  # handler will be the class itself (calling it = constructor)

            entries.append((attr_name, obj, rel_submod))

    return entries


def _disambiguate_names(
    entries: list[tuple[str, Any, str]],
) -> list[tuple[str, Any, str]]:
    """Assign unique snake_case operation names, disambiguating collisions."""
    # Group by slugified name
    groups: dict[str, list[tuple[str, Any, str]]] = {}
    for attr_name, obj, rel_submod in entries:
        slug = _slugify(attr_name)
        groups.setdefault(slug, []).append((attr_name, obj, rel_submod))

    result: list[tuple[str, Any, str]] = []
    for slug, group in groups.items():
        if len(group) == 1:
            attr_name, obj, rel_submod = group[0]
            result.append((slug, obj, rel_submod))
        else:
            # Disambiguate by prepending first submodule component
            second_try: dict[str, list[tuple[str, Any, str]]] = {}
            for attr_name, obj, rel_submod in group:
                first_comp = rel_submod.split(".")[0] if rel_submod else ""
                prefixed = f"{first_comp}_{slug}" if first_comp else slug
                second_try.setdefault(prefixed, []).append((attr_name, obj, rel_submod))

            for prefixed_slug, sub_group in second_try.items():
                if len(sub_group) == 1:
                    _, obj, rel_submod = sub_group[0]
                    result.append((prefixed_slug, obj, rel_submod))
                else:
                    # Full path disambiguation
                    for attr_name, obj, rel_submod in sub_group:
                        full = f"{rel_submod.replace('.', '_')}_{slug}" if rel_submod else slug
                        result.append((full, obj, rel_submod))

    return result


def _slugify(s: str) -> str:
    s = re.sub(r"[{}]", "", s)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s)
    s = s.strip("_").lower()
    return s


def _make_operation(
    obj: Any,
    op_name: str,
    rel_submod: str,
    default_permission: Permission | None,
) -> OperationDef:
    doc = inspect.getdoc(obj)
    description = doc.split("\n")[0] if doc else op_name

    try:
        sig = str(inspect.signature(obj))
    except (ValueError, TypeError):
        sig = None

    is_class = inspect.isclass(obj)
    tags: list[str] = ["class" if is_class else "function"]
    if rel_submod:
        for part in rel_submod.split("."):
            if not part.startswith("_"):
                tags.append(part)

    return OperationDef(
        description=description,
        handler=obj,
        signature=sig,
        tags=tags,
        default_permission=default_permission,
    )
