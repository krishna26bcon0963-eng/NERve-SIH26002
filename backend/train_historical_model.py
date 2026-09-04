"""Fit NERve's historical weather-hazard baseline.

This model deliberately does not learn an incident probability because the
source package has no verified disruption labels yet.  It learns normal and
extreme weather ranges for each logistics location and calendar month.  The
API can then explain how unusual a proposed journey's conditions are.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / "model_features_daily.csv"
LOCATIONS_FILE = ROOT / "data" / "locations.csv"
OUTPUT_FILE = ROOT / "historical_risk_model.json"

FEATURES = (
    "rain_mm",
    "rain_3d_mm",
    "rain_7d_mm",
    "rain_30d_mm",
    "relative_humidity_pct",
    "wind_speed_2m_mps",
    "temperature_anomaly_30d_c",
)


def percentile(values: list[float], fraction: float) -> float:
    """Return a linearly interpolated percentile without extra dependencies."""
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return round(ordered[lower] * (1 - weight) + ordered[upper] * weight, 3)


def summarise(bucket: dict[str, list[float]]) -> dict:
    summary = {"samples": max((len(values) for values in bucket.values()), default=0)}
    for feature, values in bucket.items():
        clean = [abs(value) if feature == "temperature_anomaly_30d_c" else value for value in values]
        summary[feature] = {
            "p50": percentile(clean, 0.50),
            "p75": percentile(clean, 0.75),
            "p90": percentile(clean, 0.90),
            "p97": percentile(clean, 0.97),
        }
    return summary


def train() -> dict:
    grouped: dict[tuple[str, int], dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    global_month: dict[int, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    rows = 0
    first_date = None
    last_date = None

    with DATA_FILE.open("r", encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            date = row["date"]
            month = int(date[5:7])
            first_date = date if first_date is None else min(first_date, date)
            last_date = date if last_date is None else max(last_date, date)
            rows += 1
            for feature in FEATURES:
                if row.get(feature) not in (None, ""):
                    value = float(row[feature])
                    grouped[(row["location_id"], month)][feature].append(value)
                    global_month[month][feature].append(value)

    with LOCATIONS_FILE.open("r", encoding="utf-8-sig", newline="") as source:
        locations = {
            row["location_id"]: {
                "state": row["state"],
                "name": row["location_name"],
                "lat": float(row["latitude"]),
                "lng": float(row["longitude"]),
            }
            for row in csv.DictReader(source)
        }

    return {
        "model_type": "EMPIRICAL_MONTHLY_WEATHER_HAZARD_BASELINE",
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "training_rows": rows,
        "training_window": [first_date, last_date],
        "feature_names": list(FEATURES),
        "target_available": False,
        "output_meaning": "Weather-hazard anomaly score, not incident probability",
        "source": "NASA POWER daily point/grid analysis from the supplied NERve foundation",
        "locations": locations,
        "baselines": {
            f"{location_id}|{month:02d}": summarise(bucket)
            for (location_id, month), bucket in grouped.items()
        },
        "global_monthly": {
            f"{month:02d}": summarise(bucket) for month, bucket in global_month.items()
        },
    }


if __name__ == "__main__":
    model = train()
    OUTPUT_FILE.write_text(json.dumps(model, indent=2), encoding="utf-8")
    print(f"Fitted {model['model_type']} on {model['training_rows']:,} rows")
    print(f"Saved {OUTPUT_FILE}")
