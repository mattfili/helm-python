from __future__ import annotations

import asyncio
import json
import urllib.request
import urllib.error
from dataclasses import dataclass

from helm._skill import define_skill
from helm._types import OperationDef, Skill


@dataclass(frozen=True)
class RequestOptions:
    method: str | None = None
    headers: dict[str, str] | None = None
    body: str | None = None
    timeout: float | None = None


@dataclass(frozen=True)
class HttpResponse:
    status: int
    status_text: str
    headers: dict[str, str]
    body: str


@dataclass(frozen=True)
class JsonResponse:
    status: int
    status_text: str
    headers: dict[str, str]
    data: object


# Map HTTP status codes to reason phrases
_STATUS_PHRASES: dict[int, str] = {
    200: "OK",
    201: "Created",
    204: "No Content",
    301: "Moved Permanently",
    302: "Found",
    304: "Not Modified",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    500: "Internal Server Error",
    502: "Bad Gateway",
    503: "Service Unavailable",
}


def _headers_to_dict(headers: list[tuple[str, str]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in headers:
        result[key.lower()] = value
    return result


def _do_request(url: str, opts: RequestOptions | None = None) -> tuple[int, str, dict[str, str], bytes]:
    method = (opts.method if opts else None) or "GET"
    body_bytes = opts.body.encode("utf-8") if opts and opts.body else None
    timeout = (opts.timeout if opts else None) or 30.0

    # Convert timeout from ms to seconds if > 1000 (matching TS convention)
    if timeout > 1000:
        timeout = timeout / 1000.0

    req = urllib.request.Request(url, data=body_bytes, method=method)

    if opts and opts.headers:
        for key, value in opts.headers.items():
            req.add_header(key, value)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status = response.status
            reason = response.reason or _STATUS_PHRASES.get(status, "")
            headers = _headers_to_dict(list(response.getheaders()))
            data = response.read()
            return status, reason, headers, data
    except urllib.error.HTTPError as e:
        status = e.code
        reason = e.reason or _STATUS_PHRASES.get(status, "")
        headers = _headers_to_dict(list(e.headers.items())) if e.headers else {}
        data = e.read()
        return status, reason, headers, data


def http() -> Skill:
    async def fetch(
        url: str, opts: RequestOptions | None = None
    ) -> HttpResponse:
        status, reason, headers, data = await asyncio.to_thread(
            _do_request, url, opts
        )
        return HttpResponse(
            status=status,
            status_text=reason,
            headers=headers,
            body=data.decode("utf-8"),
        )

    async def json_fetch(
        url: str, opts: RequestOptions | None = None
    ) -> JsonResponse:
        status, reason, headers, data = await asyncio.to_thread(
            _do_request, url, opts
        )
        parsed = json.loads(data.decode("utf-8"))
        return JsonResponse(
            status=status,
            status_text=reason,
            headers=headers,
            data=parsed,
        )

    return define_skill(
        name="http",
        description="HTTP client for making web requests and fetching data",
        operations={
            "fetch": OperationDef(
                description="Make an HTTP request and return the response",
                signature="(url: str, opts: RequestOptions | None = None) -> HttpResponse",
                default_permission="ask",
                tags=["http", "request", "fetch", "web", "api", "url", "get", "post"],
                handler=fetch,
            ),
            "json": OperationDef(
                description="Fetch a URL and parse the response as JSON",
                signature="(url: str, opts: RequestOptions | None = None) -> JsonResponse",
                default_permission="ask",
                tags=["http", "json", "api", "fetch", "rest", "data"],
                handler=json_fetch,
            ),
        },
    )
