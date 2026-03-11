"""A custom weather skill — demonstrates define_skill() and OperationDef."""

from __future__ import annotations

from helm import define_skill, OperationDef, Skill


# Async handler — most handlers should be async for I/O operations
async def get_weather(city: str) -> dict[str, object]:
    """Simulate fetching weather data. Replace with a real API call."""
    # In a real skill, you'd call a weather API here
    mock_data: dict[str, dict[str, object]] = {
        "san francisco": {"temp_f": 62, "condition": "foggy", "humidity": 85},
        "new york": {"temp_f": 78, "condition": "sunny", "humidity": 55},
        "london": {"temp_f": 58, "condition": "rainy", "humidity": 90},
    }
    data = mock_data.get(city.lower(), {"temp_f": 70, "condition": "clear", "humidity": 50})
    return {"city": city, **data}


# Sync handler — works fine for CPU-bound operations
def convert_temp(temp_f: float) -> dict[str, float]:
    """Convert Fahrenheit to Celsius."""
    return {"fahrenheit": temp_f, "celsius": round((temp_f - 32) * 5 / 9, 1)}


async def get_forecast(city: str, days: int = 3) -> dict[str, object]:
    """Simulate a multi-day forecast."""
    import random
    conditions = ["sunny", "cloudy", "rainy", "partly cloudy"]
    forecast = [
        {"day": i + 1, "condition": random.choice(conditions), "high_f": random.randint(55, 85)}
        for i in range(days)
    ]
    return {"city": city, "days": days, "forecast": forecast}


def weather() -> Skill:
    """Create the weather skill."""
    return define_skill(
        name="weather",
        description="Weather operations — current conditions, forecasts, temperature conversion",
        operations={
            "get": OperationDef(
                description="Get current weather for a city",
                handler=get_weather,
                signature="(city: str) -> dict",
                tags=["weather", "temperature", "current", "conditions"],
                default_permission="allow",
            ),
            "convert": OperationDef(
                description="Convert Fahrenheit to Celsius",
                handler=convert_temp,
                signature="(temp_f: float) -> dict[str, float]",
                tags=["weather", "convert", "temperature", "celsius", "fahrenheit"],
                default_permission="allow",
            ),
            "forecast": OperationDef(
                description="Get a multi-day weather forecast for a city",
                handler=get_forecast,
                signature="(city: str, days: int = 3) -> dict",
                tags=["weather", "forecast", "prediction", "future"],
                default_permission="allow",
            ),
        },
    )
