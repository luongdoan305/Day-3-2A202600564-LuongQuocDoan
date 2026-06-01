"""Offline tests — no API key required."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.travel_tools import (
    estimate_trip_cost,
    get_weather,
    search_attractions,
    check_budget_fit,
)
from src.tools.tool_specs import get_tools_v1, get_tools_v2


def test_weather():
    assert "Đà Nẵng" in get_weather("Đà Nẵng")


def test_attractions():
    data = json.loads(search_attractions("Đà Nẵng", "biển"))
    assert "Mỹ Khê" in " ".join(data["places"])


def test_cost():
    data = json.loads(estimate_trip_cost("Đà Nẵng", 3, 2))
    assert data["total"] > 0


def test_budget_fit():
    ok = json.loads(check_budget_fit(4_000_000, 5_000_000))
    assert ok["fits_budget"] is True


def test_tool_registry():
    assert len(get_tools_v1()) >= 4
    assert len(get_tools_v2()) > len(get_tools_v1())
