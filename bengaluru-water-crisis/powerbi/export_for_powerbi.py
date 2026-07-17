"""
Exports a clean star-schema (fact + dimension tables) for Power BI Desktop.

Run: python export_for_powerbi.py
Outputs into ./output/:
  - dim_ward.csv        (one row per ward: name, zone, lat, lon)
  - dim_date.csv         (one row per month, with year/month/quarter for time intelligence)
  - fact_readings.csv    (one row per ward-month: all metrics + risk score)
  - fact_predictions.csv (latest next-month prediction per ward, from the trained model)

Import into Power BI:
  1. Get Data > Text/CSV, load all four files.
  2. Model view: relate fact_readings[ward_id] -> dim_ward[ward_id],
     and fact_readings[date] -> dim_date[date].
  3. Suggested visuals:
     - Map (Azure/ArcGIS or Bing) with dim_ward lat/lon, bubble size = risk_score
     - Line chart: risk_score trend by ward_name over dim_date, sliced by zone
     - KPI cards: AVG(risk_score), MAX(risk_score), COUNT of Critical wards
     - Matrix: zone x month, conditional-formatted risk_score
     - Scatter: tanker_price_inr vs groundwater_depth_m, sized by population_density
"""
import os
import sys
import pandas as pd

BASE = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE, "..", "data", "output")
OUT_DIR = os.path.join(BASE, "output")
os.makedirs(OUT_DIR, exist_ok=True)

wards = pd.read_csv(os.path.join(DATA_DIR, "wards.csv"))
readings = pd.read_csv(os.path.join(DATA_DIR, "historical_readings.csv"))

# --- dim_ward ---
wards.to_csv(os.path.join(OUT_DIR, "dim_ward.csv"), index=False)

# --- dim_date ---
dim_date = readings[["date", "year", "month"]].drop_duplicates().sort_values("date")
dim_date["quarter"] = ((dim_date["month"] - 1) // 3) + 1
dim_date["month_name"] = pd.to_datetime(dim_date["date"]).dt.strftime("%b")
dim_date.to_csv(os.path.join(OUT_DIR, "dim_date.csv"), index=False)

# --- fact_readings ---
fact = readings[[
    "ward_id", "date", "rainfall_mm", "avg_temp_c", "groundwater_depth_m",
    "tanker_price_inr", "population_density", "complaint_count",
    "risk_score", "risk_label",
]]
fact.to_csv(os.path.join(OUT_DIR, "fact_readings.csv"), index=False)

# --- fact_predictions (uses the trained model if available) ---
try:
    sys.path.insert(0, os.path.join(BASE, "..", "backend"))
    from xgboost import XGBRegressor

    model_path = os.path.join(BASE, "..", "model", "output", "risk_model.json")
    model = XGBRegressor()
    model.load_model(model_path)

    df = readings.sort_values(["ward_id", "year", "month"]).copy()
    df["groundwater_trend"] = df.groupby("ward_id")["groundwater_depth_m"].diff().fillna(0)
    df["rainfall_3mo_avg"] = df.groupby("ward_id")["rainfall_mm"].transform(lambda s: s.rolling(3, min_periods=1).mean())

    latest = df.sort_values("date").groupby("ward_id").tail(1).copy()
    latest["next_month"] = (latest["month"] % 12) + 1
    features = ["rainfall_mm", "avg_temp_c", "groundwater_depth_m", "tanker_price_inr",
                "population_density", "complaint_count", "groundwater_trend", "rainfall_3mo_avg"]
    X = latest[features].copy()
    X["month"] = latest["next_month"]

    latest["predicted_next_month_risk"] = model.predict(X).clip(0, 100).round(1)
    out = latest[["ward_id", "ward_name", "predicted_next_month_risk"]]
    out.to_csv(os.path.join(OUT_DIR, "fact_predictions.csv"), index=False)
    print("Wrote fact_predictions.csv")
except Exception as e:
    print(f"Skipped predictions export (train the model first): {e}")

print(f"Power BI-ready CSVs written to {OUT_DIR}")
