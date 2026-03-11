"""List available fairlead examples."""

EXAMPLES = {
    "getting_started": "Create a Fairlead instance, register skills, call typed operations, search",
    "permissions": "Permission rules, wildcards, on_permission_request callback",
    "code_mode": "Chain .call() invocations with branching, looping, variables",
    "mcp_server": "Expose fairlead as an MCP server for Claude Desktop",
    "chat_client": "Terminal chat app using fairlead's MCP server + Anthropic API",
    "custom_skills": "Define domain-specific skills with define_skill()",
    "openapi_skill": "Turn any OpenAPI spec into a fairlead skill",
    "github_openapi": "Real API (GitHub) via openapi() — discovery, auth headers, typed calls",
    "github_code_mode": "Multi-step workflows: search + rank, org scan, repo comparison",
    "github_explorer": "Combine OpenAPI + custom skill + Code Mode in one workflow",
    "github_mcp_server": "Serve GitHub API to Claude Desktop with permission controls",
}


def main() -> None:
    print("Available fairlead examples:\n")
    for name, description in EXAMPLES.items():
        print(f"  python -m fairlead.examples.{name}")
        print(f"    {description}\n")


if __name__ == "__main__":
    main()
