import pytest

from fairlead import (
    FairleadOptions,
    OperationDef,
    PermissionDeniedError,
    create_fairlead,
    define_skill,
)


test_skill = define_skill(
    name="test",
    description="A test skill",
    operations={
        "greet": OperationDef(
            description="Says hello",
            default_permission="allow",
            tags=["greeting"],
            handler=lambda name: f"hello {name}",
        ),
        "secret": OperationDef(
            description="A secret operation",
            default_permission="deny",
            handler=lambda: "secret",
        ),
        "askable": OperationDef(
            description="Requires permission",
            handler=lambda: "asked",
        ),
    },
)


class TestCreateHelm:
    def test_creates_an_instance(self) -> None:
        agent = create_fairlead()
        assert agent is not None
        assert callable(agent.use)
        assert callable(agent.search)

    def test_registers_a_skill(self) -> None:
        agent = create_fairlead().use(test_skill)
        assert agent.test is not None
        assert callable(agent.test.greet)

    def test_chains_use_calls(self) -> None:
        other = define_skill(
            name="other",
            description="Another skill",
            operations={
                "ping": OperationDef(
                    description="Ping",
                    default_permission="allow",
                    handler=lambda: "pong",
                ),
            },
        )

        agent = (
            create_fairlead(FairleadOptions(default_permission="allow"))
            .use(test_skill)
            .use(other)
        )

        assert agent.test is not None
        assert agent.other is not None


class TestOperationCalls:
    @pytest.mark.asyncio
    async def test_calls_allowed_operation(self) -> None:
        agent = create_fairlead().use(test_skill)
        result = await agent.test.greet("world")
        assert result == "hello world"

    @pytest.mark.asyncio
    async def test_throws_for_denied_operations(self) -> None:
        agent = create_fairlead().use(test_skill)
        with pytest.raises(PermissionDeniedError):
            await agent.test.secret()

    @pytest.mark.asyncio
    async def test_calls_on_permission_request(self) -> None:
        calls: list[tuple[str, list[object]]] = []

        def on_request(op: str, args: list[object]) -> bool:
            calls.append((op, args))
            return True

        agent = create_fairlead(
            FairleadOptions(default_permission="ask", on_permission_request=on_request)
        ).use(test_skill)

        result = await agent.test.askable()
        assert result == "asked"
        assert calls == [("test.askable", [])]

    @pytest.mark.asyncio
    async def test_throws_when_permission_denied(self) -> None:
        agent = create_fairlead(
            FairleadOptions(
                default_permission="ask",
                on_permission_request=lambda _op, _args: False,
            )
        ).use(test_skill)

        with pytest.raises(PermissionDeniedError):
            await agent.test.askable()

    @pytest.mark.asyncio
    async def test_throws_when_no_permission_callback(self) -> None:
        agent = create_fairlead(FairleadOptions(default_permission="ask")).use(test_skill)
        with pytest.raises(PermissionDeniedError):
            await agent.test.askable()


class TestSearch:
    def test_searches_registered_operations(self) -> None:
        agent = create_fairlead().use(test_skill)
        results = agent.search("greet")
        assert len(results) > 0
        assert results[0].qualified_name == "test.greet"

    def test_returns_empty_for_no_matches(self) -> None:
        agent = create_fairlead().use(test_skill)
        results = agent.search("nonexistent_xyz")
        assert results == []


class TestPermissionPolicy:
    @pytest.mark.asyncio
    async def test_overrides_operation_default(self) -> None:
        agent = create_fairlead(
            FairleadOptions(permissions={"test.secret": "allow"})
        ).use(test_skill)
        result = await agent.test.secret()
        assert result == "secret"

    @pytest.mark.asyncio
    async def test_wildcard_applies_to_all_ops(self) -> None:
        agent = create_fairlead(
            FairleadOptions(permissions={"test.*": "allow"})
        ).use(test_skill)
        result = await agent.test.secret()
        assert result == "secret"
