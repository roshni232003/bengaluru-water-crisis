#!/usr/bin/env bash
# Deployment build script — regenerates data, trains the model, and loads the DB.
# Render (and similar platforms) will run this automatically as the build command.
set -e

echo "== Installing backend dependencies =="
pip install -r backend/requirements.txt
pip install xgboost scikit-learn pandas

echo "== Generating dataset =="
cd data && python generate_data.py && cd ..

echo "== Training model =="
cd model && python train_model.py && cd ..

echo "== Loading database =="
cd backend && python database.py && cd ..

echo "== Build complete =="
