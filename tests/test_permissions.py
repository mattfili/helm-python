from fairlead import PermissionDeniedError, resolve_permission


class TestResolvePermission:
    def test_returns_exact_policy_match_first(self) -> None:
        result = resolve_permission(
            "git.status", "deny", {"git.status": "allow"}, "ask"
        )
        assert result == "allow"

    def test_returns_wildcard_policy_match_second(self) -> None:
        result = resolve_permission(
            "git.status", "deny", {"git.*": "allow"}, "ask"
        )
        assert result == "allow"

    def test_returns_operation_default_third(self) -> None:
        result = resolve_permission("git.status", "deny", {}, "ask")
        assert result == "deny"

    def test_returns_global_default_last(self) -> None:
        result = resolve_permission("git.status", None, {}, "ask")
        assert result == "ask"

    def test_exact_match_takes_precedence_over_wildcard(self) -> None:
        result = resolve_permission(
            "git.push", None, {"git.*": "allow", "git.push": "deny"}, "ask"
        )
        assert result == "deny"

    def test_handles_names_without_dots_gracefully(self) -> None:
        result = resolve_permission("nodot", "allow", {}, "ask")
        assert result == "allow"


class TestPermissionDeniedError:
    def test_has_correct_message(self) -> None:
        err = PermissionDeniedError("git.push")
        assert str(err) == "Permission denied: git.push"
        assert isinstance(err, Exception)

    def test_has_qualified_name(self) -> None:
        err = PermissionDeniedError("git.push")
        assert err.qualified_name == "git.push"
