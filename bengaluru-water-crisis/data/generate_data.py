"""
Generates a synthetic-but-realistic dataset for the Bengaluru Water Crisis Predictor.

IMPORTANT: This is SYNTHETIC data built to mimic realistic patterns seen in
Bengaluru's 2023-2024 water crisis (falling groundwater tables in the eastern/
southern IT corridor wards, tanker price spikes in summer, rainfall deficits).
It is NOT scraped from BWSSB/BBMP. For a production version, replace the
generation logic in this file with real API calls to:
  - OpenWeatherMap (historical rainfall/temperature)
  - India-WRIS (groundwater levels)
  - BBMP/BWSSB open data portals (tanker pricing, complaints) if published

Run: python generate_data.py
Outputs: wards.csv, historical_readings.csv into ./output/
"""

import csv
import os
import random
import math
from datetime import date

random.seed(42)

OUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUT_DIR, exist_ok=True)

# 40 representative Bengaluru wards with approximate real coordinates.
# Grouped loosely by zone to give the model a realistic geographic risk pattern.
WARDS = [
    # (name, lat, lon, zone, base_risk 0-1 -- higher = drier/more stressed area)
    ("Whitefield", 12.9698, 77.7500, "East", 0.72),
    ("Mahadevapura", 12.9902, 77.6960, "East", 0.68),
    ("Marathahalli", 12.9591, 77.6974, "East", 0.70),
    ("KR Puram", 13.0088, 77.6959, "East", 0.65),
    ("Bellandur", 12.9260, 77.6784, "East", 0.75),
    ("HSR Layout", 12.9121, 77.6446, "South-East", 0.66),
    ("Koramangala", 12.9352, 77.6245, "South-East", 0.55),
    ("BTM Layout", 12.9166, 77.6101, "South", 0.60),
    ("JP Nagar", 12.9077, 77.5906, "South", 0.52),
    ("Jayanagar", 12.9308, 77.5838, "South", 0.45),
    ("Banashankari", 12.9255, 77.5468, "South", 0.48),
    ("Basavanagudi", 12.9422, 77.5738, "South", 0.42),
    ("Electronic City", 12.8452, 77.6602, "South-East", 0.78),
    ("Bommanahalli", 12.9010, 77.6135, "South-East", 0.63),
    ("Hebbal", 13.0358, 77.5970, "North", 0.50),
    ("Yelahanka", 13.1007, 77.5963, "North", 0.58),
    ("RT Nagar", 13.0230, 77.5950, "North", 0.47),
    ("Malleshwaram", 13.0035, 77.5709, "Central", 0.35),
    ("Rajajinagar", 12.9990, 77.5550, "Central", 0.38),
    ("Vijayanagar", 12.9719, 77.5340, "West", 0.44),
    ("Basaveshwaranagar", 12.9886, 77.5350, "West", 0.41),
    ("RR Nagar", 12.9260, 77.5180, "West", 0.57),
    ("Kengeri", 12.9081, 77.4855, "West", 0.62),
    ("Nagarbhavi", 12.9596, 77.5060, "West", 0.53),
    ("Peenya", 13.0280, 77.5200, "North-West", 0.56),
    ("Yeshwanthpur", 13.0230, 77.5540, "North-West", 0.46),
    ("CV Raman Nagar", 12.9880, 77.6640, "East", 0.61),
    ("Indiranagar", 12.9719, 77.6412, "Central-East", 0.40),
    ("Ulsoor", 12.9815, 77.6220, "Central", 0.37),
    ("Shivajinagar", 12.9857, 77.6057, "Central", 0.36),
    ("Domlur", 12.9610, 77.6387, "Central-East", 0.44),
    ("Sarjapur Road", 12.9010, 77.6870, "South-East", 0.80),
    ("Varthur", 12.9412, 77.7409, "East", 0.77),
    ("Hennur", 13.0450, 77.6350, "North-East", 0.54),
    ("Banaswadi", 13.0140, 77.6510, "North-East", 0.51),
    ("Vidyaranyapura", 13.0680, 77.5560, "North", 0.49),
    ("Jalahalli", 13.0450, 77.5470, "North-West", 0.45),
    ("Chikkabanavara", 13.0680, 77.5030, "North-West", 0.55),
    ("Uttarahalli", 12.8990, 77.5510, "South", 0.59),
    ("Begur", 12.8720, 77.6300, "South", 0.67),
]

MONTHS = 24  # 2 years of monthly history

# Bengaluru monthly rainfall climatology (mm), roughly realistic (drier Jan-Mar, wet Jun-Oct)
MONTHLY_RAINFALL_NORMAL = [4, 8, 15, 45, 110, 95, 100, 130, 190, 160, 55, 12]


def month_index_to_calendar(i, start_year=2024, start_month=7):
    total = (start_month - 1) + i
    year = start_year + total // 12
    month = total % 12 + 1
    return year, month


def generate_historical():
    rows = []
    for ward_name, lat, lon, zone, base_risk in WARDS:
        groundwater_depth = 8 + base_risk * 12 + random.uniform(-1, 1)  # meters below ground, deeper = worse
        for i in range(MONTHS):
            year, month = month_index_to_calendar(i)
            normal_rain = MONTHLY_RAINFALL_NORMAL[month - 1]
            # Simulate a drought year effect + random noise
            drought_factor = 1.0 - (base_risk * 0.35) + random.uniform(-0.15, 0.15)
            rainfall_mm = max(0, normal_rain * drought_factor)

            avg_temp_c = 24 + 6 * math.sin((month - 3) / 12 * 2 * math.pi) + random.uniform(-1, 1) + base_risk * 1.5

            # Groundwater depletes further in dry months, recovers slightly after monsoon
            seasonal_draw = 0.15 if month in [3, 4, 5] else (-0.25 if month in [8, 9, 10] else 0.02)
            groundwater_depth += seasonal_draw + base_risk * 0.05 + random.uniform(-0.05, 0.05)
            groundwater_depth = max(3, groundwater_depth)

            # Tanker price responds to groundwater depth + summer demand spike
            summer_multiplier = 1.6 if month in [3, 4, 5] else 1.0
            tanker_price = (600 + groundwater_depth * 25) * summer_multiplier + random.uniform(-50, 50)
            tanker_price = round(max(500, tanker_price), 0)

            population_density = round(8000 + base_risk * 12000 + random.uniform(-1000, 1000))

            complaint_count = round(max(0, (base_risk * 40) + (1 if month in [3, 4, 5] else 0) * 15 + random.uniform(-5, 8)))

            # Composite risk score (0-100), our ML target.
            # Calibrated so the full spread (Low -> Critical) actually shows up
            # across wards and seasons, not just the Medium/High middle band.
            rain_deficit_score = max(0, (normal_rain - rainfall_mm) / max(normal_rain, 1)) * 100
            risk_score = (
                0.35 * ((groundwater_depth - 3) / 19 * 100)   # groundwater ranges ~3-22m
                + 0.25 * rain_deficit_score
                + 0.20 * ((tanker_price - 500) / 1000 * 100)  # tanker ranges ~500-1500
                + 0.20 * (complaint_count / 45 * 100)
            )
            # Stretch around the midpoint so the full Low -> Critical range shows up
            # clearly (safe wards drop below 30, stressed summer wards exceed 75),
            # instead of everything bunching into Medium/High.
            risk_score = 50 + (risk_score - 50) * 1.55
            risk_score = round(min(100, max(0, risk_score + random.uniform(-8, 8))), 1)

            if risk_score < 30:
                risk_label = "Low"
            elif risk_score < 55:
                risk_label = "Medium"
            elif risk_score < 75:
                risk_label = "High"
            else:
                risk_label = "Critical"

            rows.append({
                "ward_name": ward_name,
                "year": year,
                "month": month,
                "date": f"{year}-{month:02d}-01",
                "rainfall_mm": round(rainfall_mm, 1),
                "avg_temp_c": round(avg_temp_c, 1),
                "groundwater_depth_m": round(groundwater_depth, 2),
                "tanker_price_inr": tanker_price,
                "population_density": population_density,
                "complaint_count": complaint_count,
                "risk_score": risk_score,
                "risk_label": risk_label,
            })
    return rows


def write_wards_csv():
    path = os.path.join(OUT_DIR, "wards.csv")
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ward_id", "ward_name", "lat", "lon", "zone"])
        for idx, (name, lat, lon, zone, _) in enumerate(WARDS, start=1):
            writer.writerow([idx, name, lat, lon, zone])
    print(f"Wrote {path}")


def write_historical_csv(rows):
    path = os.path.join(OUT_DIR, "historical_readings.csv")
    ward_id_map = {name: idx for idx, (name, *_rest) in enumerate(WARDS, start=1)}
    with open(path, "w", newline="") as f:
        fieldnames = ["ward_id", "ward_name", "year", "month", "date", "rainfall_mm",
                      "avg_temp_c", "groundwater_depth_m", "tanker_price_inr",
                      "population_density", "complaint_count", "risk_score", "risk_label"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            row["ward_id"] = ward_id_map[row["ward_name"]]
            writer.writerow(row)
    print(f"Wrote {path} ({len(rows)} rows)")


if __name__ == "__main__":
    write_wards_csv()
    rows = generate_historical()
    write_historical_csv(rows)
    print("Done. Data is SYNTHETIC — see module docstring for real API integration notes.")
