from helm._search import search
from helm._types import OperationDef, Skill


def _noop() -> None:
    pass


git_skill = Skill(
    name="git",
    description="Git operations",
    operations={
        "status": OperationDef(
            description="Show the working tree status",
            tags=["vcs", "info"],
            default_permission="allow",
            handler=_noop,
        ),
        "push": OperationDef(
            description="Push commits to remote",
            tags=["vcs", "write"],
            default_permission="ask",
            handler=_noop,
        ),
        "log": OperationDef(
            description="Show commit logs",
            tags=["vcs", "info"],
            handler=_noop,
        ),
    },
)

fs_skill = Skill(
    name="fs",
    description="File system operations",
    operations={
        "read_file": OperationDef(
            description="Read a file",
            tags=["file", "read"],
            default_permission="allow",
            handler=_noop,
        ),
        "write_file": OperationDef(
            description="Write a file",
            tags=["file", "write"],
            default_permission="ask",
            handler=_noop,
        ),
    },
)


def _make_registry(skills: list[Skill]) -> dict[str, Skill]:
    return {s.name: s for s in skills}


class TestSearch:
    def setup_method(self) -> None:
        self.registry = _make_registry([git_skill, fs_skill])

    def test_finds_exact_qualified_name_match(self) -> None:
        results = search("git.status", self.registry, {}, "ask")
        assert results[0].qualified_name == "git.status"

    def test_matches_partial_qualified_name(self) -> None:
        results = search("git", self.registry, {}, "ask")
        assert all(r.skill == "git" for r in results)
        assert len(results) == 3

    def test_matches_by_description(self) -> None:
        results = search("commit", self.registry, {}, "ask")
        assert any(r.qualified_name == "git.push" for r in results)
        assert any(r.qualified_name == "git.log" for r in results)

    def test_matches_by_tag(self) -> None:
        results = search("vcs", self.registry, {}, "ask")
        assert all(r.skill == "git" for r in results)

    def test_returns_empty_for_no_matches(self) -> None:
        results = search("nonexistent_xyz", self.registry, {}, "ask")
        assert results == []

    def test_is_case_insensitive(self) -> None:
        results = search("GIT.STATUS", self.registry, {}, "ask")
        assert results[0].qualified_name == "git.status"

    def test_resolves_permissions_from_policy(self) -> None:
        results = search(
            "git.push", self.registry, {"git.push": "deny"}, "ask"
        )
        assert results[0].permission == "deny"

    def test_ranks_exact_name_higher_than_description(self) -> None:
        results = search("read_file", self.registry, {}, "ask")
        assert results[0].qualified_name == "fs.read_file"

    def test_passes_signature_through(self) -> None:
        math_skill = Skill(
            name="math",
            description="Math operations",
            operations={
                "add": OperationDef(
                    description="Add two numbers",
                    signature="(a: int, b: int) -> int",
                    handler=_noop,
                ),
                "sub": OperationDef(
                    description="Subtract two numbers",
                    handler=_noop,
                ),
            },
        )
        reg = _make_registry([math_skill])
        results = search("math", reg, {}, "ask")
        add = next(r for r in results if r.operation == "add")
        sub = next(r for r in results if r.operation == "sub")
        assert add.signature == "(a: int, b: int) -> int"
        assert sub.signature is None
