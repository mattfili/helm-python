"""OpenAPI Skill — turn any OpenAPI spec into fairlead operations."""

import asyncio
from pathlib import Path

from fairlead import Fairlead, FairleadOptions, openapi


async def main() -> None:
    agent = Fairlead(FairleadOptions(default_permission="allow"))

    # Load the Petstore spec from a local file
    spec_path = str(Path(__file__).parent / "petstore_spec.json")
    petstore = openapi(
        spec_path,
        name="petstore",
        default_permission="allow",
    )
    agent.use(petstore)

    # --- Discover auto-generated operations ---
    print("=== All Petstore Operations ===")
    results = agent.search("pet")
    for r in results:
        print(f"  {r.qualified_name} {r.signature}")
        print(f"    {r.description}")
        print(f"    tags: {r.tags}")
        print()

    # --- Call an operation ---
    print("=== Find Pets by Status ===")
    try:
        result = await agent.call(
            "petstore.find_pets_by_status",
            {"query": {"status": "available"}},
        )
        status_code = result["status"]
        print(f"  HTTP {status_code}")
        if isinstance(result["data"], list):
            print(f"  Found {len(result['data'])} pets")
        else:
            print(f"  Response: {result['data']}")
    except Exception as e:
        print(f"  Request failed (expected if API is down): {e}")

    # --- Get inventory ---
    print("\n=== Store Inventory ===")
    try:
        result = await agent.call("petstore.get_inventory")
        print(f"  HTTP {result['status']}")
        print(f"  Data: {result['data']}")
    except Exception as e:
        print(f"  Request failed (expected if API is down): {e}")

    # --- Search by tag ---
    print("\n=== Search for 'store' operations ===")
    results = agent.search("store")
    for r in results:
        print(f"  {r.qualified_name}: {r.description}")


if __name__ == "__main__":
    asyncio.run(main())
