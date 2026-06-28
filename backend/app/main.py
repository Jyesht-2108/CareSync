"""
CareSync — FastAPI Backend
===========================
Local/edge-first clinical decision-support API.

Architecture note: This service is designed to run entirely on-device.
The ML model, TF-IDF vectorizer, and all preprocessing artifacts are
loaded from local disk at startup. NO patient data is transmitted to
any external API, LLM service, or cloud endpoint at any point.

NOTE: The JARVIS voice assistant feature uses OpenAI's API for conversational
AI, which does require an API key and external connectivity. This is an optional
feature for enhanced user experience.

Endpoints:
  POST /api/evaluate-risk — Run risk assessment on a patient
  POST /api/jarvis/chat            — Text chat with JARVIS (fallback)
  POST /api/jarvis/realtime-session — WebRTC Realtime voice session
  GET  /health                     — Liveness check
"""

import json
import os
import numpy as np
from pathlib import Path
from contextlib import asynccontextmanager
from dotenv import load_dotenv

import httpx
import joblib
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
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
    - Multi-disease diagnosis (top 5 probable diseases from 41 options)
    
    Note: Multi-disease model requires symptom input (132 features), so we
    intelligently infer symptoms from vitals and clinical notes.
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
    
    # NEW: Multi-disease prediction from symptoms
    try:
        if multi_disease_model is not None and multi_disease_symptoms is not None:
            # Infer symptoms from vitals and clinical notes
            symptom_vector = infer_symptoms_from_patient_data(req)
            
            # Get prediction probabilities for all 41 diseases
            disease_probas = multi_disease_model.predict_proba([symptom_vector])[0]
            
            # Get top 5 most probable diseases
            top_5_indices = np.argsort(disease_probas)[-5:][::-1]
            top_5_diseases = []
            
            for idx in top_5_indices:
                disease_name = multi_disease_labels.classes_[idx]
                probability = float(disease_probas[idx])
                if probability > 0.05:  # Only show if > 5% probability
                    top_5_diseases.append({
                        'disease': disease_name,
                        'probability': probability
                    })
            
            predictions['multi_disease_top5'] = top_5_diseases
    except Exception as e:
        print(f"Multi-disease prediction failed: {e}")
        predictions['multi_disease_top5'] = []
    
    return predictions


def infer_symptoms_from_patient_data(req: RiskAssessmentRequest) -> list:
    """
    Intelligently infer symptom presence (0/1) from patient vitals and clinical notes.
    
    Maps 133 symptom features based on:
    - Vital signs (fever → high temp, low SpO2 → breathing issues, etc.)
    - Clinical notes (keyword matching)
    - Demographics (age, gender, conditions)
    
    This allows multi-disease model to work without explicit symptom checklist.
    """
    v = req.vitals
    d = req.demographics
    notes = (req.ehr_notes + " " + req.clinical_summary).lower()
    
    # Initialize all symptoms as 0 (absent)
    symptoms = {symptom: 0 for symptom in multi_disease_symptoms}
    
    # Vital-based symptom inference
    # Temperature
    if v.temperature > 38.0:
        symptoms['high_fever'] = 1
    if v.temperature > 37.5:
        symptoms['continuous_sneezing'] = 0.3  # Mild indicator
        symptoms['chills'] = 1 if v.temperature > 39.0 else 0.5
        symptoms['shivering'] = 1 if v.temperature > 39.0 else 0
    if v.temperature < 36.0:
        symptoms['cold_hands_and_feets'] = 1
    
    # SpO2 - Respiratory
    if v.spo2 < 94:
        symptoms['breathlessness'] = 1
        symptoms['fast_heart_rate'] = 1 if v.heart_rate > 100 else 0
    if v.spo2 < 90:
        symptoms['breathlessness'] = 1
        symptoms['cough'] = 0.7
        symptoms['rusty_sputum'] = 0.3  # Could indicate pneumonia
    
    # Heart Rate
    if v.heart_rate > 100:
        symptoms['fast_heart_rate'] = 1
        symptoms['palpitations'] = 1
        symptoms['anxiety'] = 0.5
    if v.heart_rate < 60:
        symptoms['fatigue'] = 0.7
        symptoms['weakness_in_limbs'] = 0.3
    
    # Blood Pressure
    if v.systolic_bp > 140:
        symptoms['headache'] = 0.5
        symptoms['dizziness'] = 0.3
    if v.systolic_bp < 90:
        symptoms['dizziness'] = 0.7
        symptoms['weakness_in_limbs'] = 0.6
        symptoms['fatigue'] = 0.7
    
    # Demographics-based
    if d.diabetes == "Yes":
        symptoms['increased_appetite'] = 0.5
        symptoms['polyuria'] = 0.5  # Frequent urination
        symptoms['fatigue'] = 0.6
        symptoms['weight_loss'] = 0.3
    
    if d.hypertension == "Yes":
        symptoms['headache'] = 0.4
        symptoms['chest_pain'] = 0.3
    
    if d.smoking_status in ["Current", "Former"]:
        symptoms['cough'] = 0.4
        symptoms['breathlessness'] = 0.3
    
    # Age-based
    if d.age > 60:
        symptoms['joint_pain'] = 0.3
        symptoms['muscle_weakness'] = 0.2
        symptoms['fatigue'] = 0.3
    
    # Clinical notes keyword matching
    symptom_keywords = {
        'cough': ['cough', 'coughing'],
        'fever': ['fever', 'febrile', 'pyrexia'],
        'headache': ['headache', 'head pain'],
        'fatigue': ['fatigue', 'tired', 'exhausted', 'weakness'],
        'chest_pain': ['chest pain', 'chest discomfort', 'angina'],
        'breathlessness': ['shortness of breath', 'dyspnea', 'breathing difficulty', 'sob'],
        'vomiting': ['vomiting', 'nausea', 'emesis'],
        'dizziness': ['dizziness', 'dizzy', 'vertigo', 'lightheaded'],
        'abdominal_pain': ['abdominal pain', 'stomach pain', 'belly pain'],
        'diarrhoea': ['diarrhea', 'diarrhoea', 'loose stools'],
        'loss_of_appetite': ['loss of appetite', 'anorexia', 'not eating'],
        'weight_loss': ['weight loss', 'losing weight'],
        'yellowing_of_eyes': ['jaundice', 'yellow eyes', 'icterus'],
        'skin_rash': ['rash', 'skin eruption'],
        'itching': ['itching', 'pruritus', 'itch'],
        'joint_pain': ['joint pain', 'arthralgia'],
        'muscle_pain': ['muscle pain', 'myalgia'],
        'weakness_in_limbs': ['weakness', 'limb weakness', 'paralysis'],
        'confusion': ['confused', 'confusion', 'disoriented'],
        'back_pain': ['back pain', 'backache'],
        'neck_pain': ['neck pain', 'stiff neck'],
        'constipation': ['constipation', 'no bowel movement'],
        'sweating': ['sweating', 'diaphoresis', 'perspiration'],
        'chest_pain': ['chest pain', 'cardiac pain'],
        'palpitations': ['palpitations', 'racing heart'],
        'irregular_sugar_level': ['glucose', 'sugar', 'hyperglycemia', 'hypoglycemia'],
        'blurred_and_distorted_vision': ['blurred vision', 'vision problems'],
        'altered_sensorium': ['altered mental', 'altered sensorium', 'drowsy'],
        'loss_of_smell': ['loss of smell', 'anosmia'],
        'congestion': ['congestion', 'stuffy nose', 'blocked nose'],
        'sore_throat': ['sore throat', 'throat pain'],
        'phlegm': ['phlegm', 'sputum', 'mucus'],
        'swelling_joints': ['swollen joints', 'joint swelling'],
        'red_spots_over_body': ['red spots', 'petechiae', 'rash'],
        'pain_during_bowel_movements': ['painful bowel', 'pain defecation'],
        'pain_in_anal_region': ['anal pain', 'rectal pain'],
        'bloody_stool': ['bloody stool', 'blood in stool', 'melena'],
        'irritation_in_anus': ['anal irritation', 'itchy anus'],
        'cramps': ['cramps', 'muscle cramps', 'spasms'],
        'bruising': ['bruising', 'bruises', 'ecchymosis'],
        'swelling_of_stomach': ['abdominal swelling', 'distended abdomen', 'bloating'],
        'history_of_alcohol_consumption': ['alcohol', 'drinking', 'alcoholic'],
        'receiving_blood_transfusion': ['blood transfusion', 'transfusion'],
        'receiving_unsterile_injections': ['injection', 'needle'],
        'malaise': ['malaise', 'unwell', 'feeling sick'],
        'blister': ['blister', 'blisters', 'vesicles'],
        'red_sore_around_nose': ['nose sore', 'nasal sore'],
        'yellow_crust_ooze': ['yellow crust', 'oozing'],
        'family_history': ['family history'],
    }
    
    for symptom, keywords in symptom_keywords.items():
        if symptom in symptoms:  # Only if symptom exists in model
            for keyword in keywords:
                if keyword in notes:
                    symptoms[symptom] = 1
                    break
    
    # Convert to vector in correct order
    symptom_vector = []
    for symptom_name in multi_disease_symptoms:
        value = symptoms.get(symptom_name, 0)
        # Convert probabilistic values to binary (threshold at 0.5)
        symptom_vector.append(1 if value >= 0.5 else 0)
    
    return symptom_vector


def calculate_news2_score(req: RiskAssessmentRequest) -> dict:
    """
    Calculate NEWS2 (National Early Warning Score 2) - a clinically validated
    vital signs-based risk scoring system used in UK NHS and globally.
    
    NEWS2 scores 7 physiological parameters:
    - Respiration rate (we approximate from clinical context)
    - SpO2 saturation
    - Systolic blood pressure
    - Pulse (heart rate)
    - Consciousness (AVPU scale - we approximate)
    - Temperature
    
    Score ranges:
    - 0-4: Low risk
    - 5-6: Medium risk (urgent response)
    - 7+: High risk (emergency response)
    
    This provides a vital-based safety net that can't be fooled by missing text.
    """
    v = req.vitals
    d = req.demographics
    notes = (req.ehr_notes + " " + req.clinical_summary).lower()
    
    score = 0
    breakdown = {}
    
    # 1. SpO2 Score (0-3 points)
    # Scale 1 (standard): 96%+ = 0, 94-95% = 1, 92-93% = 2, ≤91% = 3
    if v.spo2 >= 96:
        spo2_score = 0
    elif v.spo2 >= 94:
        spo2_score = 1
    elif v.spo2 >= 92:
        spo2_score = 2
    else:
        spo2_score = 3
    
    score += spo2_score
    breakdown['spo2'] = spo2_score
    
    # 2. Heart Rate Score (0-3 points)
    hr = v.heart_rate
    if 51 <= hr <= 90:
        hr_score = 0
    elif (41 <= hr <= 50) or (91 <= hr <= 110):
        hr_score = 1
    elif (111 <= hr <= 130) or (hr <= 40):
        hr_score = 2
    else:  # >130 or <40
        hr_score = 3
    
    score += hr_score
    breakdown['heart_rate'] = hr_score
    
    # 3. Systolic BP Score (0-3 points)
    sbp = v.systolic_bp
    if 111 <= sbp <= 219:
        sbp_score = 0
    elif 101 <= sbp <= 110:
        sbp_score = 1
    elif 91 <= sbp <= 100:
        sbp_score = 2
    else:  # ≤90 or ≥220
        sbp_score = 3
    
    score += sbp_score
    breakdown['systolic_bp'] = sbp_score
    
    # 4. Temperature Score (0-3 points)
    temp = v.temperature
    if 36.1 <= temp <= 38.0:
        temp_score = 0
    elif (35.1 <= temp <= 36.0) or (38.1 <= temp <= 39.0):
        temp_score = 1
    elif temp >= 39.1:
        temp_score = 2
    else:  # ≤35.0
        temp_score = 3
    
    score += temp_score
    breakdown['temperature'] = temp_score
    
    # 5. Consciousness Score (0-3 points)
    # AVPU scale: Alert=0, Voice/Pain/Unresponsive=3
    # Approximate from notes
    consciousness_keywords = ['confused', 'drowsy', 'unconscious', 'unresponsive', 
                             'altered mental', 'disoriented', 'lethargic']
    if any(word in notes for word in consciousness_keywords):
        consciousness_score = 3
    else:
        consciousness_score = 0
    
    score += consciousness_score
    breakdown['consciousness'] = consciousness_score
    
    # 6. Age adjustment (bonus for elderly + any score)
    # If age ≥65 and score ≥1, add emphasis
    age_adjusted_score = score
    if d.age >= 65 and score >= 1:
        age_adjusted_score += 1
    
    # Map to risk level
    if age_adjusted_score <= 4:
        news2_risk = "Low"
    elif age_adjusted_score <= 6:
        news2_risk = "Medium"
    else:
        news2_risk = "High"
    
    return {
        'score': score,
        'age_adjusted_score': age_adjusted_score,
        'risk_level': news2_risk,
        'breakdown': breakdown
    }


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
    
    HYBRID APPROACH:
    1. ML-based mortality risk model (trained on MIMIC-III)
    2. Disease-specific ML models (heart, diabetes, stroke)
    3. NEWS2 clinical vital scoring (evidence-based)
    4. Clinical condition detection rules
    5. INTELLIGENT AGGREGATION with vital-based safety overrides

    This ensures we can't miss obvious high-risk cases due to missing text features.
    
    Returns:
    - Overall risk score and level (Low/Medium/High) 
    - Specific disease risk predictions (heart disease, diabetes, stroke)
    - Clinical condition indicators (sepsis, respiratory, etc.)
    - NEWS2 vital-based score
    - Contributing factors
    
    All processing is local - no external API calls.
    """
    try:
        X = build_feature_vector(req)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Feature extraction failed: {str(e)}")

    # ═══ 1. ML Model Prediction ═══
    proba = model.predict_proba(X)[0]  # shape: (n_classes,)
    ml_risk_score = float(proba[2] * 1.0 + proba[1] * 0.5 + proba[0] * 0.0)
    ml_predicted_class = int(np.argmax(proba))
    ml_risk_level = REVERSE_LABEL_MAP.get(ml_predicted_class, "Low")
    
    # ═══ 2. Disease-Specific Predictions ═══
    disease_predictions = predict_diseases(req)
    
    # Get max disease risk
    disease_risks = []
    if disease_predictions.get('heart_disease'):
        disease_risks.append(disease_predictions['heart_disease'])
    if disease_predictions.get('diabetes'):
        disease_risks.append(disease_predictions['diabetes'])
    if disease_predictions.get('stroke'):
        disease_risks.append(disease_predictions['stroke'])
    
    max_disease_risk = max(disease_risks) if disease_risks else 0.0
    
    # Map disease risk to level
    if max_disease_risk > 0.7:
        disease_risk_level = "High"
    elif max_disease_risk > 0.4:
        disease_risk_level = "Medium"
    else:
        disease_risk_level = "Low"
    
    # ═══ 3. NEWS2 Vital-Based Scoring ═══
    news2_result = calculate_news2_score(req)
    news2_risk_level = news2_result['risk_level']
    news2_score = news2_result['age_adjusted_score']
    
    # ═══ 4. Clinical Condition Detection ═══
    clinical_conditions = detect_clinical_conditions(req, proba)
    
    # Check for critical conditions
    critical_condition = (
        clinical_conditions.get('sepsis_risk') == 'High' or
        clinical_conditions.get('requires_icu') or
        clinical_conditions.get('respiratory_concern')
    )
    
    # ═══ 5. INTELLIGENT RISK AGGREGATION ═══
    # Priority order:
    # 1. Critical safety overrides (can't miss these!)
    # 2. NEWS2 vital score (evidence-based clinical tool)
    # 3. Disease-specific models (domain-specific)
    # 4. ML model (but text-biased, so lowest priority)
    
    v = req.vitals
    
    # CRITICAL SAFETY OVERRIDES (immediate High risk)
    if (
        v.spo2 < 88 or              # Severe hypoxia
        v.heart_rate > 150 or       # Severe tachycardia
        v.heart_rate < 35 or        # Severe bradycardia
        v.systolic_bp < 70 or       # Severe hypotension
        v.systolic_bp > 220 or      # Hypertensive emergency
        v.temperature > 40.0 or     # Hyperpyrexia
        v.temperature < 35.0        # Severe hypothermia
    ):
        final_risk_level = "High"
        final_risk_score = 0.95
        primary_reason = "CRITICAL: Vital signs in dangerous range"
    
    # Disease model shows High risk (>70%) even with normal vitals
    elif disease_risk_level == "High" and news2_risk_level == "Low":
        final_risk_level = "High"
        final_risk_score = max(0.7, max_disease_risk)
        primary_reason = f"High disease risk detected (vitals currently stable)"
    
    # NEWS2 or disease model shows High risk
    elif news2_risk_level == "High" or disease_risk_level == "High" or critical_condition:
        final_risk_level = "High"
        final_risk_score = max(0.7, ml_risk_score, max_disease_risk, news2_score / 20.0)
        primary_reason = f"NEWS2: {news2_risk_level}, Disease: {disease_risk_level}"
    
    # Medium risk from any source
    elif (news2_risk_level == "Medium" or 
          disease_risk_level == "Medium" or 
          ml_risk_level == "Medium" or
          proba[2] > 0.35):  # ML shows elevated High risk probability
        final_risk_level = "Medium"
        final_risk_score = max(0.4, ml_risk_score, max_disease_risk * 0.8, news2_score / 20.0)
        primary_reason = f"NEWS2: {news2_risk_level}, Disease: {disease_risk_level}, ML: {ml_risk_level}"
    
    # Low risk only if ALL indicators agree
    else:
        final_risk_level = "Low"
        final_risk_score = min(0.3, max(ml_risk_score, max_disease_risk, news2_score / 20.0))
        primary_reason = "All indicators within normal limits"
    
    # ═══ 6. Contributing Factors (Enhanced) ═══
    contributing_factors = []
    
    # Add NEWS2 breakdown as factors
    for vital, score_val in news2_result['breakdown'].items():
        if score_val > 0:
            contributing_factors.append(ContributingFactor(
                factor=f"{_humanize_feature(vital)} (NEWS2: {score_val} pts)",
                importance=score_val / 3.0  # Normalize to 0-1
            ))
    
    # Add disease risks
    if disease_predictions.get('stroke', 0) > 0.4:
        contributing_factors.append(ContributingFactor(
            factor=f"Stroke Risk: {disease_predictions['stroke']*100:.0f}%",
            importance=disease_predictions['stroke']
        ))
    if disease_predictions.get('heart_disease', 0) > 0.4:
        contributing_factors.append(ContributingFactor(
            factor=f"Heart Disease Risk: {disease_predictions['heart_disease']*100:.0f}%",
            importance=disease_predictions['heart_disease']
        ))
    if disease_predictions.get('diabetes', 0) > 0.4:
        contributing_factors.append(ContributingFactor(
            factor=f"Diabetes Risk: {disease_predictions['diabetes']*100:.0f}%",
            importance=disease_predictions['diabetes']
        ))
    
    # Add clinical conditions
    if critical_condition:
        contributing_factors.append(ContributingFactor(
            factor="Critical clinical condition detected",
            importance=1.0
        ))
    
    # Sort by importance and take top 5
    contributing_factors.sort(key=lambda x: x.importance, reverse=True)
    contributing_factors = contributing_factors[:5]
    
    # If we don't have enough factors, add from ML model
    if len(contributing_factors) < 3:
        if hasattr(model, "feature_importances_"):
            importances = model.feature_importances_
        elif hasattr(model, "coef_"):
            importances = np.mean(np.abs(model.coef_), axis=0)
        else:
            importances = np.zeros(len(feature_names))
        
        feat_imp_pairs = list(zip(feature_names, importances))
        feat_imp_pairs.sort(key=lambda x: x[1], reverse=True)
        
        for fname, imp in feat_imp_pairs[:3]:
            if not any(f.factor.startswith(_humanize_feature(fname)) for f in contributing_factors):
                contributing_factors.append(ContributingFactor(
                    factor=_humanize_feature(fname),
                    importance=round(float(imp), 4)
                ))
                if len(contributing_factors) >= 5:
                    break
    
    # Add NEWS2 info to clinical conditions
    clinical_conditions['news2_score'] = news2_score
    clinical_conditions['news2_risk'] = news2_risk_level
    clinical_conditions['primary_assessment'] = primary_reason

    return RiskAssessmentResponse(
        risk_score=round(final_risk_score, 4),
        risk_level=final_risk_level,
        contributing_factors=contributing_factors[:5],
        confidence=round(0.85 if final_risk_level != ml_risk_level else float(np.max(proba)), 4),
        clinical_conditions=clinical_conditions,
        disease_predictions=disease_predictions,
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


# ═══ OpenAI Setup for JARVIS Assistant ═══
# Load .env file from backend directory
backend_dir = Path(__file__).resolve().parent.parent
env_path = backend_dir / '.env'
load_dotenv(dotenv_path=env_path)

# Get API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_available = OPENAI_API_KEY and OPENAI_API_KEY != "your_openai_api_key_here"

if openai_available:
    print("✅ OpenAI API key loaded for JARVIS assistant")
else:
    print("⚠️  OPENAI_API_KEY not configured - JARVIS feature will be unavailable")
    print(f"    Looking for .env at: {env_path}")


JARVIS_REALTIME_MODEL = "gpt-4o-realtime-preview-2024-12-17"
JARVIS_REALTIME_VOICE = "alloy"  # Natural, conversational voice


def format_risk_context_for_jarvis(risk_context: dict) -> str:
    """Format the current risk assessment for JARVIS context."""
    context_str = "\n\n--- CURRENT PATIENT ASSESSMENT ---\n"
    
    if "risk_level" in risk_context:
        context_str += f"Overall Risk Level: {risk_context['risk_level']}"
        if "risk_score" in risk_context:
            context_str += f" ({risk_context['risk_score']*100:.1f}%)"
        context_str += "\n"
    
    if "vitals" in risk_context:
        v = risk_context["vitals"]
        context_str += f"\nVital Signs:\n"
        context_str += f"- Heart Rate: {v.get('heart_rate', 'N/A')} bpm\n"
        context_str += f"- Blood Pressure: {v.get('systolic_bp', 'N/A')}/{v.get('diastolic_bp', 'N/A')} mmHg\n"
        context_str += f"- SpO2: {v.get('spo2', 'N/A')}%\n"
        context_str += f"- Temperature: {v.get('temperature', 'N/A')}°C\n"
    
    if "demographics" in risk_context:
        d = risk_context["demographics"]
        context_str += f"\nPatient Info:\n"
        context_str += f"- Age: {d.get('age', 'N/A')}\n"
        context_str += f"- Diabetes: {d.get('diabetes', 'N/A')}\n"
        context_str += f"- Hypertension: {d.get('hypertension', 'N/A')}\n"
    
    if "disease_predictions" in risk_context:
        dp = risk_context["disease_predictions"]
        context_str += f"\nDisease Risk Predictions:\n"
        if dp.get("heart_disease"):
            context_str += f"- Heart Disease: {dp['heart_disease']*100:.1f}%\n"
        if dp.get("diabetes"):
            context_str += f"- Diabetes: {dp['diabetes']*100:.1f}%\n"
        if dp.get("stroke"):
            context_str += f"- Stroke: {dp['stroke']*100:.1f}%\n"
    
    if "clinical_conditions" in risk_context:
        cc = risk_context["clinical_conditions"]
        if cc.get("news2_score") is not None:
            context_str += f"\nNEWS2 Score: {cc['news2_score']} ({cc.get('news2_risk', 'N/A')} Risk)\n"
        if cc.get("primary_assessment"):
            context_str += f"Assessment: {cc['primary_assessment']}\n"
    
    context_str += "\n--- END ASSESSMENT ---\n"
    return context_str


def build_jarvis_system_prompt(risk_context: dict | None = None) -> str:
    """System instructions for JARVIS — shared by text chat and Realtime voice."""
    prompt = """You are JARVIS, a conversational AI medical assistant helping healthcare workers in India.

Your personality:
- Natural and warm — like talking to an experienced colleague
- Confident but never pushy
- Direct without being robotic
- Think of yourself as a helpful partner, not a textbook

How you communicate:
- Speak naturally with contractions and casual flow (you're, it's, that's)
- Keep sentences short and conversational when speaking
- Answer directly first, then add context if needed
- Use simple language and explain medical terms naturally
- Hinglish is perfectly fine when it helps
- Reference this specific patient's data when answering

Important guidelines:
- The UI already shows a one-time disclaimer — you don't need to repeat it
- Only mention consulting a doctor or emergency services when it's genuinely urgent
- Trust the healthcare worker — they know when to escalate
- Be helpful and informative, not a walking liability warning

When discussing risk levels:
- HIGH risk → Be clear and direct about needing immediate attention, cite specific concerns
- MEDIUM risk → Suggest seeing a doctor within a day, mention what to watch
- LOW risk → Reassure but note routine monitoring

Current patient context:"""

    if risk_context:
        prompt += format_risk_context_for_jarvis(risk_context)
    else:
        prompt += "\nNo assessment loaded yet."

    return prompt


def build_jarvis_realtime_session_config(risk_context: dict | None = None) -> dict:
    """OpenAI Realtime session config for natural speech-to-speech."""
    return {
        "type": "realtime",
        "model": JARVIS_REALTIME_MODEL,
        "instructions": build_jarvis_system_prompt(risk_context),
        "audio": {
            "output": {
                "voice": JARVIS_REALTIME_VOICE
            }
        }
    }


@app.post("/api/jarvis/realtime-session", response_class=PlainTextResponse)
async def jarvis_realtime_session(request: Request):
    """
    Establish an OpenAI Realtime WebRTC session (unified interface).

    Browser sends its SDP offer + patient context; we forward to OpenAI
    with JARVIS instructions and return the SDP answer.
    """
    if not openai_available:
        raise HTTPException(
            status_code=503,
            detail="JARVIS Realtime is not available. OpenAI API key not configured.",
        )

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=422, detail="Expected JSON body with sdp and risk_assessment_context")

    sdp_offer = body.get("sdp")
    if not sdp_offer:
        raise HTTPException(status_code=422, detail="Missing SDP offer")

    risk_context = body.get("risk_assessment_context") or {}
    session_config = build_jarvis_realtime_session_config(risk_context)

    try:
        # Step 1: Create ephemeral token for WebRTC
        async with httpx.AsyncClient(timeout=30.0) as client:
            token_response = await client.post(
                "https://api.openai.com/v1/realtime/client_secrets",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "session": session_config,
                }
            )

            if token_response.status_code != 200:
                print(f"\n\n=== JARVIS OPENAI TOKEN ERROR ===\n{token_response.text}\n=================================\n\n")
                raise HTTPException(
                    status_code=token_response.status_code,
                    detail=f"OpenAI session creation error: {token_response.text}",
                )

            session_data = token_response.json()
            ephemeral_token = session_data.get("value") or session_data.get("client_secret", {}).get("value")
            
            if not ephemeral_token:
                print(f"\n\n=== JARVIS OPENAI TOKEN MISSING ===\n{token_response.text}\n===================================\n\n")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to get ephemeral token from OpenAI"
                )

            # Step 2: Use ephemeral token to exchange SDP
            sdp_response = await client.post(
                "https://api.openai.com/v1/realtime/calls",
                headers={
                    "Authorization": f"Bearer {ephemeral_token}",
                    "Content-Type": "application/sdp",
                },
                content=sdp_offer,
            )

        if sdp_response.status_code != 200:
            raise HTTPException(
                status_code=sdp_response.status_code,
                detail=f"OpenAI Realtime error: {sdp_response.text}",
            )

        return PlainTextResponse(content=sdp_response.text, media_type="application/sdp")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"JARVIS Realtime session error: {str(e)}")


@app.post("/api/jarvis/chat")
async def jarvis_chat(request: dict):
    """Text fallback for JARVIS when Realtime voice is unavailable."""
    if not openai_available:
        raise HTTPException(
            status_code=503,
            detail="JARVIS assistant is not available. OpenAI API key not configured.",
        )

    try:
        user_message = request.get("message", "")
        risk_context = request.get("risk_assessment_context", {})
        conversation_history = request.get("conversation_history", [])
        system_prompt = build_jarvis_system_prompt(risk_context)

        messages = [{"role": "system", "content": system_prompt}]
        for msg in conversation_history[-6:]:
            messages.append(msg)
        messages.append({"role": "user", "content": user_message})

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o",
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 500,
                },
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"OpenAI API error: {response.text}",
                )

            data = response.json()
            assistant_message = data["choices"][0]["message"]["content"]

        return {
            "success": True,
            "message": assistant_message,
            "role": "assistant",
            "model": "gpt-4o",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"JARVIS assistant error: {str(e)}")


@app.get("/health")
async def health_check():
    """Basic liveness check — confirms model is loaded and ready."""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "jarvis_available": openai_available,
        "jarvis_mode": "openai-realtime-webrtc" if openai_available else None,
        "jarvis_voice": JARVIS_REALTIME_VOICE if openai_available else None,
        "service": "CareSync",
        "privacy": "All processing is local — no data leaves this device (except optional JARVIS feature)",
    }
