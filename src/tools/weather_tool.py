"""Real current weather tool with normalized output."""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv

from src.telemetry.logger import logger

load_dotenv()

REQUEST_TIMEOUT = 10


def _error(message: str, city: str) -> Dict[str, str]:
    logger.log_event("TOOL_ERROR", {"tool": "get_weather", "city": city, "error": message})
    return {"error": message}


def _number(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _condition(value: Any) -> Optional[str]:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, dict):
        return _condition(value.get("description") or value.get("text") or value.get("main"))
    if isinstance(value, list) and value:
        return _condition(value[0])
    return None


def _normalized_weather(city: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Normalize common current-weather API response shapes."""
    current = payload.get("current")
    main = payload.get("main")
    if isinstance(main, dict):
        temperature = _number(main.get("temp"))
        humidity = _number(main.get("humidity"))
        wind = payload.get("wind") if isinstance(payload.get("wind"), dict) else {}
        wind_speed = _number(wind.get("speed"))
        condition = _condition(payload.get("weather"))
    elif isinstance(current, dict):
        temperature = _number(current.get("temp_c", current.get("temperature")))
        humidity = _number(current.get("humidity"))
        wind_speed = _number(
            current.get("wind_kph", current.get("wind_speed", current.get("windspeed")))
        )
        condition = _condition(
            current.get("condition", current.get("weather_description", current.get("weather_code")))
        )
    else:
        temperature = _number(payload.get("temperature", payload.get("temp")))
        humidity = _number(payload.get("humidity"))
        wind_speed = _number(payload.get("wind_speed", payload.get("windspeed")))
        condition = _condition(payload.get("condition", payload.get("weather")))

    if temperature is None or humidity is None or wind_speed is None or condition is None:
        return None
    return {
        "city": city,
        "condition": condition,
        "temperature": temperature,
        "humidity": humidity,
        "wind_speed": wind_speed,
        "raw": payload,
    }


def get_weather(city: str) -> Dict[str, Any]:
    """Fetch current weather for a city and return a normalized dictionary."""
    city = city.strip()
    logger.log_event("TOOL_CALL", {"tool": "get_weather", "city": city})
    if not city:
        return _error("Invalid city: city is required", city)

    api_key = os.getenv("WEATHER_API_KEY")
    base_url = os.getenv("WEATHER_API_BASE_URL")
    if not api_key:
        return _error("Missing WEATHER_API_KEY", city)
    if not base_url:
        return _error("Missing WEATHER_API_BASE_URL", city)

    params = {"q": city, "appid": api_key, "units": "metric"}
    try:
        response = requests.get(base_url, params=params, timeout=REQUEST_TIMEOUT)
    except requests.Timeout:
        return _error("Weather API request timed out", city)
    except requests.RequestException as exc:
        return _error(f"Weather API network failure: {exc}", city)

    if response.status_code in (400, 404):
        return _error(f"Invalid city: {city}", city)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        return _error(f"Weather API HTTP error: {exc}", city)

    try:
        payload = response.json()
    except ValueError:
        return _error("Weather API returned invalid JSON", city)
    if not payload:
        return _error("Weather API returned an empty response", city)
    if not isinstance(payload, dict):
        return _error("Weather API returned an unexpected response format", city)
    provider_error = payload.get("error")
    if provider_error:
        if isinstance(provider_error, dict):
            detail = provider_error.get("message") or provider_error.get("code") or provider_error
        else:
            detail = provider_error
        return _error(f"Weather API rejected city '{city}': {detail}", city)

    result = _normalized_weather(city, payload)
    if result is None:
        return _error("Weather API returned an unexpected response format", city)
    logger.log_event(
        "TOOL_RESULT",
        {
            "tool": "get_weather",
            "city": city,
            "temperature": result["temperature"],
            "condition": result["condition"],
        },
    )
    return result
