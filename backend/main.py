"""
FastAPI backend for the Bengaluru Water Crisis Predictor & Civic Dashboard.

Run:
    pip install -r requirements.txt
    python database.py         # loads CSV data into SQLite (one-time)
    uvicorn main:app --reload --port 8000

Docs: http://localhost:8000/docs
"""
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import pandas as pd
from xgboost import XGBRegressor

import database as db

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "model", "output", "risk_model.json")

app = FastAPI(title="Bengaluru Water Crisis API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

model = XGBRegressor()
model.load_model(MODEL_PATH)

FEATURES = [
    "rainfall_mm", "avg_temp_c", "groundwater_depth_m", "tanker_price_inr",
    "population_density", "complaint_count", "groundwater_trend", "rainfall_3mo_avg", "month",
]


def risk_label(score: float) -> str:
    if score < 30:
        return "Low"
    if score < 55:
        return "Medium"
    if score < 75:
        return "High"
    return "Critical"


@app.get("/")
def root():
    return {"status": "ok", "service": "Bengaluru Water Crisis API"}


@app.get("/api/summary")
def summary():
    s = db.get_city_summary()
    return {
        "avg_risk_score": round(s["avg_risk"], 1),
        "max_risk_score": round(s["max_risk"], 1),
        "critical_ward_count": int(s["critical_wards"]),
    }


@app.get("/api/wards")
def list_wards():
    wards = db.get_all_wards()
    latest = db.get_latest_readings()
    merged = wards.merge(latest, on=["ward_id", "ward_name"], how="left")
    cols = ["ward_id", "ward_name", "lat", "lon", "zone", "risk_score", "risk_label",
            "groundwater_depth_m", "tanker_price_inr", "rainfall_mm", "date"]
    return merged[cols].to_dict(orient="records")


@app.get("/api/months")
def available_months():
    months = db.get_available_months()
    return months.to_dict(orient="records")


@app.get("/api/months/breakdown")
def monthly_breakdown():
    """Per-month count of wards in each risk category — powers the scrubber chart."""
    counts = db.get_monthly_category_counts()
    result = {}
    for _, row in counts.iterrows():
        key = row["date"]
        if key not in result:
            result[key] = {"date": key, "year": int(row["year"]), "month": int(row["month"]),
                            "Low": 0, "Medium": 0, "High": 0, "Critical": 0}
        result[key][row["risk_label"]] = int(row["ward_count"])
    return list(result.values())


@app.get("/api/wards/by-month")
def wards_by_month(year: int, month: int):
    """All wards' readings for a specific month — lets the map show any point in time."""
    wards = db.get_all_wards()
    readings = db.get_readings_for_month(year, month)
    if readings.empty:
        raise HTTPException(status_code=404, detail="No data for that month")
    merged = wards.merge(readings, on=["ward_id", "ward_name"], how="left")
    cols = ["ward_id", "ward_name", "lat", "lon", "zone", "risk_score", "risk_label",
            "groundwater_depth_m", "tanker_price_inr", "rainfall_mm", "date"]
    return merged[cols].to_dict(orient="records")


@app.get("/api/wards/by-month")
def wards_by_month(year: int, month: int):
    """All wards with their reading for one specific month — powers the map when a
    month is selected from the city-wide scrubber chart."""
    df = db.get_wards_for_month(year, month)
    if df.empty:
        raise HTTPException(status_code=404, detail="No data for that month")
    cols = ["ward_id", "ward_name", "lat", "lon", "zone", "risk_score", "risk_label",
            "groundwater_depth_m", "tanker_price_inr", "rainfall_mm", "date"]
    return df[cols].to_dict(orient="records")


@app.get("/api/months/breakdown")
def months_breakdown():
    """Count of wards per risk band for every month — powers the stacked bar
    'scrubber' chart under the map."""
    df = db.get_monthly_breakdown()
    return df.to_dict(orient="records")


@app.get("/api/months/{year}/{month}")
def month_breakdown(year: int, month: int):
    """Returns every ward's risk reading for a given month, grouped by risk_label —
    powers the 'click a month on the chart' drill-down."""
    df = db.get_month_breakdown(year, month)
    if df.empty:
        raise HTTPException(status_code=404, detail="No data for that month")

    groups = {"Low": [], "Medium": [], "High": [], "Critical": []}
    for _, row in df.iterrows():
        groups[row["risk_label"]].append({
            "ward_id": int(row["ward_id"]),
            "ward_name": row["ward_name"],
            "zone": row["zone"],
            "risk_score": row["risk_score"],
            "groundwater_depth_m": row["groundwater_depth_m"],
            "tanker_price_inr": row["tanker_price_inr"],
        })

    return {
        "year": year,
        "month": month,
        "counts": {k: len(v) for k, v in groups.items()},
        "wards_by_label": groups,
    }


@app.get("/api/wards/{ward_id}/history")
def ward_history(ward_id: int):
    hist = db.get_ward_history(ward_id)
    if hist.empty:
        raise HTTPException(status_code=404, detail="Ward not found")
    return hist.to_dict(orient="records")


@app.get("/api/wards/{ward_id}/predict")
def predict_next_month(ward_id: int):
    hist = db.get_ward_history(ward_id)
    if hist.empty:
        raise HTTPException(status_code=404, detail="Ward not found")

    hist = hist.sort_values(["year", "month"])
    hist["groundwater_trend"] = hist["groundwater_depth_m"].diff().fillna(0)
    hist["rainfall_3mo_avg"] = hist["rainfall_mm"].rolling(3, min_periods=1).mean()

    latest = hist.iloc[-1]
    next_month = (latest["month"] % 12) + 1

    x = pd.DataFrame([{
        "rainfall_mm": latest["rainfall_mm"],
        "avg_temp_c": latest["avg_temp_c"],
        "groundwater_depth_m": latest["groundwater_depth_m"],
        "tanker_price_inr": latest["tanker_price_inr"],
        "population_density": latest["population_density"],
        "complaint_count": latest["complaint_count"],
        "groundwater_trend": latest["groundwater_trend"],
        "rainfall_3mo_avg": latest["rainfall_3mo_avg"],
        "month": next_month,
    }])[FEATURES]

    pred = float(model.predict(x)[0])
    pred = max(0, min(100, pred))

    return {
        "ward_id": ward_id,
        "ward_name": latest["ward_name"],
        "predicted_next_month_risk_score": round(pred, 1),
        "predicted_risk_label": risk_label(pred),
        "current_risk_score": latest["risk_score"],
        "current_risk_label": latest["risk_label"],
    }


# Serve the frontend statically at /app (optional convenience for local demo)
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="frontend")
