"""
CareSync — FastAPI Backend
===========================
Local/edge-first clinical decision-support API.

Architecture note: This service is designed to run entirely on-device.
The ML model, TF-IDF vectorizer, and all preprocessing artifacts are
loaded from local disk at startup. NO patient data is transmitted to
any external API, LLM service, or cloud endpoint at any point.

Endpoints:
  POST /api/evaluate-risk — Run risk assessment on a patient
  GET  /health            — Liveness check
"""

import os
import numpy as np
from pathlib import Path
from contextlib import asynccontextmanager

import joblib
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from scipy.sparse import csr_matrix, hstack

from .schemas import (
    RiskAssessmentRequest,
    RiskAssessmentResponse,
    ContributingFactor,
)

# ── Model artifacts path ──────────────────────────────────────────────
MODEL_DIR = Path(__file__).resolve().parent / "models"

# Global model artifacts (loaded at startup)
model = None
scaler = None
tfidf = None
feature_names = None
numeric_cols = None
label_map = None
vital_cols = None

REVERSE_LABEL_MAP = {}  # filled at startup


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load ML model artifacts at startup — no lazy loading needed for this scale."""
    global model, scaler, tfidf, feature_names, numeric_cols, label_map, vital_cols, REVERSE_LABEL_MAP

    print("🔄 Loading model artifacts from", MODEL_DIR)
    model = joblib.load(MODEL_DIR / "risk_model.joblib")
    scaler = joblib.load(MODEL_DIR / "scaler.joblib")
    tfidf = joblib.load(MODEL_DIR / "tfidf_vectorizer.joblib")
    feature_names = joblib.load(MODEL_DIR / "feature_names.joblib")
    numeric_cols = joblib.load(MODEL_DIR / "numeric_cols.joblib")
    label_map = joblib.load(MODEL_DIR / "label_map.joblib")
    vital_cols = joblib.load(MODEL_DIR / "vital_cols.joblib")
    REVERSE_LABEL_MAP = {v: k for k, v in label_map.items()}
    print("✅ Model loaded. Features:", len(feature_names))
    yield
    print("🛑 Shutting down CareSync backend")


app = FastAPI(
    title="CareSync API",
    description="Privacy-preserving clinical risk assessment — runs 100% on-device",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS — allow Vite dev server ──────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173",
                    "http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def build_feature_vector(req: RiskAssessmentRequest) -> np.ndarray:
    """
    Mirror the training feature pipeline for a single patient.

    ASSUMPTION: Since the API receives a *single* vitals snapshot (not 24h
    time series), we treat all time-series aggregates (mean, std, min, max,
    delta) as derived from that single reading:
      - latest = mean = min = max = the provided value
      - std = 0 (no variance from a single point)
      - delta = 0 (no trend from a single point)

    In a production system, the frontend or device would buffer readings
    and send the full window; the API would compute real rolling stats.
    """
    v = req.vitals
    vital_values = {
        "heart_rate": v.heart_rate,
        "systolic_bp": v.systolic_bp,
        "diastolic_bp": v.diastolic_bp,
        "temperature": v.temperature,
        "spo2": v.spo2,
    }

    # Build vitals features matching training column order
    numeric_dict = {}
    for col in ["heart_rate", "systolic_bp", "diastolic_bp", "temperature", "spo2"]:
        val = vital_values[col]
        numeric_dict[f"{col}_latest"] = val
        numeric_dict[f"{col}_mean"] = val
        numeric_dict[f"{col}_std"] = 0.0  # single reading
        numeric_dict[f"{col}_min"] = val
        numeric_dict[f"{col}_max"] = val
        numeric_dict[f"{col}_delta"] = 0.0  # no trend from single point

    # Demographics
    d = req.demographics
    numeric_dict["age"] = d.age
    numeric_dict["gender_enc"] = 1 if d.gender == "Male" else 0
    smoking_map = {"Never": 0, "Former": 1, "Current": 2}
    numeric_dict["smoking_enc"] = smoking_map.get(d.smoking_status, 0)
    numeric_dict["diabetes_enc"] = 1 if d.diabetes == "Yes" else 0
    numeric_dict["hypertension_enc"] = 1 if d.hypertension == "Yes" else 0

    # Assemble numeric vector in the same column order as training
    numeric_vector = np.array([[numeric_dict.get(c, 0.0) for c in numeric_cols]])

    # Scale
    numeric_scaled = scaler.transform(numeric_vector)

    # TF-IDF on combined EHR text
    combined_text = (req.ehr_notes or "") + " " + (req.clinical_summary or "")
    text_vector = tfidf.transform([combined_text])

    # Fuse
    X = hstack([csr_matrix(numeric_scaled), text_vector]).toarray()
    return X


@app.post("/api/evaluate-risk", response_model=RiskAssessmentResponse)
async def evaluate_risk(req: RiskAssessmentRequest):
    """
    Evaluate a patient's disease risk level.

    Returns a risk score (0-1), risk level (Low/Medium/High), and the
    top contributing factors from the model's feature importances.
    """
    try:
        X = build_feature_vector(req)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Feature extraction failed: {str(e)}")

    # Predict probabilities
    proba = model.predict_proba(X)[0]  # shape: (n_classes,)

    # Risk score: weighted combination biased toward high-risk probability
    # proba[2] is P(High), proba[1] is P(Medium)
    risk_score = float(proba[2] * 1.0 + proba[1] * 0.5 + proba[0] * 0.0)

    # Risk level: use the predicted class
    predicted_class = int(np.argmax(proba))
    risk_level = REVERSE_LABEL_MAP.get(predicted_class, "Low")

    # Override to High if P(High) is notably elevated (safety margin)
    # Even if the model's argmax says Medium, if P(High) > 0.35, escalate
    if proba[2] > 0.35:
        risk_level = "High"

    # Contributing factors from feature importances
    if hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
    elif hasattr(model, "coef_"):
        importances = np.mean(np.abs(model.coef_), axis=0)
    else:
        importances = np.zeros(len(feature_names))

    # Get the input values for context
    feat_imp_pairs = list(zip(feature_names, importances))
    feat_imp_pairs.sort(key=lambda x: x[1], reverse=True)

    top_factors = [
        ContributingFactor(
            factor=_humanize_feature(fname),
            importance=round(float(imp), 4)
        )
        for fname, imp in feat_imp_pairs[:3]
    ]

    return RiskAssessmentResponse(
        risk_score=round(risk_score, 4),
        risk_level=risk_level,
        contributing_factors=top_factors,
        confidence=round(float(np.max(proba)), 4),
    )


def _humanize_feature(feature_name: str) -> str:
    """Convert internal feature names to human-readable labels."""
    mapping = {
        "heart_rate_latest": "Heart Rate",
        "heart_rate_mean": "Avg Heart Rate",
        "heart_rate_std": "Heart Rate Variability",
        "heart_rate_delta": "Heart Rate Trend",
        "heart_rate_min": "Min Heart Rate",
        "heart_rate_max": "Max Heart Rate",
        "systolic_bp_latest": "Systolic Blood Pressure",
        "systolic_bp_mean": "Avg Systolic BP",
        "systolic_bp_std": "BP Variability",
        "systolic_bp_delta": "BP Trend",
        "systolic_bp_min": "Min Systolic BP",
        "systolic_bp_max": "Max Systolic BP",
        "diastolic_bp_latest": "Diastolic Blood Pressure",
        "diastolic_bp_mean": "Avg Diastolic BP",
        "diastolic_bp_std": "Diastolic BP Variability",
        "diastolic_bp_delta": "Diastolic BP Trend",
        "diastolic_bp_min": "Min Diastolic BP",
        "diastolic_bp_max": "Max Diastolic BP",
        "temperature_latest": "Body Temperature",
        "temperature_mean": "Avg Temperature",
        "temperature_std": "Temperature Variability",
        "temperature_delta": "Temperature Trend",
        "temperature_min": "Min Temperature",
        "temperature_max": "Max Temperature",
        "spo2_latest": "Oxygen Saturation (SpO₂)",
        "spo2_mean": "Avg SpO₂",
        "spo2_std": "SpO₂ Variability",
        "spo2_delta": "SpO₂ Trend",
        "spo2_min": "Min SpO₂",
        "spo2_max": "Max SpO₂",
        "age": "Patient Age",
        "gender_enc": "Gender",
        "smoking_enc": "Smoking Status",
        "diabetes_enc": "Diabetes",
        "hypertension_enc": "Hypertension",
    }
    return mapping.get(feature_name, feature_name.replace("_", " ").title())


@app.get("/health")
async def health_check():
    """Basic liveness check — confirms model is loaded and ready."""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "service": "CareSync",
        "privacy": "All processing is local — no data leaves this device",
    }
