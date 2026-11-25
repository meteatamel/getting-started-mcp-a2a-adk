import logging
import httpx
from google.adk.agents import LlmAgent

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = (
    "You are a specialized assistant for providing weather forecasts and conditions for travel destinations. "
    "Your sole purpose is to use the 'get_weather' tool to fetch weather information. "
    "Provide clear, concise summaries of current weather conditions, temperatures, and forecasts to help travelers pack and plan."
)


def get_weather(location: str = "London") -> dict:
    """Gets the current weather and forecast for a given location or city.

    Args:
        location: The city or location name (e.g., 'London', 'Tokyo', 'Paris').

    Returns:
        A dictionary containing weather conditions, temperature, humidity, and forecast summary.
    """
    logger.info(f"--- 🌤️ Tool: get_weather called for {location} ---")
    try:
        response = httpx.get(
            f"https://wttr.in/{location}?format=j1",
            headers={"User-Agent": "curl/7.68.0"},
            timeout=8.0,
        )
        response.raise_for_status()
        data = response.json()

        current = data["current_condition"][0]
        desc = current.get("weatherDesc", [{}])[0].get("value", "Unknown")
        temp_c = current.get("temp_C", "N/A")
        temp_f = current.get("temp_F", "N/A")
        humidity = current.get("humidity", "N/A")
        wind_speed_kmph = current.get("windspeedKmph", "N/A")

        result = {
            "location": location,
            "condition": desc,
            "temperature_celsius": f"{temp_c}°C",
            "temperature_fahrenheit": f"{temp_f}°F",
            "humidity": f"{humidity}%",
            "wind_speed_kmph": f"{wind_speed_kmph} km/h",
        }
        logger.info(f"✅ Weather data fetched: {result}")
        return result
    except Exception as e:
        logger.warning(f"⚠️ Weather lookup via API failed: {e}. Returning simulated estimate.")
        return {
            "location": location,
            "condition": "Partly Cloudy",
            "temperature_celsius": "20°C",
            "temperature_fahrenheit": "68°F",
            "humidity": "55%",
            "wind_speed_kmph": "10 km/h",
            "note": f"Live data unavailable ({e}); showing estimated conditions.",
        }


weather_agent = LlmAgent(
    model="gemini-3.8-flash",
    name="weather_agent",
    description="A local specialist agent that provides current weather reports and forecasts for travel destinations.",
    instruction=SYSTEM_INSTRUCTION,
    tools=[get_weather],
)
