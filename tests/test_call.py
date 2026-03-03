import pytest

from helm import (
    HelmOptions,
    OperationDef,
    PermissionDeniedError,
    create_helm,
    define_skill,
)


def _make_skill():
    return define_skill(
        name="math",
        description="Math operations",
        operations={
            "add": OperationDef(
                description="Add two numbers",
                signature="(a: int, b: int) -> int",
                default_permission="allow",
                handler=lambda a, b: a + b,
            ),
            "greet": OperationDef(
                description="Greet someone",
                signature="(name: str, greeting: str = 'hello') -> str",
                default_permission="allow",
                handler=lambda name, greeting="hello": f"{greeting} {name}",
            ),
            "secret": OperationDef(
                description="Secret op",
                default_permission="deny",
                handler=lambda: "secret",
            ),
        },
    )


class TestCall:
    @pytest.mark.asyncio
    async def test_call_with_kwargs(self) -> None:
        agent = create_helm().use(_make_skill())
        result = await agent.call("math.add", {"a": 3, "b": 4})
        assert result == 7

    @pytest.mark.asyncio
    async def test_call_with_default_kwargs(self) -> None:
        agent = create_helm().use(_make_skill())
        result = await agent.call("math.greet", {"name": "world"})
        assert result == "hello world"

    @pytest.mark.asyncio
    async def test_call_with_override_kwargs(self) -> None:
        agent = create_helm().use(_make_skill())
        result = await agent.call("math.greet", {"name": "world", "greeting": "hi"})
        assert result == "hi world"

    @pytest.mark.asyncio
    async def test_call_with_none_kwargs(self) -> None:
        agent = create_helm().use(_make_skill())
        result = await agent.call("math.greet", {"name": "world"})
        assert result == "hello world"

    @pytest.mark.asyncio
    async def test_call_invalid_format(self) -> None:
        agent = create_helm().use(_make_skill())
        with pytest.raises(ValueError, match="Invalid qualified name"):
            await agent.call("nope")

    @pytest.mark.asyncio
    async def test_call_unknown_skill(self) -> None:
        agent = create_helm().use(_make_skill())
        with pytest.raises(AttributeError, match="not registered"):
            await agent.call("unknown.op")

    @pytest.mark.asyncio
    async def test_call_unknown_operation(self) -> None:
        agent = create_helm().use(_make_skill())
        with pytest.raises(AttributeError, match="not found"):
            await agent.call("math.unknown")

    @pytest.mark.asyncio
    async def test_call_enforces_permissions(self) -> None:
        agent = create_helm().use(_make_skill())
        with pytest.raises(PermissionDeniedError):
            await agent.call("math.secret")

    @pytest.mark.asyncio
    async def test_call_respects_policy_override(self) -> None:
        agent = create_helm(
            HelmOptions(permissions={"math.secret": "allow"})
        ).use(_make_skill())
        result = await agent.call("math.secret")
        assert result == "secret"
