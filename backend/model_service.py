"""Inference helpers for the real historical NER weather baseline."""

from __future__ import annotations

import json
from datetime import datetime
from math import atan2, cos, radians, sin, sqrt
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parent
MODEL = json.loads((ROOT / "historical_risk_model.json").read_text(encoding="utf-8"))


def distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6371
    dlat, dlng = radians(lat2 - lat1), radians(lng2 - lng1)
    value = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return radius * 2 * atan2(sqrt(value), sqrt(1 - value))


async def geocode(client: httpx.AsyncClient, name: str) -> dict:
    response = await client.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": name, "count": 1, "language": "en", "format": "json"},
    )
    response.raise_for_status()
    results = response.json().get("results", [])
    if not results:
        raise ValueError(f"Location not found: {name}")
    result = results[0]
    return {
        "name": result["name"],
        "admin": result.get("admin1", ""),
        "lat": result["latitude"],
        "lng": result["longitude"],
    }


async def road_route(client: httpx.AsyncClient, start: dict, end: dict) -> dict:
    points = f'{start["lng"]},{start["lat"]};{end["lng"]},{end["lat"]}'
    response = await client.get(
        f"https://router.project-osrm.org/route/v1/driving/{points}",
        params={"alternatives": "false", "steps": "false", "geometries": "geojson", "overview": "full"},
    )
    response.raise_for_status()
    body = response.json()
    if body.get("code") != "Ok" or not body.get("routes"):
        raise ValueError("No drivable route found")
    return body["routes"][0]


def nearest_locations(coordinates: list[list[float]], limit: int = 3) -> list[tuple[str, dict, float]]:
    sampled = coordinates[:: max(1, len(coordinates) // 60)]
    ranked = []
    for location_id, location in MODEL["locations"].items():
        distance = min(
            distance_km(location["lat"], location["lng"], lat, lng)
            for lng, lat in sampled
        )
        ranked.append((location_id, location, distance))
    return sorted(ranked, key=lambda item: item[2])[:limit]


def calibrated_score(coordinates: list[list[float]], month: int) -> tuple[float, list[dict], list[dict]]:
    """Compare a route's monthly baselines with the regional extreme range."""
    stations = nearest_locations(coordinates)
    month_key = f"{month:02d}"
    regional = MODEL["global_monthly"][month_key]
    scales = {
        "rain_7d_mm": max(regional["rain_7d_mm"]["p97"], 1),
        "rain_30d_mm": max(regional["rain_30d_mm"]["p97"], 1),
        "relative_humidity_pct": max(regional["relative_humidity_pct"]["p97"], 1),
        "wind_speed_2m_mps": max(regional["wind_speed_2m_mps"]["p97"], 1),
    }
    weights = {
        "rain_7d_mm": 0.40,
        "rain_30d_mm": 0.32,
        "relative_humidity_pct": 0.18,
        "wind_speed_2m_mps": 0.10,
    }
    station_scores = []
    station_rows = []
    baselines = []
    for location_id, location, route_distance in stations:
        baseline = MODEL["baselines"].get(f"{location_id}|{month_key}", regional)
        baselines.append(baseline)
        score = sum(
            min(100, baseline[feature]["p90"] / scales[feature] * 100) * weight
            for feature, weight in weights.items()
        )
        station_scores.append(score)
        station_rows.append({
            "location_id": location_id,
            "name": location["name"],
            "state": location["state"],
            "distance_from_route_km": round(route_distance, 1),
            "samples": baseline["samples"],
        })

    average = lambda feature: sum(item[feature]["p90"] for item in baselines) / len(baselines)
    factors = [
        {"name": "Historical 7-day rainfall", "value": round(average("rain_7d_mm"), 1), "unit": "mm · 90th percentile"},
        {"name": "Historical 30-day rainfall", "value": round(average("rain_30d_mm"), 1), "unit": "mm · 90th percentile"},
        {"name": "Historical humidity", "value": round(average("relative_humidity_pct"), 1), "unit": "% · 90th percentile"},
    ]
    return round(sum(station_scores) / len(station_scores), 1), factors, station_rows


async def predict_route_weather_risk(origin: str, destination: str, departure: datetime) -> dict:
    async with httpx.AsyncClient(timeout=15, headers={"User-Agent": "NERve-Hackathon-Prototype/2.0"}) as client:
        start, end = await geocode(client, origin), await geocode(client, destination)
        route = await road_route(client, start, end)

    risk, factors, stations = calibrated_score(route["geometry"]["coordinates"], departure.month)
    if departure.hour in (5, 6, 7, 17, 18, 19):
        risk = min(100, risk + 4)
        factors.append({"name": "Peak movement window", "value": 4, "unit": "risk points"})
    risk = round(risk, 1)
    level = "HIGH" if risk >= 65 else "ELEVATED" if risk >= 42 else "LOW"
    return {
        "data_source": "REAL_HISTORICAL_FEATURES_CALIBRATED_MODEL",
        "model_type": MODEL["model_type"],
        "training_rows": MODEL["training_rows"],
        "training_window": MODEL["training_window"],
        "target_available": False,
        "origin": start,
        "destination": end,
        "departure_time": departure.isoformat(),
        "route": {
            "distance_km": round(route["distance"] / 1000, 1),
            "duration_minutes": round(route["duration"] / 60),
            "geometry": route["geometry"],
        },
        "weather_hazard_score": risk,
        "accessibility_score": round(100 - risk * 0.72, 1),
        "level": level,
        "confidence": 74,
        "factors": factors,
        "reference_locations": stations,
        "recommendation": "Consider another departure window and verify local advisories" if level == "HIGH" else "Proceed with monitoring and verify road reports" if level == "ELEVATED" else "Conditions are comparatively favourable; continue normal checks",
        "disclaimer": "Historically calibrated weather-hazard signal—not the probability that an incident will occur.",
    }


def public_model_info() -> dict:
    keys = ("model_type", "training_rows", "training_window", "feature_names", "target_available", "output_meaning", "source")
    return {key: MODEL[key] for key in keys}
