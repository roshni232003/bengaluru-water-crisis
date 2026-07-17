"""
Trains an XGBoost regressor to predict next-month water scarcity risk_score
per ward, using rainfall, groundwater, tanker price and complaint trends.

Run: python train_model.py
Outputs: risk_model.json, feature_importance.csv into ./output/
"""
import os
import pandas as pd
import numpy as np
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

BASE = os.path.dirname(__file__)
DATA_PATH = os.path.join(BASE, "..", "data", "output", "historical_readings.csv")
OUT_DIR = os.path.join(BASE, "output")
os.makedirs(OUT_DIR, exist_ok=True)

df = pd.read_csv(DATA_PATH)
df = df.sort_values(["ward_id", "year", "month"])

# Feature engineering: lag features + rolling trend per ward, predicting NEXT month's risk_score
df["groundwater_trend"] = df.groupby("ward_id")["groundwater_depth_m"].diff().fillna(0)
df["rainfall_3mo_avg"] = df.groupby("ward_id")["rainfall_mm"].transform(lambda s: s.rolling(3, min_periods=1).mean())
df["target_next_risk"] = df.groupby("ward_id")["risk_score"].shift(-1)

df = df.dropna(subset=["target_next_risk"])

features = [
    "rainfall_mm", "avg_temp_c", "groundwater_depth_m", "tanker_price_inr",
    "population_density", "complaint_count", "groundwater_trend", "rainfall_3mo_avg", "month",
]
X = df[features]
y = df["target_next_risk"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = XGBRegressor(
    n_estimators=200,
    max_depth=4,
    learning_rate=0.08,
    subsample=0.85,
    colsample_bytree=0.85,
    random_state=42,
)
model.fit(X_train, y_train)

preds = model.predict(X_test)
mae = mean_absolute_error(y_test, preds)
r2 = r2_score(y_test, preds)
print(f"Test MAE: {mae:.2f}  |  Test R2: {r2:.3f}")

model_path = os.path.join(OUT_DIR, "risk_model.json")
model.save_model(model_path)
print(f"Saved model to {model_path}")

importance = pd.DataFrame({
    "feature": features,
    "importance": model.feature_importances_,
}).sort_values("importance", ascending=False)
importance.to_csv(os.path.join(OUT_DIR, "feature_importance.csv"), index=False)
print(importance.to_string(index=False))
