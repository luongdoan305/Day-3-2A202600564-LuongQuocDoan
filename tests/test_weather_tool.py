"""Weather tool tests with mocked external API responses."""
import os
import sys
from unittest.mock import Mock, patch

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.tool_specs import get_tools_v1
from src.tools.weather_tool import get_weather


def _response(payload, status_code=200):
    response = Mock()
    response.status_code = status_code
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    return response


def test_missing_weather_api_key(monkeypatch):
    monkeypatch.delenv("WEATHER_API_KEY", raising=False)
    monkeypatch.setenv("WEATHER_API_BASE_URL", "https://weather.example/current")
    assert get_weather("Da Nang") == {"error": "Missing WEATHER_API_KEY"}


def test_openweather_response_is_normalized(monkeypatch):
    monkeypatch.setenv("WEATHER_API_KEY", "secret")
    monkeypatch.setenv("WEATHER_API_BASE_URL", "https://weather.example/current")
    payload = {
        "weather": [{"description": "scattered clouds"}],
        "main": {"temp": 31.2, "humidity": 72},
        "wind": {"speed": 3.5},
    }

    with patch("src.tools.weather_tool.requests.get", return_value=_response(payload)) as request:
        result = get_weather("Da Nang")

    assert result == {
        "city": "Da Nang",
        "condition": "scattered clouds",
        "temperature": 31.2,
        "humidity": 72,
        "wind_speed": 3.5,
        "raw": payload,
    }
    request.assert_called_once_with(
        "https://weather.example/current",
        params={"q": "Da Nang", "appid": "secret", "units": "metric"},
        timeout=10,
    )


def test_weather_timeout(monkeypatch):
    monkeypatch.setenv("WEATHER_API_KEY", "secret")
    monkeypatch.setenv("WEATHER_API_BASE_URL", "https://weather.example/current")
    with patch("src.tools.weather_tool.requests.get", side_effect=requests.Timeout):
        assert get_weather("Da Nang") == {"error": "Weather API request timed out"}


def test_provider_invalid_city_payload(monkeypatch):
    monkeypatch.setenv("WEATHER_API_KEY", "secret")
    monkeypatch.setenv("WEATHER_API_BASE_URL", "https://weather.example/current")
    response = _response({"error": {"message": "No matching location found."}})
    with patch("src.tools.weather_tool.requests.get", return_value=response):
        result = get_weather("Unknown City")
    assert result == {
        "error": "Weather API rejected city 'Unknown City': No matching location found."
    }


def test_get_weather_registry_uses_real_tool():
    weather = next(tool for tool in get_tools_v1() if tool["name"] == "get_weather")
    assert weather["func"] is get_weather
