"""
Database layer. Uses SQLite locally for a zero-config demo.

To move to PostgreSQL (Neon) for production — same pattern as ARIA:
    DATABASE_URL = "postgresql://user:pass@ep-xxxx.neon.tech/dbname"
    engine = create_engine(DATABASE_URL)
Everything else (models, queries) stays identical since we use SQLAlchemy Core/ORM.
"""
import os
import pandas as pd
from sqlalchemy import create_engine, text

BASE = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE, "water_crisis.db")
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DB_PATH}")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})


def load_csv_data():
    """Loads the generated CSVs into the database. Run once at startup / setup."""
    data_dir = os.path.join(BASE, "..", "data", "output")
    wards = pd.read_csv(os.path.join(data_dir, "wards.csv"))
    readings = pd.read_csv(os.path.join(data_dir, "historical_readings.csv"))

    wards.to_sql("wards", engine, if_exists="replace", index=False)
    readings.to_sql("readings", engine, if_exists="replace", index=False)
    print(f"Loaded {len(wards)} wards and {len(readings)} readings into {DATABASE_URL}")


def get_latest_readings():
    query = """
    SELECT r.*
    FROM readings r
    INNER JOIN (
        SELECT ward_id, MAX(date) AS max_date FROM readings GROUP BY ward_id
    ) latest ON r.ward_id = latest.ward_id AND r.date = latest.max_date
    """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)


def get_ward_history(ward_id: int):
    query = "SELECT * FROM readings WHERE ward_id = :ward_id ORDER BY date"
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params={"ward_id": ward_id})


def get_all_wards():
    with engine.connect() as conn:
        return pd.read_sql(text("SELECT * FROM wards"), conn)


def get_readings_for_month(year: int, month: int):
    """All ward readings for one specific calendar month (for the month scrubber)."""
    query = "SELECT * FROM readings WHERE year = :year AND month = :month"
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params={"year": year, "month": month})


def get_available_months():
    query = "SELECT DISTINCT year, month, date FROM readings ORDER BY year, month"
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)


def get_monthly_category_counts():
    """Count of wards in each risk_label, per month — powers the stacked bar scrubber."""
    query = """
    SELECT year, month, date, risk_label, COUNT(*) as ward_count
    FROM readings
    GROUP BY year, month, risk_label
    ORDER BY year, month
    """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)


def get_wards_for_month(year: int, month: int):
    """All wards joined with their reading for one specific month (for map filtering)."""
    query = """
    SELECT w.ward_id, w.ward_name, w.lat, w.lon, w.zone,
           r.risk_score, r.risk_label, r.groundwater_depth_m, r.tanker_price_inr,
           r.rainfall_mm, r.date
    FROM wards w
    JOIN readings r ON r.ward_id = w.ward_id
    WHERE r.year = :year AND r.month = :month
    """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params={"year": year, "month": month})


def get_monthly_breakdown():
    """Count of wards in each risk band, per calendar month across the whole dataset —
    powers the city-wide stacked-bar 'scrubber' chart."""
    query = """
    SELECT year, month, date, risk_label, COUNT(*) as cnt
    FROM readings
    GROUP BY year, month, date, risk_label
    ORDER BY date
    """
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)

    pivot = df.pivot_table(index=["year", "month", "date"], columns="risk_label", values="cnt", fill_value=0)
    pivot = pivot.reset_index().sort_values("date")
    for label in ["Low", "Medium", "High", "Critical"]:
        if label not in pivot.columns:
            pivot[label] = 0
    return pivot


def get_month_breakdown(year: int, month: int):
    """All ward readings for a specific calendar month, for the drill-down view."""
    query = """
    SELECT r.ward_id, r.ward_name, w.zone, r.risk_score, r.risk_label,
           r.rainfall_mm, r.groundwater_depth_m, r.tanker_price_inr
    FROM readings r
    JOIN wards w ON w.ward_id = r.ward_id
    WHERE r.year = :year AND r.month = :month
    ORDER BY r.risk_score DESC
    """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params={"year": year, "month": month})


def get_city_summary():
    query = """
    SELECT AVG(r.risk_score) as avg_risk, MAX(r.risk_score) as max_risk,
           SUM(CASE WHEN r.risk_label = 'Critical' THEN 1 ELSE 0 END) as critical_wards
    FROM readings r
    INNER JOIN (
        SELECT ward_id, MAX(date) AS max_date FROM readings GROUP BY ward_id
    ) latest ON r.ward_id = latest.ward_id AND r.date = latest.max_date
    """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn).iloc[0].to_dict()


if __name__ == "__main__":
    load_csv_data()
