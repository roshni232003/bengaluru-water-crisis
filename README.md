# Neeru Nadi — Bengaluru Water Crisis Predictor & Civic Dashboard

Ward-level water scarcity risk prediction and monitoring for Bengaluru, combining
groundwater depletion, rainfall deficit, and tanker-price trends into a single
risk score — with an interactive map dashboard and a Power BI executive view.

> **Note on data:** This build uses a synthetic-but-realistic dataset modeled on
> Bengaluru's real 2023–24 groundwater crisis patterns (see `data/generate_data.py`
> docstring). Swap in real OpenWeatherMap / India-WRIS API calls using the same
> pipeline for a production version — the architecture doesn't change.

🔗 **Live Demo:** https://roshni232003.github.io/bengaluru-water-crisis/
🔗 **API Backend:** https://bengaluru-water-crisis-6.onrender.com/app/

## Stack

| Layer | Tech |
|---|---|
| Data ingestion | Python (API-ready structure) |
| Database | SQLite (demo) → PostgreSQL/Neon (production, same pattern as ARIA) |
| ML | XGBoost regression, R² 0.85 on held-out data |
| Backend API | FastAPI |
| Frontend | HTML/CSS/JS, Leaflet.js map, Chart.js |
| BI | Power BI (star-schema CSV exports) |

## Project structure

```
bengaluru-water-crisis/
├── data/
│   └── generate_data.py       # builds wards.csv + historical_readings.csv
├── model/
│   └── train_model.py         # trains XGBoost risk model
├── backend/
│   ├── database.py            # SQLite/Postgres data layer
│   ├── main.py                # FastAPI app
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
└── powerbi/
    └── export_for_powerbi.py  # star-schema CSV export for Power BI
```

## Setup (run in order)

```bash
# 1. Generate the dataset
cd data && python generate_data.py

# 2. Train the model
cd ../model && pip install xgboost scikit-learn pandas
python train_model.py

# 3. Set up and run the backend
cd ../backend
pip install -r requirements.txt
python database.py          # loads CSVs into SQLite
uvicorn main:app --reload --port 8000

# 4. Open the dashboard
# http://localhost:8000/app/
# (backend serves the frontend directly, or open frontend/index.html
#  in a browser — just make sure the API is running on :8000)

# 5. Export for Power BI
cd ../powerbi
python export_for_powerbi.py
# Then in Power BI Desktop: Get Data > Text/CSV > load all 4 files from
# powerbi/output/, relate on ward_id and date, and build visuals
# (see docstring in export_for_powerbi.py for suggested visual list)
```

## API endpoints

- `GET /api/summary` — city-wide KPIs
- `GET /api/wards` — all wards with latest readings
- `GET /api/wards/{id}/history` — 24-month history for one ward
- `GET /api/wards/{id}/predict` — next-month risk forecast

## What makes this project distinctive

Most portfolio projects predict a single well-known target (churn, house prices,
sentiment). This one fuses three normally-siloed signals — meteorological
(rainfall/temp), hydrogeological (groundwater depth), and economic (tanker black-market
pricing) — into one composite civic risk score, at ward granularity, for a crisis
that's genuinely in the news. That combination is what you can speak to in an
interview, more than any claim of being "the first ever."

## Talking points for interviews

- **Feature engineering:** lag features (groundwater trend) and rolling averages
  (3-month rainfall) mattered more than raw values — shows in `feature_importance.csv`.
- **Why XGBoost over linear regression:** non-linear interactions between
  drought-month tanker price spikes and groundwater depth.
- **Design decision:** SQLite for demo simplicity, with a one-line swap to
  Postgres/Neon for production — same pattern you used in ARIA.
- **Honesty about data:** synthetic data clearly labeled as such, with a stated
  path to real APIs — this matters more to interviewers than pretending it's real.
