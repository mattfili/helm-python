from __future__ import annotations

import asyncio
import json
import re
import urllib.request
from typing import Any

from helm._skill import define_skill
from helm._types import OperationDef, Permission, Skill


def openapi(
    spec: str | dict[str, Any],
    *,
    name: str,
    base_url: str | None = None,
    headers: dict[str, str] | None = None,
    default_permission: Permission | None = None,
    timeout: float = 30.0,
) -> Skill:
    """Create a Skill from an OpenAPI spec.

    Args:
        spec: OpenAPI spec as a URL, file path, JSON string, or pre-parsed dict.
        name: Skill name.
        base_url: Override the base URL from the spec.
        headers: Default headers to send with every request.
        default_permission: Default permission for all operations.
        timeout: Request timeout in seconds.
    """
    parsed = _load_spec(spec)
    _resolve_refs(parsed, parsed)

    servers = parsed.get("servers", [])
    resolved_base_url = base_url or (servers[0]["url"] if servers else "")
    resolved_base_url = resolved_base_url.rstrip("/")

    operations: dict[str, OperationDef] = {}
    paths: dict[str, Any] = parsed.get("paths", {})

    for path, path_item in paths.items():
        for method in ("get", "post", "put", "patch", "delete", "head", "options"):
            if method not in path_item:
                continue
            endpoint = path_item[method]

            op_name = _operation_name(endpoint, method, path)
            description = endpoint.get("summary") or endpoint.get("description") or f"{method.upper()} {path}"
            signature = _build_signature(endpoint, path, method)
            tags = list(endpoint.get("tags", [])) + [method]

            handler = _make_handler(
                method=method,
                path=path,
                endpoint=endpoint,
                base_url=resolved_base_url,
                default_headers=headers or {},
                timeout=timeout,
            )

            operations[op_name] = OperationDef(
                description=description,
                handler=handler,
                signature=signature,
                tags=tags,
                default_permission=default_permission,
            )

    return define_skill(
        name=name,
        description=parsed.get("info", {}).get("description", f"OpenAPI skill: {name}"),
        operations=operations,
    )


def _load_spec(spec: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(spec, dict):
        return spec

    # Try as JSON string
    text = spec.strip()
    if text.startswith("{"):
        return json.loads(text)  # type: ignore[no-any-return]

    # Try as URL
    if text.startswith("http://") or text.startswith("https://"):
        with urllib.request.urlopen(text) as resp:
            data = resp.read().decode("utf-8")
        return _parse_spec_text(data, text)

    # Try as file path
    with open(text) as f:
        data = f.read()
    return _parse_spec_text(data, text)


def _parse_spec_text(data: str, source: str) -> dict[str, Any]:
    text = data.strip()
    if text.startswith("{"):
        return json.loads(text)  # type: ignore[no-any-return]
    # Try YAML
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as e:
        raise ImportError(
            "PyYAML is required to parse YAML OpenAPI specs. "
            "Install it with: pip install pyyaml"
        ) from e
    return yaml.safe_load(text)  # type: ignore[no-any-return]


def _resolve_refs(node: Any, root: dict[str, Any]) -> Any:
    if isinstance(node, dict):
        if "$ref" in node:
            ref_path = node["$ref"]
            if ref_path.startswith("#/"):
                resolved = _follow_ref(ref_path, root)
                # Replace in place for dict mutations
                node.clear()
                node.update(resolved)
                _resolve_refs(node, root)
            return node
        for value in node.values():
            _resolve_refs(value, root)
    elif isinstance(node, list):
        for item in node:
            _resolve_refs(item, root)
    return node


def _follow_ref(ref_path: str, root: dict[str, Any]) -> dict[str, Any]:
    parts = ref_path.lstrip("#/").split("/")
    current: Any = root
    for part in parts:
        part = part.replace("~1", "/").replace("~0", "~")
        current = current[part]
    return current  # type: ignore[no-any-return]


def _operation_name(endpoint: dict[str, Any], method: str, path: str) -> str:
    op_id = endpoint.get("operationId")
    if op_id:
        return _slugify(op_id)
    return f"{method}_{_slugify(path)}"


def _slugify(s: str) -> str:
    s = re.sub(r"[{}]", "", s)
    # Insert underscore before uppercase letters (camelCase -> camel_Case)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s)
    s = s.strip("_").lower()
    return s


def _build_signature(endpoint: dict[str, Any], path: str, method: str) -> str:
    params: list[str] = []

    # Path parameters
    path_param_names = re.findall(r"\{(\w+)\}", path)
    all_params = endpoint.get("parameters", [])

    for pname in path_param_names:
        param_def = next((p for p in all_params if p.get("name") == pname and p.get("in") == "path"), None)
        ptype = "str"
        if param_def:
            schema = param_def.get("schema", {})
            ptype = _schema_to_type(schema)
        params.append(f"{pname}: {ptype}")

    # Query params -> query dict
    query_params = [p for p in all_params if p.get("in") == "query"]
    if query_params:
        params.append("query: dict | None = None")

    # Request body
    if "requestBody" in endpoint:
        params.append("body: dict | None = None")

    return f"({', '.join(params)}) -> dict"


def _schema_to_type(schema: dict[str, Any]) -> str:
    t = schema.get("type", "")
    if t == "integer":
        return "int"
    if t == "number":
        return "float"
    if t == "boolean":
        return "bool"
    if t == "array":
        return "list"
    if t == "object":
        return "dict"
    return "str"


def _make_handler(
    *,
    method: str,
    path: str,
    endpoint: dict[str, Any],
    base_url: str,
    default_headers: dict[str, str],
    timeout: float,
) -> Any:
    path_param_names = re.findall(r"\{(\w+)\}", path)
    has_query = any(p.get("in") == "query" for p in endpoint.get("parameters", []))
    has_body = "requestBody" in endpoint

    async def handler(**kwargs: Any) -> dict[str, Any]:
        # Substitute path params
        url_path = path
        for pname in path_param_names:
            value = kwargs.pop(pname, "")
            url_path = url_path.replace(f"{{{pname}}}", str(value))

        url = f"{base_url}{url_path}"

        # Query params
        query = kwargs.pop("query", None)
        if query:
            qs = "&".join(f"{k}={v}" for k, v in query.items())
            url = f"{url}?{qs}"

        # Body
        body = kwargs.pop("body", None)
        body_bytes = json.dumps(body).encode("utf-8") if body else None

        # Build request
        req = urllib.request.Request(url, data=body_bytes, method=method.upper())
        for k, v in default_headers.items():
            req.add_header(k, v)
        if body_bytes:
            req.add_header("Content-Type", "application/json")

        def _do() -> dict[str, Any]:
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    data = resp.read().decode("utf-8")
                    try:
                        parsed = json.loads(data)
                    except json.JSONDecodeError:
                        parsed = data
                    return {"status": resp.status, "data": parsed}
            except urllib.error.HTTPError as e:
                data = e.read().decode("utf-8")
                try:
                    parsed = json.loads(data)
                except json.JSONDecodeError:
                    parsed = data
                return {"status": e.code, "data": parsed}

        return await asyncio.to_thread(_do)

    return handler
