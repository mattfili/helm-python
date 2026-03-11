import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import pytest

from fairlead import FairleadOptions, create_fairlead
from fairlead.skills import http
from fairlead.skills._http import RequestOptions


class _TestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/text":
            self.send_response(200)
            self.send_header("content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"hello text")
        elif self.path == "/json":
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"message": "hello json"}).encode())
        elif self.path == "/status/404":
            self.send_response(404)
            self.send_header("content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"not found")
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.end_headers()
        response = {
            "method": "POST",
            "headers": dict(self.headers),
            "body": body,
        }
        self.wfile.write(json.dumps(response).encode())

    def log_message(self, format: str, *args: object) -> None:
        pass  # Suppress log output during tests


@pytest.fixture(scope="module")
def base_url():
    server = HTTPServer(("127.0.0.1", 0), _TestHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


def agent():
    return create_fairlead(FairleadOptions(permissions={"http.*": "allow"})).use(http())


class TestHttpSkill:
    @pytest.mark.asyncio
    async def test_fetches_text(self, base_url: str) -> None:
        result = await agent().http.fetch(f"{base_url}/text")
        assert result.status == 200
        assert result.body == "hello text"
        assert result.headers["content-type"] == "text/plain"

    @pytest.mark.asyncio
    async def test_fetches_json(self, base_url: str) -> None:
        result = await agent().http.json(f"{base_url}/json")
        assert result.status == 200
        assert result.data == {"message": "hello json"}

    @pytest.mark.asyncio
    async def test_post_with_body(self, base_url: str) -> None:
        result = await agent().http.json(
            f"{base_url}/echo",
            RequestOptions(
                method="POST",
                headers={"content-type": "application/json"},
                body=json.dumps({"key": "value"}),
            ),
        )
        assert result.status == 200
        assert result.data["method"] == "POST"
        assert result.data["body"] == '{"key": "value"}'

    @pytest.mark.asyncio
    async def test_handles_non_200(self, base_url: str) -> None:
        result = await agent().http.fetch(f"{base_url}/status/404")
        assert result.status == 404
        assert result.body == "not found"

    @pytest.mark.asyncio
    async def test_includes_headers(self, base_url: str) -> None:
        result = await agent().http.fetch(f"{base_url}/json")
        assert result.headers["content-type"] == "application/json"

    @pytest.mark.asyncio
    async def test_timeout_on_fetch(self, base_url: str) -> None:
        result = await agent().http.fetch(
            f"{base_url}/text", RequestOptions(timeout=5000)
        )
        assert result.status == 200
        assert result.body == "hello text"

    @pytest.mark.asyncio
    async def test_timeout_on_json(self, base_url: str) -> None:
        result = await agent().http.json(
            f"{base_url}/json", RequestOptions(timeout=5000)
        )
        assert result.status == 200
        assert result.data == {"message": "hello json"}
