import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import pytest

from fairlead import FairleadOptions, PermissionDeniedError, create_fairlead
from fairlead.skills._openapi import openapi, _slugify, _operation_name, _resolve_refs


PETSTORE_SPEC: dict = {
    "openapi": "3.0.0",
    "info": {
        "title": "Petstore",
        "description": "A sample pet store API",
        "version": "1.0.0",
    },
    "servers": [{"url": "http://localhost:{{PORT}}"}],
    "paths": {
        "/pets": {
            "get": {
                "operationId": "listPets",
                "summary": "List all pets",
                "tags": ["pets"],
                "parameters": [
                    {
                        "name": "limit",
                        "in": "query",
                        "schema": {"type": "integer"},
                    }
                ],
                "responses": {"200": {"description": "A list of pets"}},
            },
            "post": {
                "operationId": "createPet",
                "summary": "Create a pet",
                "tags": ["pets"],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                },
                            }
                        }
                    }
                },
                "responses": {"201": {"description": "Pet created"}},
            },
        },
        "/pets/{petId}": {
            "get": {
                "operationId": "getPet",
                "summary": "Get a pet by ID",
                "tags": ["pets"],
                "parameters": [
                    {
                        "name": "petId",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer"},
                    }
                ],
                "responses": {"200": {"description": "A pet"}},
            },
        },
    },
}


SPEC_WITH_REFS: dict = {
    "openapi": "3.0.0",
    "info": {"title": "Refs Test", "version": "1.0.0"},
    "components": {
        "schemas": {
            "Pet": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                },
            }
        }
    },
    "paths": {
        "/pets": {
            "post": {
                "operationId": "createPet",
                "summary": "Create a pet",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Pet"}
                        }
                    }
                },
                "responses": {"201": {"description": "Created"}},
            }
        }
    },
}


def _make_spec(port: int) -> dict:
    """Create a copy of PETSTORE_SPEC with the actual server port."""
    import copy
    spec = copy.deepcopy(PETSTORE_SPEC)
    spec["servers"] = [{"url": f"http://localhost:{port}"}]
    return spec


class _PetHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/pets" or self.path.startswith("/pets?"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps([{"id": 1, "name": "Fido"}]).encode())
        elif self.path.startswith("/pets/"):
            pet_id = self.path.split("/")[-1]
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"id": int(pet_id), "name": "Fido"}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"id": 2, **body}).encode())

    def log_message(self, format: str, *args: object) -> None:
        pass  # Suppress log output


@pytest.fixture
def pet_server():
    server = HTTPServer(("127.0.0.1", 0), _PetHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield port
    server.shutdown()


class TestOpenApiSkillCreation:
    def test_creates_skill_from_dict(self) -> None:
        skill = openapi(_make_spec(9999), name="petstore")
        assert skill.name == "petstore"
        assert skill.description == "A sample pet store API"

    def test_generates_operations_from_spec(self) -> None:
        skill = openapi(_make_spec(9999), name="petstore")
        assert "list_pets" in skill.operations
        assert "create_pet" in skill.operations
        assert "get_pet" in skill.operations

    def test_operation_descriptions(self) -> None:
        skill = openapi(_make_spec(9999), name="petstore")
        assert skill.operations["list_pets"].description == "List all pets"
        assert skill.operations["create_pet"].description == "Create a pet"
        assert skill.operations["get_pet"].description == "Get a pet by ID"

    def test_operation_tags(self) -> None:
        skill = openapi(_make_spec(9999), name="petstore")
        tags = skill.operations["list_pets"].tags
        assert "pets" in tags
        assert "get" in tags

    def test_operation_signatures(self) -> None:
        skill = openapi(_make_spec(9999), name="petstore")
        assert "query: dict | None = None" in (skill.operations["list_pets"].signature or "")
        assert "petId: int" in (skill.operations["get_pet"].signature or "")
        assert "body: dict | None = None" in (skill.operations["create_pet"].signature or "")

    def test_default_permission(self) -> None:
        skill = openapi(_make_spec(9999), name="petstore", default_permission="deny")
        assert skill.operations["list_pets"].default_permission == "deny"

    def test_base_url_override(self) -> None:
        skill = openapi(
            _make_spec(9999),
            name="petstore",
            base_url="http://override:1234",
        )
        # Skill is created, operations exist
        assert len(skill.operations) == 3


class TestOperationNaming:
    def test_uses_operation_id(self) -> None:
        assert _operation_name({"operationId": "listPets"}, "get", "/pets") == "list_pets"

    def test_camel_case_to_snake(self) -> None:
        assert _slugify("getUserById") == "get_user_by_id"

    def test_falls_back_to_method_path(self) -> None:
        assert _operation_name({}, "get", "/pets/{petId}") == "get_pets_pet_id"


class TestRefResolution:
    def test_resolves_internal_refs(self) -> None:
        import copy
        spec = copy.deepcopy(SPEC_WITH_REFS)
        _resolve_refs(spec, spec)

        schema = (
            spec["paths"]["/pets"]["post"]["requestBody"]["content"]["application/json"]["schema"]
        )
        assert schema["type"] == "object"
        assert "name" in schema["properties"]


class TestHttpHandlers:
    @pytest.mark.asyncio
    async def test_list_pets(self, pet_server: int) -> None:
        skill = openapi(_make_spec(pet_server), name="petstore", default_permission="allow")
        agent = create_fairlead(FairleadOptions(default_permission="allow")).use(skill)
        result = await agent.call("petstore.list_pets")
        assert result["status"] == 200
        assert isinstance(result["data"], list)

    @pytest.mark.asyncio
    async def test_get_pet_by_id(self, pet_server: int) -> None:
        skill = openapi(_make_spec(pet_server), name="petstore", default_permission="allow")
        agent = create_fairlead(FairleadOptions(default_permission="allow")).use(skill)
        result = await agent.call("petstore.get_pet", {"petId": 1})
        assert result["status"] == 200
        assert result["data"]["id"] == 1

    @pytest.mark.asyncio
    async def test_create_pet(self, pet_server: int) -> None:
        skill = openapi(_make_spec(pet_server), name="petstore", default_permission="allow")
        agent = create_fairlead(FairleadOptions(default_permission="allow")).use(skill)
        result = await agent.call("petstore.create_pet", {"body": {"name": "Rex"}})
        assert result["status"] == 201
        assert result["data"]["name"] == "Rex"

    @pytest.mark.asyncio
    async def test_query_params(self, pet_server: int) -> None:
        skill = openapi(_make_spec(pet_server), name="petstore", default_permission="allow")
        agent = create_fairlead(FairleadOptions(default_permission="allow")).use(skill)
        result = await agent.call("petstore.list_pets", {"query": {"limit": "10"}})
        assert result["status"] == 200

    @pytest.mark.asyncio
    async def test_permission_enforcement(self, pet_server: int) -> None:
        skill = openapi(_make_spec(pet_server), name="petstore", default_permission="deny")
        agent = create_fairlead().use(skill)
        with pytest.raises(PermissionDeniedError):
            await agent.call("petstore.list_pets")
