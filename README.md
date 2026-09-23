# AnkurAI Smart Crop Advisory System

AnkurAI is a full-stack smart farming assistant for crop recommendation, irrigation planning, pest-outbreak forecasting, leaf disease detection, market support, and farmer-friendly advisory reports.

The project combines a Flask API, React dashboard, SQLite persistence, scikit-learn models, TensorFlow disease detection, and optional live integrations for weather, mandi prices, and AI-assisted farmer guidance.

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [System Architecture](#system-architecture)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Model Training](#model-training)
- [API Overview](#api-overview)
- [Screenshots](#screenshots)
- [Progressive Web App](#progressive-web-app)
- [Analytics Dashboard](#analytics-dashboard)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)

## Features

- Crop recommendation using a Random Forest classifier.
- Irrigation requirement prediction using a Random Forest regressor.
- Weekly pest-outbreak forecasting model trained from tabular field, weather, trap, and pest-history data, surfaced in the Planning & Soil Care workflow.
- Leaf disease detection using MobileNetV2-based CNN artifacts when available.
- Farmer advisory reports with fertilizer, season, irrigation, pest-risk, and reasoning cards.
- JWT authentication with farmer and admin roles.
- Farmer dashboard for crop prediction, disease detection, market insights, AI chat, and report export.
- Admin dashboard for metrics, model artifacts, feature importance, and recent activity.
- Market support using MSP reference data, KVK contacts, seasonal tips, and optional live Agmarknet mandi prices.
- Optional Groq-powered Ask AI assistant for follow-up farming questions.
- Browser geolocation-based weather autofill through Open-Meteo.
- Installable React Progressive Web App.
- Separate Streamlit analytics dashboard.
- English, Hindi, and Marathi UI language support.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | React 18, React Router, Axios, Tailwind CSS |
| Backend | Flask, Flask-CORS, Flask-JWT-Extended |
| Database | SQLite |
| ML | scikit-learn, pandas, NumPy, joblib |
| Disease Detection | TensorFlow, MobileNetV2, Pillow |
| AI Assistant | Groq API |
| Dashboard | Streamlit, matplotlib |
| Reports | Browser print/PDF, html2canvas, jsPDF |

## System Architecture

```text
React PWA
   |
   | Axios + JWT
   v
Flask REST API
   |
   |-- Auth, crop, irrigation, pest outbreak, disease, advisory, market, AI, system routes
   |
   v
SQLite database + ML artifacts
   |
   |-- users and prediction logs
   |-- Random Forest crop and irrigation models
   |-- Random Forest pest-outbreak model
   |-- TensorFlow disease model and class labels
   |-- metrics JSON and feature-importance CSV files
```

## Project Structure

```text
smart-crop-advisory-system/
|-- backend/
|   |-- app.py
|   |-- config.py
|   |-- requirements.txt
|   |-- database/
|   |-- models/
|   |-- routes/
|   |-- services/
|   `-- utils/
|-- frontend/
|   |-- public/
|   |-- src/
|   `-- package.json
|-- ml/
|   |-- crop_data.csv
|   |-- data/
|   |   `-- pest_outbreak_training.csv
|   |-- train_pipeline.py
|   |-- train_disease_cnn.py
|   `-- models/
|-- dashboard/
|   |-- dashboard.py
|   `-- requirements.txt
`-- README.md
```

Generated folders such as `venv/`, `.venv/`, `node_modules/`, `build/`, `tmp/`, database files, and local `.env` files are ignored by Git.

## Getting Started

### Prerequisites

- Python 3.10 or newer
- Node.js 18 or newer
- npm
- Git
- Optional: TensorFlow-compatible environment for CNN training
- Optional: data.gov.in API key for live mandi prices
- Optional: Groq API key for Ask AI

### 1. Clone the Repository

```bash
git clone <repository-url>
cd smart-crop-advisory-system
```

### 2. Start the Backend

Windows PowerShell:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

macOS/Linux:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

Backend health check:

```text
http://localhost:5000/api/health
```

### 3. Start the Frontend

Open a second terminal:

```bash
cd frontend
npm install
npm start
```

Frontend URL:

```text
http://localhost:3000
```

The React development server proxies `/api` requests to `http://localhost:5000`.

## Environment Variables

Create `backend/.env` for local configuration:

```env
APP_ENV=development
FLASK_DEBUG=true
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
CORS_ORIGINS=http://localhost:3000
LOG_LEVEL=INFO
DB_PATH=database/predictions.db
ML_DIR=../ml
JWT_SECRET_KEY=change-this-before-production

GROQ_API_KEY=
GROQ_MODEL=openai/gpt-oss-120b
GROQ_TIMEOUT_SECONDS=25

DATA_GOV_API_KEY=
MANDI_API_TIMEOUT_SECONDS=12
MANDI_CACHE_TTL_SECONDS=1800
```

Create `frontend/.env` only when the API is hosted somewhere other than the local proxy:

```env
REACT_APP_API_BASE_URL=
```

Do not commit `.env` files or real API keys.

## Model Training

The repository uses `ml/train_pipeline.py` for tabular Random Forest training. It writes:

- A versioned `.pkl` model
- A metrics JSON file
- A feature-importance CSV file

### Crop and Irrigation Models

Train from `ml/crop_data.csv` or your own compatible CSV:

```powershell
python .\ml\train_pipeline.py `
  --csv-path .\ml\crop_data.csv `
  --classification-target label `
  --regression-target irrigation_requirement `
  --test-size 0.2 `
  --cv-folds 5 `
  --n-estimators 500 `
  --random-state 42 `
  --output-dir .\ml\models
```

### Pest-Outbreak Forecasting Model

The pest model is trained from weekly tabular records, not leaf images. One row represents one field, crop, pest, and observation week.

Required dataset path:

```text
ml/data/pest_outbreak_training.csv
```

Core columns:

```text
crop_rice,crop_wheat,crop_maize,crop_cotton,crop_soybean,
pest_stem_borer,pest_aphid,pest_fall_armyworm,pest_whitefly,
month,days_after_sowing,temperature_c,humidity_pct,rainfall_7d_mm,
rainfall_14d_mm,wind_speed_kmh,soil_moisture_pct,trap_count_7d,
previous_pest_count_7d,outbreak_next_7d
```

Current local dataset summary:

- 20,000 weekly records
- 5 crops and 4 pest classes
- 1,000 rows per crop-pest combination
- 4 seasons: 2023, 2024, 2025, 2026
- 10 farm/location IDs
- Both outbreak and non-outbreak labels

Training command:

```powershell
python .\ml\train_pipeline.py `
  --csv-path .\ml\data\pest_outbreak_training.csv `
  --feature-columns "crop_rice,crop_wheat,crop_maize,crop_cotton,crop_soybean,pest_stem_borer,pest_aphid,pest_fall_armyworm,pest_whitefly,month,days_after_sowing,temperature_c,humidity_pct,rainfall_7d_mm,rainfall_14d_mm,wind_speed_kmh,soil_moisture_pct,trap_count_7d,previous_pest_count_7d" `
  --classification-target outbreak_next_7d `
  --test-size 0.2 `
  --cv-folds 5 `
  --n-estimators 500 `
  --random-state 42 `
  --output-dir .\ml\models\pest_outbreak
```

Generated pest artifacts:

```text
ml/models/pest_outbreak/rf_classifier_outbreak_next_7d_v*.pkl
ml/models/pest_outbreak/rf_classifier_outbreak_next_7d_metrics.json
ml/models/pest_outbreak/rf_classifier_outbreak_next_7d_feature_importance.csv
```

Latest recorded pest metrics:

```json
{
  "cv_accuracy_mean": 0.851125,
  "cv_f1_weighted_mean": 0.8110528244570283,
  "test_accuracy": 0.8555,
  "test_f1_weighted": 0.8234183956408893
}
```

### Leaf Disease Model

The disease detector uses TensorFlow/MobileNetV2 artifacts when present.

Train the leaf disease model:

```powershell
python .\backend\leaf_disease\train_model.py `
  --dataset-dir .\backend\data\PlantVillage `
  --epochs 12 `
  --fine-tune-epochs 8 `
  --batch-size 32
```

Expected artifacts:

```text
ml/models/leaf_disease_mobilenetv2.keras
ml/models/labels.json
ml/models/leaf_disease_training_report.json
```

Restart the backend after training so the disease model is loaded at startup.

## API Overview

Most endpoints require a JWT bearer token except health, signup, login, and the public disease endpoint.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Backend health check |
| POST | `/api/auth/signup` | Register a farmer or admin |
| POST | `/api/auth/login` | Login and receive access token |
| GET | `/api/auth/me` | Fetch current user |
| POST | `/api/predict/crop` | Predict recommended crop |
| POST | `/api/predict/irrigation` | Predict irrigation requirement |
| POST | `/api/predict/pest-outbreak` | Predict next-7-day pest outbreak risk |
| POST | `/api/advisory` | Generate crop advisory report |
| POST | `/api/disease/detect` | Authenticated disease detection route |
| POST | `/api/detect-leaf-disease` | Public MobileNetV2 leaf disease route |
| GET | `/api/market/overview` | MSP, market, KVK, schemes, and seasonal tips |
| POST | `/api/ai/chat` | Ask AI follow-up questions |
| GET | `/api/predictions` | Recent prediction history |
| GET | `/api/model-info` | Model metrics and active artifacts |
| GET | `/api/admin/stats` | Admin usage statistics |

### Example Crop Prediction Payload

```json
{
  "N": 52,
  "P": 50,
  "K": 52,
  "temperature": 20,
  "humidity": 68,
  "ph": 6.7,
  "rainfall": 140
}
```

Low-confidence crop predictions still return the best crop instead of failing. The response includes `is_low_confidence`, `confidence_threshold`, `confidence_note`, and `top_crops` so the frontend can show a review warning and alternatives.

### Example Pest-Outbreak Payload

```json
{
  "crop": "wheat",
  "month": 9,
  "days_after_sowing": 48,
  "temperature_c": 27,
  "humidity_pct": 78,
  "rainfall_7d_mm": 34,
  "rainfall_14d_mm": 62,
  "wind_speed_kmh": 8,
  "soil_moisture_pct": 42,
  "trap_count_7d": 11,
  "previous_pest_count_7d": 7
}
```

The endpoint returns ranked risk for stem borer, aphid, fall armyworm, and whitefly where supported by the trained model. The frontend uses this in the `Planning & Soil Care` tab after crop prediction.

### Example Advisory Payload

```json
{
  "crop": "wheat",
  "confidence": 0.92,
  "irrigation": 2.4,
  "state": "Maharashtra",
  "season": "Rabi",
  "inputs": {
    "N": 52,
    "P": 50,
    "K": 52,
    "temperature": 20,
    "humidity": 68,
    "ph": 6.7,
    "rainfall": 140
  },
  "top_crops": [
    { "crop": "wheat", "confidence": 0.92 },
    { "crop": "maize", "confidence": 0.05 }
  ]
}
```

### Leaf Disease Upload

Send a multipart request with a file field named `file`:

```text
POST /api/detect-leaf-disease
Content-Type: multipart/form-data
file=<leaf-image.jpg>
```

Supported formats: JPG, JPEG, PNG. Maximum size: 5 MB.

### Market Overview

```text
GET /api/market/overview?state=Maharashtra&season=Rabi&crop=wheat
```

When `DATA_GOV_API_KEY` is configured, the market response includes recent Agmarknet mandi records from data.gov.in. Without the key, the app keeps static MSP, scheme, KVK, and seasonal guidance fallbacks for demos.

## Screenshots

Add final screenshots in `docs/screenshots/` before publishing the repository. Recommended captures:

| Screen | Suggested file |
| --- | --- |
| Farmer crop prediction and advisory report | `docs/screenshots/farmer-crop-prediction.png` |
| Low-confidence crop warning with top alternatives | `docs/screenshots/low-confidence-crop-warning.png` |
| Planning outlook, pest outbreak forecast, and soil care | `docs/screenshots/planning-soil-care.png` |
| Leaf disease prediction result | `docs/screenshots/leaf-disease-prediction.png` |
| Admin dashboard model metrics | `docs/screenshots/admin-model-metrics.png` |

Example Markdown once screenshots are exported:

```md
![Farmer crop prediction](docs/screenshots/farmer-crop-prediction.png)
![Planning and soil care](docs/screenshots/planning-soil-care.png)
```

## Progressive Web App

The frontend is installable as a PWA in production builds.

Build:

```bash
cd frontend
npm run build
```

Deploy `frontend/build/` behind HTTPS. Configure the server to:

- Serve `index.html` for client-side routes.
- Serve `manifest.json`, icons, and `service-worker.js` from the site root.
- Expose the Flask API through HTTPS or set `REACT_APP_API_BASE_URL` before building.

For mobile LAN testing during development:

```powershell
cd frontend
$env:HOST = "0.0.0.0"
npm start
```

Then open `http://<PC_IPV4_ADDRESS>:3000` on a phone connected to the same network. Full PWA installation requires HTTPS, except for localhost browser exceptions.

## Analytics Dashboard

The Streamlit dashboard shows model metrics, feature importance, confusion matrices, prediction distribution, and recent activity.

```powershell
cd dashboard
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run dashboard.py
```

## Testing

Backend tests:

```powershell
cd backend
.\venv\Scripts\python.exe -m pytest
```

Frontend tests:

```bash
cd frontend
npm test
```

## Troubleshooting

- If the backend cannot load crop or irrigation models, confirm `ml/models/` contains the latest `rf_classifier_*_v*.pkl` and `rf_regressor_*_v*.pkl` files.
- If pest forecasting fails, confirm `ml/models/pest_outbreak/` contains `rf_classifier_outbreak_next_7d_v*.pkl` and rerun the pest training command if needed.
- If disease detection fails, confirm TensorFlow is installed and the `.keras` model plus label JSON files exist.
- If the frontend cannot reach Flask, confirm Flask is running on port `5000` and `frontend/package.json` still has the local proxy.
- If Ask AI fails, set `GROQ_API_KEY` in `backend/.env` and restart the backend.
- If mandi prices are not live, set `DATA_GOV_API_KEY`; otherwise the fallback market guidance is expected.
- If geolocation does not work, allow location access in the browser and use HTTPS for production.
- If print/PDF output looks pale, enable background graphics in the browser print dialog.

## Roadmap

- Add stronger validation and provenance metadata for pest threshold labels.
- Add per-class disease precision, recall, confusion matrix, and sample review screens.
- Improve Hindi and Marathi translation quality for production demos.
- Add weather forecast history and mandi price trends.
- Add SHAP or LIME explanations for model interpretability.
- Move from SQLite to PostgreSQL for multi-user deployment.
- Deploy backend, frontend, and dashboard to cloud infrastructure.

## License

This project is currently maintained as an academic/final-year project. Add a license file before publishing publicly if you want others to reuse or modify it under explicit terms.
