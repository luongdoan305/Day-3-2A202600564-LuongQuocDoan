"""Real hotel search tool backed by RapidAPI Booking.com or Amadeus."""
from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv

REQUEST_TIMEOUT = 15
AMADEUS_BASE_URL = "https://test.api.amadeus.com"
load_dotenv()


class HotelToolError(RuntimeError):
    """Raised when the hotel provider cannot return a usable result."""


def _positive_nights(nights: int) -> int:
    if isinstance(nights, bool) or not isinstance(nights, int) or nights < 1:
        raise HotelToolError("nights must be a positive integer")
    return nights


def _rating(value: Any, ten_point_scale: bool = False) -> Any:
    if value is None:
        return None
    try:
        rating = float(value)
    except (TypeError, ValueError):
        return None
    return round(rating / 2 if ten_point_scale else rating, 1)


def _request_json(method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
    try:
        response = requests.request(method, url, timeout=REQUEST_TIMEOUT, **kwargs)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise HotelToolError(f"Hotel API request failed: {exc}") from exc
    except ValueError as exc:
        raise HotelToolError("Hotel API request failed: invalid JSON response") from exc
    if not isinstance(payload, dict):
        raise HotelToolError("Hotel API request failed: unexpected response format")
    return payload


def _rapidapi_headers() -> Dict[str, str]:
    key = os.getenv("RAPIDAPI_KEY")
    host = os.getenv("RAPIDAPI_HOST")
    if not key or not host:
        raise HotelToolError("Missing RAPIDAPI_KEY or RAPIDAPI_HOST")
    return {"X-RapidAPI-Key": key, "X-RapidAPI-Host": host}


def _search_rapidapi(city: str, nights: int) -> List[Dict[str, Any]]:
    headers = _rapidapi_headers()
    host = os.environ["RAPIDAPI_HOST"]
    base_url = f"https://{host}"
    destinations = _request_json(
        "GET",
        f"{base_url}/api/v1/hotels/searchDestination",
        headers=headers,
        params={"query": city},
    ).get("data") or []
    if not destinations:
        raise HotelToolError(f"City not found: {city}")

    destination_id = destinations[0].get("dest_id")
    search_type = destinations[0].get("search_type")
    if destination_id is None or not search_type:
        raise HotelToolError(f"City not found: {city}")

    checkin = date.today() + timedelta(days=1)
    checkout = checkin + timedelta(days=nights)
    data = _request_json(
        "GET",
        f"{base_url}/api/v1/hotels/searchHotels",
        headers=headers,
        params={
            "dest_id": destination_id,
            "search_type": search_type,
            "arrival_date": checkin.isoformat(),
            "departure_date": checkout.isoformat(),
            "adults": 1,
            "room_qty": 1,
            "page_number": 1,
            "languagecode": "vi",
            "currency_code": "VND",
        },
    ).get("data") or {}

    result: List[Dict[str, Any]] = []
    for item in (data.get("hotels") or [])[:10]:
        prop = item.get("property") or {}
        total = ((prop.get("priceBreakdown") or {}).get("grossPrice") or {}).get("value")
        if total is None:
            continue
        total_price = round(float(total))
        result.append(
            {
                "name": prop.get("name") or "Unknown hotel",
                "price_per_night": round(total_price / nights),
                "rating": _rating(prop.get("reviewScore"), ten_point_scale=True),
                "address": prop.get("wishlistName") or prop.get("address") or city,
                "nights": nights,
                "total_price": total_price,
            }
        )
    return result


def _amadeus_access_token() -> str:
    client_id = os.getenv("AMADEUS_CLIENT_ID")
    client_secret = os.getenv("AMADEUS_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise HotelToolError("Missing AMADEUS_CLIENT_ID or AMADEUS_CLIENT_SECRET")
    payload = _request_json(
        "POST",
        f"{AMADEUS_BASE_URL}/v1/security/oauth2/token",
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )
    token = payload.get("access_token")
    if not token:
        raise HotelToolError("Hotel API request failed: Amadeus access token missing")
    return str(token)


def _search_amadeus(city: str, nights: int) -> List[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {_amadeus_access_token()}"}
    locations = _request_json(
        "GET",
        f"{AMADEUS_BASE_URL}/v1/reference-data/locations/cities",
        headers=headers,
        params={"keyword": city, "max": 1},
    ).get("data") or []
    if not locations or not locations[0].get("iataCode"):
        raise HotelToolError(f"City not found: {city}")

    city_code = locations[0]["iataCode"]
    hotels = _request_json(
        "GET",
        f"{AMADEUS_BASE_URL}/v1/reference-data/locations/hotels/by-city",
        headers=headers,
        params={"cityCode": city_code},
    ).get("data") or []
    if not hotels:
        raise HotelToolError(f"Empty hotel result for city: {city}")

    checkin = date.today() + timedelta(days=1)
    checkout = checkin + timedelta(days=nights)
    hotel_by_id = {hotel["hotelId"]: hotel for hotel in hotels[:20] if hotel.get("hotelId")}
    if not hotel_by_id:
        raise HotelToolError(f"Empty hotel result for city: {city}")
    offers = _request_json(
        "GET",
        f"{AMADEUS_BASE_URL}/v3/shopping/hotel-offers",
        headers=headers,
        params={
            "hotelIds": ",".join(hotel_by_id),
            "adults": 1,
            "checkInDate": checkin.isoformat(),
            "checkOutDate": checkout.isoformat(),
            "roomQuantity": 1,
            "currency": "VND",
            "bestRateOnly": "true",
        },
    ).get("data") or []

    result: List[Dict[str, Any]] = []
    for item in offers[:10]:
        hotel = item.get("hotel") or {}
        offer_list = item.get("offers") or []
        if not offer_list:
            continue
        total = (offer_list[0].get("price") or {}).get("total")
        if total is None:
            continue
        total_price = round(float(total))
        details = hotel_by_id.get(hotel.get("hotelId"), {})
        address = details.get("address") or {}
        result.append(
            {
                "name": hotel.get("name") or details.get("name") or "Unknown hotel",
                "price_per_night": round(total_price / nights),
                "rating": _rating(hotel.get("rating")),
                "address": ", ".join(address.get("lines") or []) or city,
                "nights": nights,
                "total_price": total_price,
            }
        )
    return result


def search_hotels(city: str, nights: int = 1) -> List[Dict[str, Any]]:
    """Search real hotel offers and normalize prices for the requested stay."""
    city = city.strip()
    if not city:
        raise HotelToolError("City is required")
    nights = _positive_nights(nights)

    if os.getenv("RAPIDAPI_KEY") or os.getenv("RAPIDAPI_HOST"):
        hotels = _search_rapidapi(city, nights)
    elif os.getenv("AMADEUS_CLIENT_ID") or os.getenv("AMADEUS_CLIENT_SECRET"):
        hotels = _search_amadeus(city, nights)
    else:
        raise HotelToolError(
            "Hotel API key missing: configure RAPIDAPI_KEY and RAPIDAPI_HOST, "
            "or AMADEUS_CLIENT_ID and AMADEUS_CLIENT_SECRET"
        )

    if not hotels:
        raise HotelToolError(f"Empty hotel result for city: {city}")
    return hotels
