"""Custom Skills — define domain-specific operations with define_skill()."""

import asyncio

from fairlead import Fairlead, FairleadOptions, fs

from .weather_skill import weather


async def main() -> None:
    agent = Fairlead(FairleadOptions(default_permission="allow"))

    # Register built-in and custom skills together
    agent.use(fs()).use(weather())

    # --- Use custom skill via attribute access ---
    print("=== Current Weather ===")
    sf = await agent.weather.get(city="San Francisco")
    print(f"{sf['city']}: {sf['temp_f']}°F, {sf['condition']}")

    ny = await agent.weather.get(city="New York")
    print(f"{ny['city']}: {ny['temp_f']}°F, {ny['condition']}")

    # --- Sync handler works too ---
    print("\n=== Temperature Conversion ===")
    converted = await agent.weather.convert(temp_f=sf["temp_f"])
    print(f"{converted['fahrenheit']}°F = {converted['celsius']}°C")

    # --- Use .call() for dynamic dispatch ---
    print("\n=== Forecast (via .call()) ===")
    forecast = await agent.call("weather.forecast", {"city": "London", "days": 5})
    print(f"{forecast['city']} — {forecast['days']}-day forecast:")
    for day in forecast["forecast"]:
        print(f"  Day {day['day']}: {day['condition']}, high {day['high_f']}°F")

    # --- Discover custom operations via search ---
    print("\n=== Search for 'temperature' ===")
    results = agent.search("temperature")
    for r in results:
        print(f"  {r.qualified_name}: {r.description}")

    # --- Compose custom + built-in ---
    print("\n=== Composing Custom + Built-in ===")
    listing = await agent.fs.readdir(path=".")
    file_count = sum(1 for e in listing["entries"] if e.is_file)
    weather_data = await agent.weather.get(city="San Francisco")
    print(f"This directory has {file_count} files and it's {weather_data['condition']} in SF")


if __name__ == "__main__":
    asyncio.run(main())
