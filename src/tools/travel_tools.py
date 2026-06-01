"""
TripWise — mock travel tools for Lab 3 (no external API required).
Replace with real Weather / Places / Maps APIs in production.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List

# --- Mock data ---

WEATHER_DB: Dict[str, str] = {
    "đà nẵng": "Nắng đẹp, 28–32°C; buổi chiều có thể mưa rào ngắn.",
    "đà lạt": "Mát, 18–24°C; sương mù buổi sáng, mưa nhẹ buổi tối.",
    "hà nội": "Nóng ẩm, 30–35°C; chiều có mưa dông.",
    "phú quốc": "Nắng, biển êm; tối gió nhẹ.",
    "nha trang": "Nắng, phù hợp tắm biển; trưa nắng gắt.",
}

ATTRACTIONS_DB: Dict[str, Dict[str, List[str]]] = {
    "đà nẵng": {
        "biển": ["Bãi biển Mỹ Khê", "Cầu Rồng", "Ngũ Hành Sơn", "Chợ đêm Sơn Trà"],
        "gia đình": ["Bà Nà Hills", "Asia Park", "Bãi biển Mỹ Khê", "Cầu Rồng"],
        "ăn uống": ["Chợ Hàn", "Mỹ An seafood", "Cầu Rồng", "Hải sản Bé Mặn"],
        "chụp ảnh": ["Cầu Vàng Bà Nà", "Cầu Rồng", "Bãi biển Mỹ Khê", "Linh Ứng Sơn Trà"],
        "default": ["Bãi biển Mỹ Khê", "Bà Nà Hills", "Cầu Rồng", "Chợ đêm Sơn Trà"],
    },
    "đà lạt": {
        "default": ["Hồ Xuân Hương", "Langbiang", "Chợ đêm", "Dinh Bảo Đại"],
        "chụp ảnh": ["Đồi chè Cầu Đất", "Hồ Xuân Hương", "Ga Đà Lạt", "Thung lũng tình yêu"],
    },
}

COST_BASE_PER_DAY: Dict[str, int] = {
    "đà nẵng": 1_600_000,
    "đà lạt": 1_400_000,
    "hà nội": 1_800_000,
    "phú quốc": 2_000_000,
    "nha trang": 1_500_000,
}

RESTAURANTS_DB: Dict[str, List[str]] = {
    "đà nẵng": ["Hải sản Bé Mặn", "Bà Aê Restaurant", "Mì Quảng Bà Mua", "Nhà hàng Cơm Niêu"],
    "đà lạt": ["Quán Gỏi Đà Lạt", "Bánh căn Bà Tùng", "Lẩu gà lá é"],
}


def _norm_destination(destination: str) -> str:
    return destination.strip().lower()


def get_weather(destination: str, date: str = "today") -> str:
    """Kiểm tra thời tiết dự kiến tại điểm đến."""
    key = _norm_destination(destination)
    detail = WEATHER_DB.get(key, "Thời tiết ổn định, nên mang áo mưa nhẹ phòng mưa rào.")
    return f"Thời tiết tại {destination} ({date}): {detail}"


def search_attractions(destination: str, travel_style: str = "default") -> str:
    """Tìm địa điểm tham quan theo điểm đến và phong cách du lịch."""
    key = _norm_destination(destination)
    style_key = travel_style.strip().lower() or "default"
    by_dest = ATTRACTIONS_DB.get(key, {})
    places = by_dest.get(style_key) or by_dest.get("default") or [
        "Quảng trường trung tâm",
        "Chợ địa phương",
        "Bảo tàng địa phương",
    ]
    return json.dumps({"destination": destination, "style": travel_style, "places": places}, ensure_ascii=False)


def estimate_trip_cost(destination: str, days: int, people: int = 1) -> str:
    """Ước lượng chi phí khách sạn, ăn uống, di chuyển, vé tham quan."""
    key = _norm_destination(destination)
    base = COST_BASE_PER_DAY.get(key, 1_500_000)
    hotel = int(base * 0.35 * days * people)
    food = int(base * 0.30 * days * people)
    transport = int(base * 0.15 * days * people)
    tickets = int(base * 0.20 * days * people)
    total = hotel + food + transport + tickets
    payload = {
        "destination": destination,
        "days": days,
        "people": people,
        "hotel": hotel,
        "food": food,
        "transport": transport,
        "tickets": tickets,
        "total": total,
        "currency": "VND",
    }
    return json.dumps(payload, ensure_ascii=False)


def calculate_route_time(start: str, end: str) -> str:
    """Ước lượng thời gian di chuyển giữa hai địa điểm (mock)."""
    return f"Thời gian di chuyển từ '{start}' đến '{end}': khoảng 20–35 phút (ô tô/grab)."


def create_itinerary(destination: str, days: int, budget: int, style: str = "default") -> str:
    """Tạo khung lịch trình theo ngày (mock)."""
    lines = [f"# Lịch trình {days} ngày tại {destination}", f"Phong cách: {style} | Ngân sách mục tiêu: {budget:,} VND/người", ""]
    for d in range(1, days + 1):
        if d == 1:
            lines.append(f"## Ngày {d}: Check-in & khám phá gần trung tâm")
            lines.append("- Sáng: Di chuyển & nhận phòng")
            lines.append("- Chiều: Điểm tham quan nổi bật + chụp ảnh")
            lines.append("- Tối: Chợ đêm / ẩm thực địa phương")
        elif d == days:
            lines.append(f"## Ngày {d}: Trả phòng & mua quà")
            lines.append("- Sáng: Cafe view đẹp")
            lines.append("- Trưa: Check-out & về")
        else:
            lines.append(f"## Ngày {d}: Tham quan nổi bật")
            lines.append("- Sáng: Điểm ngoại ô / cáp treo")
            lines.append("- Chiều: Biển hoặc danh lam")
            lines.append("- Tối: Show / phố đi bộ")
        lines.append("")
    return "\n".join(lines)


def suggest_restaurants(destination: str, cuisine: str = "địa phương") -> str:
    """Gợi ý quán ăn theo điểm đến và sở thích ẩm thực."""
    key = _norm_destination(destination)
    places = RESTAURANTS_DB.get(key, ["Quán địa phương được đánh giá cao trên Maps"])
    return json.dumps({"destination": destination, "cuisine": cuisine, "restaurants": places}, ensure_ascii=False)


def check_budget_fit(estimated_total: int, budget: int) -> str:
    """So sánh chi phí ước tính với ngân sách người dùng."""
    diff = budget - estimated_total
    if diff >= 0:
        return json.dumps(
            {"fits_budget": True, "remaining": diff, "message": f"Trong ngân sách, còn dư ~{diff:,} VND."},
            ensure_ascii=False,
        )
    return json.dumps(
        {
            "fits_budget": False,
            "over_by": abs(diff),
            "message": f"Vượt ngân sách ~{abs(diff):,} VND — nên giảm ngày chơi hoặc đổi khách sạn.",
        },
        ensure_ascii=False,
    )


def weather_risk_warning(destination: str) -> str:
    """Cảnh báo rủi ro thời tiết cho outdoor activities."""
    key = _norm_destination(destination)
    if key in ("đà lạt", "đà nẵng"):
        return json.dumps(
            {
                "risk": "medium",
                "warning": "Có thể mưa chiều — ưu tiên outdoor buổi sáng, buổi tối chọn indoor.",
            },
            ensure_ascii=False,
        )
    return json.dumps({"risk": "low", "warning": "Thời tiết thuận lợi cho hoạt động ngoài trời."}, ensure_ascii=False)
