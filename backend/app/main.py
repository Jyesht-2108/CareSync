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
DISEASE_MODEL_DIR = MODEL_DIR / "disease_specific"

# Global model artifacts (loaded at startup)
model = None
scaler = None
tfidf = None
feature_names = None
numeric_cols = None
label_map = None
vital_cols = None

# Disease-specific models
heart_model = None
heart_scaler = None
heart_features = None

diabetes_model = None
diabetes_scaler = None
diabetes_features = None

stroke_model = None
stroke_scaler = None
stroke_features = None

multi_disease_model = None
multi_disease_labels = None
multi_disease_symptoms = None

REVERSE_LABEL_MAP = {}  # filled at startup


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load ML model artifacts at startup — no lazy loading needed for this scale."""
    global model, scaler, tfidf, feature_names, numeric_cols, label_map, vital_cols, REVERSE_LABEL_MAP
    global heart_model, heart_scaler, heart_features
    global diabetes_model, diabetes_scaler, diabetes_features
    global stroke_model, stroke_scaler, stroke_features
    global multi_disease_model, multi_disease_labels, multi_disease_symptoms

    print("🔄 Loading model artifacts from", MODEL_DIR)
    
    # Main mortality risk model
    model = joblib.load(MODEL_DIR / "risk_model.joblib")
    scaler = joblib.load(MODEL_DIR / "scaler.joblib")
    tfidf = joblib.load(MODEL_DIR / "tfidf_vectorizer.joblib")
    feature_names = joblib.load(MODEL_DIR / "feature_names.joblib")
    numeric_cols = joblib.load(MODEL_DIR / "numeric_cols.joblib")
    label_map = joblib.load(MODEL_DIR / "label_map.joblib")
    vital_cols = joblib.load(MODEL_DIR / "vital_cols.joblib")
    REVERSE_LABEL_MAP = {v: k for k, v in label_map.items()}
    print("✅ Mortality risk model loaded. Features:", len(feature_names))
    
    # Disease-specific models
    try:
        print("🔄 Loading disease-specific models...")
        
        # Heart disease model
        heart_model = joblib.load(DISEASE_MODEL_DIR / "heart_disease_model.joblib")
        heart_scaler = joblib.load(DISEASE_MODEL_DIR / "heart_disease_scaler.joblib")
        heart_features = joblib.load(DISEASE_MODEL_DIR / "heart_disease_features.joblib")
        print("  ✅ Heart disease model loaded")
        
        # Diabetes model
        diabetes_model = joblib.load(DISEASE_MODEL_DIR / "diabetes_model.joblib")
        diabetes_scaler = joblib.load(DISEASE_MODEL_DIR / "diabetes_scaler.joblib")
        diabetes_features = joblib.load(DISEASE_MODEL_DIR / "diabetes_features.joblib")
        print("  ✅ Diabetes model loaded")
        
        # Stroke model
        stroke_model = joblib.load(DISEASE_MODEL_DIR / "stroke_model.joblib")
        stroke_scaler = joblib.load(DISEASE_MODEL_DIR / "stroke_scaler.joblib")
        stroke_features = joblib.load(DISEASE_MODEL_DIR / "stroke_features.joblib")
        print("  ✅ Stroke model loaded")
        
        # Multi-disease model
        multi_disease_model = joblib.load(DISEASE_MODEL_DIR / "multi_disease_model.joblib")
        multi_disease_labels = joblib.load(DISEASE_MODEL_DIR / "multi_disease_labels.joblib")
        multi_disease_symptoms = joblib.load(DISEASE_MODEL_DIR / "multi_disease_symptoms.joblib")
        print("  ✅ Multi-disease model loaded")
        
        print("✅ All disease models loaded successfully")
    except Exception as e:
        print(f"⚠️  Warning: Could not load disease models: {e}")
        print("   Disease predictions will be unavailable")
    
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


def extract_heart_features(req: RiskAssessmentRequest) -> np.ndarray:
    """
    Extract features for heart disease prediction from patient data.
    
    Heart disease model expects 13 features:
    age, sex, cp (chest pain), trestbps (resting BP), chol (cholesterol),
    fbs (fasting blood sugar), restecg, thalach (max HR), exang, oldpeak,
    slope, ca, thal
    
    We approximate from available vitals/demographics.
    """
    v = req.vitals
    d = req.demographics
    notes = (req.ehr_notes + " " + req.clinical_summary).lower()
    
    # Map available data to heart disease features
    features = {
        'age': d.age,
        'sex': 1 if d.gender == "Male" else 0,
        'cp': 2,  # Default: atypical angina (can't determine from vitals alone)
        'trestbps': v.systolic_bp,
        'chol': 200,  # Default cholesterol (not available in vitals)
        'fbs': 1 if d.diabetes == "Yes" else 0,  # Fasting blood sugar > 120
        'restecg': 0,  # Normal resting ECG (not available)
        'thalach': v.heart_rate,  # Use current HR as max HR
        'exang': 1 if 'chest pain' in notes or 'angina' in notes else 0,
        'oldpeak': 0.0,  # ST depression (not available)
        'slope': 1,  # Flat slope (not available)
        'ca': 0,  # Number of major vessels (not available)
        'thal': 2,  # Normal thalassemia (not available)
    }
    
    # Create feature vector in correct order
    feature_vector = np.array([[features[col] for col in heart_features]])
    return feature_vector


def extract_diabetes_features(req: RiskAssessmentRequest) -> np.ndarray:
    """
    Extract features for diabetes prediction from patient data.
    
    Diabetes model expects 8 features:
    Pregnancies, Glucose, BloodPressure, SkinThickness, Insulin, BMI,
    DiabetesPedigreeFunction, Age
    
    We approximate from available vitals/demographics.
    """
    v = req.vitals
    d = req.demographics
    
    # Estimate glucose from diabetes status and temperature (stress indicator)
    # High temp can indicate infection which raises glucose
    glucose_estimate = 140 if d.diabetes == "Yes" else 100
    if v.temperature > 38.0:
        glucose_estimate += 20
    
    features = {
        'Pregnancies': 0,  # Not available
        'Glucose': glucose_estimate,
        'BloodPressure': v.diastolic_bp,
        'SkinThickness': 20,  # Default (not available)
        'Insulin': 80,  # Default (not available)
        'BMI': 25,  # Default BMI (not available)
        'DiabetesPedigreeFunction': 0.5,  # Default (not available)
        'Age': d.age,
    }
    
    # Create feature vector in correct order
    feature_vector = np.array([[features[col] for col in diabetes_features]])
    return feature_vector


def extract_stroke_features(req: RiskAssessmentRequest) -> np.ndarray:
    """
    Extract features for stroke prediction from patient data.
    
    Stroke model expects 10 features:
    gender_enc, age, hypertension, heart_disease, ever_married_enc,
    work_type_enc, Residence_type_enc, avg_glucose_level, bmi, smoking_status_enc
    
    We approximate from available vitals/demographics.
    """
    v = req.vitals
    d = req.demographics
    notes = (req.ehr_notes + " " + req.clinical_summary).lower()
    
    # Estimate glucose
    glucose_estimate = 140 if d.diabetes == "Yes" else 100
    if v.temperature > 38.0:
        glucose_estimate += 20
    
    # Check for heart disease indicators in notes
    heart_disease = 1 if any(word in notes for word in ['heart', 'cardiac', 'angina', 'mi', 'infarction']) else 0
    
    features = {
        'gender_enc': 1 if d.gender == "Male" else 0,
        'age': float(d.age),
        'hypertension': 1 if d.hypertension == "Yes" else 0,
        'heart_disease': heart_disease,
        'ever_married_enc': 1 if d.age > 25 else 0,  # Assume married if > 25
        'work_type_enc': 0,  # Private (most common)
        'Residence_type_enc': 1,  # Urban (default)
        'avg_glucose_level': float(glucose_estimate),
        'bmi': 25.0,  # Default BMI
        'smoking_status_enc': 0 if d.smoking_status == "Never" else (1 if d.smoking_status == "Former" else 2),
    }
    
    # Create feature vector in correct order
    feature_vector = np.array([[features[col] for col in stroke_features]])
    return feature_vector


def predict_diseases(req: RiskAssessmentRequest) -> dict:
    """
    Run disease-specific predictions using the trained models.
    
    Returns probabilities for:
    - Heart disease
    - Diabetes
    - Stroke
    
    Note: Multi-disease model requires symptom input (132 features), so we skip it
    for now unless we add a symptom checklist to the UI.
    """
    predictions = {}
    
    try:
        if heart_model is not None:
            X_heart = extract_heart_features(req)
            X_heart_scaled = heart_scaler.transform(X_heart)
            heart_proba = heart_model.predict_proba(X_heart_scaled)[0][1]  # P(disease)
            predictions['heart_disease'] = float(heart_proba)
    except Exception as e:
        print(f"Heart disease prediction failed: {e}")
        predictions['heart_disease'] = None
    
    try:
        if diabetes_model is not None:
            X_diabetes = extract_diabetes_features(req)
            X_diabetes_scaled = diabetes_scaler.transform(X_diabetes)
            diabetes_proba = diabetes_model.predict_proba(X_diabetes_scaled)[0][1]  # P(diabetes)
            predictions['diabetes'] = float(diabetes_proba)
    except Exception as e:
        print(f"Diabetes prediction failed: {e}")
        predictions['diabetes'] = None
    
    try:
        if stroke_model is not None:
            X_stroke = extract_stroke_features(req)
            X_stroke_scaled = stroke_scaler.transform(X_stroke)
            stroke_proba = stroke_model.predict_proba(X_stroke_scaled)[0][1]  # P(stroke)
            predictions['stroke'] = float(stroke_proba)
    except Exception as e:
        print(f"Stroke prediction failed: {e}")
        predictions['stroke'] = None
    
    return predictions


def detect_clinical_conditions(req: RiskAssessmentRequest, proba: np.ndarray) -> dict:
    """
    Detect specific clinical conditions based on vitals, demographics, and model output.
    
    Uses clinical thresholds and pattern matching on the EHR notes.
    These are indicators, not diagnoses - for triage purposes only.
    """
    v = req.vitals
    d = req.demographics
    notes = (req.ehr_notes + " " + req.clinical_summary).lower()
    
    conditions = {}
    
    # 1. Sepsis/Infection Risk
    # Criteria: fever + hypotension + tachycardia + infection keywords
    infection_keywords = any(word in notes for word in ['infection', 'sepsis', 'fever', 'bacteria', 'culture'])
    fever = v.temperature > 38.0
    hypotension = v.systolic_bp < 90
    tachycardia = v.heart_rate > 100
    
    sepsis_score = sum([infection_keywords * 2, fever, hypotension, tachycardia])
    conditions['sepsis_risk'] = 'High' if sepsis_score >= 3 else 'Moderate' if sepsis_score >= 2 else 'Low'
    
    # 2. Respiratory Distress
    # Criteria: low SpO2 + high resp rate keywords + ventilation mentions
    respiratory_keywords = any(word in notes for word in ['ventilation', 'breathing', 'respiratory', 'oxygen', 'dyspnea'])
    low_spo2 = v.spo2 < 92
    conditions['respiratory_concern'] = bool(low_spo2 or ('mechanical ventilation' in notes) or ('severe' in notes and respiratory_keywords))
    
    # 3. Cardiovascular Risk
    # Criteria: abnormal BP + HR + chest pain keywords
    chest_keywords = any(word in notes for word in ['chest pain', 'cardiac', 'heart', 'angina'])
    abnormal_bp = v.systolic_bp > 160 or v.systolic_bp < 90
    abnormal_hr = v.heart_rate > 120 or v.heart_rate < 50
    conditions['cardiovascular_risk'] = 'Elevated' if (abnormal_bp or abnormal_hr or chest_keywords) else 'Normal'
    
    # 4. Organ Dysfunction
    # Criteria: severe keywords + multiple abnormal vitals + high risk prediction
    organ_keywords = any(word in notes for word in ['organ failure', 'organ dysfunction', 'failure', 'dysfunction'])
    multiple_abnormal = sum([
        v.spo2 < 90,
        v.heart_rate > 130,
        v.systolic_bp < 85,
        v.temperature > 38.5
    ])
    
    if organ_keywords or proba[2] > 0.7:  # High probability of mortality
        conditions['organ_function'] = 'Severe Dysfunction'
    elif multiple_abnormal >= 2 or proba[2] > 0.4:
        conditions['organ_function'] = 'Moderate Dysfunction'
    else:
        conditions['organ_function'] = 'Normal'
    
    # 5. Diabetes Complications (if diabetic)
    if d.diabetes == "Yes":
        # Check for signs of diabetic complications
        complications = any(word in notes for word in ['neuropathy', 'retinopathy', 'nephropathy', 'complications'])
        poor_control = v.temperature > 38.0 or notes.count('infection') > 0
        conditions['diabetes_status'] = 'Complications' if complications else 'Poorly Controlled' if poor_control else 'Stable'
    else:
        conditions['diabetes_status'] = 'N/A'
    
    # 6. Overall Severity Flag
    severe_indicators = sum([
        conditions['sepsis_risk'] == 'High',
        conditions['respiratory_concern'],
        conditions['cardiovascular_risk'] == 'Elevated',
        'Severe' in conditions['organ_function'],
        proba[2] > 0.6
    ])
    conditions['requires_icu'] = bool(severe_indicators >= 2)
    
    # Convert all numpy types to native Python types for JSON serialization
    return {k: (bool(v) if isinstance(v, (np.bool_, np.generic)) else v) 
            for k, v in conditions.items()}


@app.post("/api/evaluate-risk", response_model=RiskAssessmentResponse)
async def evaluate_risk(req: RiskAssessmentRequest):
    """
    Evaluate a patient's disease risk level with clinical condition detection.

    Returns:
    - Overall mortality risk score and level (Low/Medium/High) 
    - Specific disease risk predictions (heart disease, diabetes, stroke)
    - Specific clinical condition indicators (sepsis, respiratory, etc.)
    - Top contributing factors from model
    - Actionable recommendations
    
    All processing is local - no external API calls.
    """
    try:
        X = build_feature_vector(req)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Feature extraction failed: {str(e)}")

    # Predict probabilities for mortality risk
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
    
    # NEW: Predict specific diseases
    disease_predictions = predict_diseases(req)
    
    # Detect specific clinical conditions
    clinical_conditions = detect_clinical_conditions(req, proba)

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
        clinical_conditions=clinical_conditions,
        disease_predictions=disease_predictions,  # NEW: Disease risk predictions
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
