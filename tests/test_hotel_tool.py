"""Hotel tool tests with mocked provider responses."""
import os
import sys
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.hotel_tool import HotelToolError, search_hotels
from src.tools.tool_specs import get_tools_v1


def _response(payload):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    return response


def test_missing_hotel_api_key(monkeypatch):
    for name in (
        "RAPIDAPI_KEY",
        "RAPIDAPI_HOST",
        "AMADEUS_CLIENT_ID",
        "AMADEUS_CLIENT_SECRET",
    ):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(HotelToolError, match="Hotel API key missing"):
        search_hotels("Da Nang", 2)


def test_rapidapi_hotels_are_normalized(monkeypatch):
    monkeypatch.setenv("RAPIDAPI_KEY", "secret")
    monkeypatch.setenv("RAPIDAPI_HOST", "booking-com15.p.rapidapi.com")
    responses = [
        _response({"data": [{"dest_id": "-3712125", "search_type": "CITY"}]}),
        _response(
            {
                "data": {
                    "hotels": [
                        {
                            "property": {
                                "name": "Sea View Hotel",
                                "reviewScore": 8.6,
                                "wishlistName": "Da Nang",
                                "priceBreakdown": {"grossPrice": {"value": 1400000}},
                            }
                        }
                    ]
                }
            }
        ),
    ]

    with patch("src.tools.hotel_tool.requests.request", side_effect=responses):
        hotels = search_hotels("Da Nang", 2)

    assert hotels == [
        {
            "name": "Sea View Hotel",
            "price_per_night": 700000,
            "rating": 4.3,
            "address": "Da Nang",
            "nights": 2,
            "total_price": 1400000,
        }
    ]


def test_search_hotels_registered():
    assert "search_hotels" in {tool["name"] for tool in get_tools_v1()}
