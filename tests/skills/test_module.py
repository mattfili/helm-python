"""Tests for module() factory — auto-generate Skills from Python packages."""

from __future__ import annotations

import pytest

from fairlead import FairleadOptions, create_fairlead
from fairlead.skills._module import module, _slugify

import tests.skills._fixture_pkg as fix_pkg


def _skill():
    return module(fix_pkg)


def _agent(skill=None):
    s = skill or _skill()
    return create_fairlead(FairleadOptions(default_permission="allow")).use(s)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


class TestDiscovery:
    def test_creates_skill_from_module_object(self) -> None:
        skill = module(fix_pkg)
        assert skill.name == "tests.skills._fixture_pkg"
        assert len(skill.operations) > 0

    def test_defaults_name_to_package_name(self) -> None:
        skill = module(fix_pkg)
        assert skill.name == "tests.skills._fixture_pkg"

    def test_custom_name(self) -> None:
        skill = module(fix_pkg, name="my_lib")
        assert skill.name == "my_lib"

    def test_discovers_functions(self) -> None:
        skill = _skill()
        op_names = list(skill.operations.keys())
        assert any("multiply" in n for n in op_names)

    def test_discovers_classes_as_constructors(self) -> None:
        skill = _skill()
        op_names = list(skill.operations.keys())
        assert any("widget" in n for n in op_names)
        # Find the widget operation and check its tag
        widget_op = next(op for name, op in skill.operations.items() if "widget" in name)
        assert "class" in widget_op.tags

    def test_skips_private_callables(self) -> None:
        skill = _skill()
        op_names = list(skill.operations.keys())
        assert not any("private_helper" in n for n in op_names)
        assert not any("secret" in n for n in op_names)

    def test_skips_abstract_classes(self) -> None:
        skill = _skill()
        op_names = list(skill.operations.keys())
        assert not any("abstract_base" in n for n in op_names)

    def test_includes_public_from_private_submodule(self) -> None:
        skill = _skill()
        op_names = list(skill.operations.keys())
        assert any("public_from_internal" in n for n in op_names)

    def test_filters_by_module_origin(self) -> None:
        skill = _skill()
        op_names = list(skill.operations.keys())
        # ABC is imported in beta but belongs to abc module — should not appear
        assert not any(n == "abc" for n in op_names)
        assert not any(n == "abstract_method" for n in op_names)


# ---------------------------------------------------------------------------
# Naming
# ---------------------------------------------------------------------------


class TestNaming:
    def test_snake_cases_class_names(self) -> None:
        skill = _skill()
        op_names = list(skill.operations.keys())
        # Widget -> widget (already lowercase after slugify)
        assert any("widget" in n for n in op_names)
        # No CamelCase names should remain
        assert not any("Widget" in n for n in op_names)

    def test_disambiguates_collisions(self) -> None:
        skill = _skill()
        op_names = list(skill.operations.keys())
        # alpha.add and gamma.delta.add should produce two distinct ops
        add_ops = [n for n in op_names if "add" in n and "public" not in n]
        assert len(add_ops) >= 2, f"Expected 2+ add ops, got {add_ops}"
        # They should be different names
        assert len(set(add_ops)) == len(add_ops)


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


class TestFiltering:
    def test_include_filter(self) -> None:
        skill = module(fix_pkg, include=["alpha"])
        op_names = list(skill.operations.keys())
        assert any("add" in n for n in op_names) or any("multiply" in n for n in op_names)
        assert not any("widget" in n for n in op_names)
        assert not any("processor" in n for n in op_names)

    def test_exclude_filter(self) -> None:
        skill = module(fix_pkg, exclude=["beta"])
        op_names = list(skill.operations.keys())
        assert not any("widget" in n for n in op_names)
        assert not any("abstract_base" in n for n in op_names)
        # alpha and gamma should still be present
        assert any("multiply" in n for n in op_names)


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class TestMetadata:
    def test_description_from_docstring(self) -> None:
        skill = _skill()
        multiply_op = next(op for name, op in skill.operations.items() if "multiply" in name)
        assert multiply_op.description == "Multiply two numbers."

    def test_signature_extracted(self) -> None:
        skill = _skill()
        multiply_op = next(op for name, op in skill.operations.items() if "multiply" in name)
        assert multiply_op.signature is not None
        assert "a" in multiply_op.signature
        assert "b" in multiply_op.signature

    def test_tags_include_type_and_submodule(self) -> None:
        skill = _skill()
        multiply_op = next(op for name, op in skill.operations.items() if "multiply" in name)
        assert "function" in multiply_op.tags
        assert "alpha" in multiply_op.tags

    def test_default_permission_propagated(self) -> None:
        skill = module(fix_pkg, default_permission="deny")
        for op in skill.operations.values():
            assert op.default_permission == "deny"


# ---------------------------------------------------------------------------
# Handler execution
# ---------------------------------------------------------------------------


class TestHandlers:
    @pytest.mark.asyncio
    async def test_function_handler_works(self) -> None:
        skill = module(fix_pkg, name="fix")
        agent = _agent(skill)
        # Find the multiply op's qualified name
        multiply_qn = next(
            f"fix.{name}" for name in skill.operations if "multiply" in name
        )
        result = await agent.call(multiply_qn, {"a": 3, "b": 4})
        assert result == 12

    @pytest.mark.asyncio
    async def test_class_constructor_returns_instance(self) -> None:
        skill = module(fix_pkg, name="fix")
        agent = _agent(skill)
        widget_qn = next(
            f"fix.{name}" for name in skill.operations if "widget" in name
        )
        result = await agent.call(widget_qn, {"name": "test"})
        assert result.name == "test"
        assert result.size == 10

    @pytest.mark.asyncio
    async def test_works_in_code_mode(self) -> None:
        skill = module(fix_pkg, name="fix")
        agent = _agent(skill)
        widget_qn = next(
            f"fix.{name}" for name in skill.operations if "widget" in name
        )
        code = f"""\
w = await agent.call("{widget_qn}", {{"name": "bot", "size": 5}})
w.describe()
"""
        result = await agent.run(code)
        assert result.result == "bot (size=5)"

    @pytest.mark.asyncio
    async def test_deduplicates_reexports(self) -> None:
        skill = _skill()
        # alpha.add is re-exported in __init__.py — should appear only once
        add_handlers = [
            op.handler for name, op in skill.operations.items() if "add" in name
        ]
        handler_ids = [id(h) for h in add_handlers]
        assert len(handler_ids) == len(set(handler_ids)), "Duplicate handler ids found"


# ---------------------------------------------------------------------------
# Slugify
# ---------------------------------------------------------------------------


class TestSlugify:
    def test_camel_to_snake(self) -> None:
        assert _slugify("RandomForestClassifier") == "random_forest_classifier"

    def test_already_snake(self) -> None:
        assert _slugify("my_function") == "my_function"
