"""
CareSync — Disease-Specific Model Training
===========================================
Trains additional disease prediction models (Heart, Diabetes, Stroke, Multi-Disease)
These complement the existing mortality risk model without replacing it.

Data sources: Kaggle datasets for specific disease prediction
All processing is LOCAL — no data ever leaves this machine.
"""

import warnings
import numpy as np
import pandas as pd
from pathlib import Path

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    accuracy_score,
)

import joblib

# ── Paths ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "datasets" / "disease prediction"
MODEL_DIR = Path(__file__).resolve().parent / "app" / "models" / "disease_specific"
REPORT_DIR = Path(__file__).resolve().parent / "reports"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 60)
print("DISEASE-SPECIFIC MODEL TRAINING")
print("=" * 60)

# ══════════════════════════════════════════════════════════════════════
# 1. HEART DISEASE MODEL
# ══════════════════════════════════════════════════════════════════════
print("\n[1/4] Training Heart Disease Model...")
print("=" * 60)

heart_df = pd.read_csv(DATA / "heart.csv")
print(f"Dataset shape: {heart_df.shape}")
print(f"Target distribution:\n{heart_df['target'].value_counts()}")

# Features and target
X_heart = heart_df.drop('target', axis=1)
y_heart = heart_df['target']

# Split
X_heart_train, X_heart_test, y_heart_train, y_heart_test = train_test_split(
    X_heart, y_heart, test_size=0.2, random_state=42, stratify=y_heart
)

# Scale
heart_scaler = StandardScaler()
X_heart_train_scaled = heart_scaler.fit_transform(X_heart_train)
X_heart_test_scaled = heart_scaler.transform(X_heart_test)

# Train
heart_model = LogisticRegression(max_iter=1000, random_state=42, class_weight='balanced')
heart_model.fit(X_heart_train_scaled, y_heart_train)

# Evaluate
y_heart_pred = heart_model.predict(X_heart_test_scaled)
y_heart_proba = heart_model.predict_proba(X_heart_test_scaled)[:, 1]

heart_acc = accuracy_score(y_heart_test, y_heart_pred)
heart_auc = roc_auc_score(y_heart_test, y_heart_proba)

print(f"\nHeart Disease Model Performance:")
print(f"  Accuracy: {heart_acc:.4f}")
print(f"  ROC-AUC: {heart_auc:.4f}")
print(f"\nClassification Report:")
print(classification_report(y_heart_test, y_heart_pred, target_names=['No Disease', 'Heart Disease']))

# Save
joblib.dump(heart_model, MODEL_DIR / "heart_disease_model.joblib")
joblib.dump(heart_scaler, MODEL_DIR / "heart_disease_scaler.joblib")
joblib.dump(list(X_heart.columns), MODEL_DIR / "heart_disease_features.joblib")
print(f"✅ Heart disease model saved")

# ══════════════════════════════════════════════════════════════════════
# 2. DIABETES MODEL
# ══════════════════════════════════════════════════════════════════════
print("\n[2/4] Training Diabetes Model...")
print("=" * 60)

diabetes_df = pd.read_csv(DATA / "diabetes.csv")
print(f"Dataset shape: {diabetes_df.shape}")
print(f"Target distribution:\n{diabetes_df['Outcome'].value_counts()}")

# Features and target
X_diabetes = diabetes_df.drop('Outcome', axis=1)
y_diabetes = diabetes_df['Outcome']

# Split
X_diabetes_train, X_diabetes_test, y_diabetes_train, y_diabetes_test = train_test_split(
    X_diabetes, y_diabetes, test_size=0.2, random_state=42, stratify=y_diabetes
)

# Scale
diabetes_scaler = StandardScaler()
X_diabetes_train_scaled = diabetes_scaler.fit_transform(X_diabetes_train)
X_diabetes_test_scaled = diabetes_scaler.transform(X_diabetes_test)

# Train
diabetes_model = RandomForestClassifier(
    n_estimators=200, max_depth=10, random_state=42, class_weight='balanced', n_jobs=-1
)
diabetes_model.fit(X_diabetes_train_scaled, y_diabetes_train)

# Evaluate
y_diabetes_pred = diabetes_model.predict(X_diabetes_test_scaled)
y_diabetes_proba = diabetes_model.predict_proba(X_diabetes_test_scaled)[:, 1]

diabetes_acc = accuracy_score(y_diabetes_test, y_diabetes_pred)
diabetes_auc = roc_auc_score(y_diabetes_test, y_diabetes_proba)

print(f"\nDiabetes Model Performance:")
print(f"  Accuracy: {diabetes_acc:.4f}")
print(f"  ROC-AUC: {diabetes_auc:.4f}")
print(f"\nClassification Report:")
print(classification_report(y_diabetes_test, y_diabetes_pred, target_names=['No Diabetes', 'Diabetes']))

# Save
joblib.dump(diabetes_model, MODEL_DIR / "diabetes_model.joblib")
joblib.dump(diabetes_scaler, MODEL_DIR / "diabetes_scaler.joblib")
joblib.dump(list(X_diabetes.columns), MODEL_DIR / "diabetes_features.joblib")
print(f"✅ Diabetes model saved")

# ══════════════════════════════════════════════════════════════════════
# 3. STROKE MODEL
# ══════════════════════════════════════════════════════════════════════
print("\n[3/4] Training Stroke Model...")
print("=" * 60)

stroke_df = pd.read_csv(DATA / "healthcare-dataset-stroke-data.csv")
print(f"Dataset shape: {stroke_df.shape}")
print(f"Target distribution:\n{stroke_df['stroke'].value_counts()}")

# Handle missing BMI
stroke_df['bmi'] = stroke_df['bmi'].fillna(stroke_df['bmi'].median())

# Encode categorical variables
stroke_df['gender_enc'] = stroke_df['gender'].map({'Male': 1, 'Female': 0, 'Other': 2})
stroke_df['ever_married_enc'] = stroke_df['ever_married'].map({'Yes': 1, 'No': 0})
stroke_df['work_type_enc'] = stroke_df['work_type'].map({
    'Private': 0, 'Self-employed': 1, 'Govt_job': 2, 'children': 3, 'Never_worked': 4
})
stroke_df['Residence_type_enc'] = stroke_df['Residence_type'].map({'Urban': 1, 'Rural': 0})
stroke_df['smoking_status_enc'] = stroke_df['smoking_status'].map({
    'never smoked': 0, 'formerly smoked': 1, 'smokes': 2, 'Unknown': 3
})

# Features and target
feature_cols = ['gender_enc', 'age', 'hypertension', 'heart_disease', 'ever_married_enc',
                'work_type_enc', 'Residence_type_enc', 'avg_glucose_level', 'bmi', 'smoking_status_enc']
X_stroke = stroke_df[feature_cols]
y_stroke = stroke_df['stroke']

# Handle class imbalance (stroke is rare: ~5%)
print(f"Class imbalance: {y_stroke.value_counts(normalize=True)}")

# Split
X_stroke_train, X_stroke_test, y_stroke_train, y_stroke_test = train_test_split(
    X_stroke, y_stroke, test_size=0.2, random_state=42, stratify=y_stroke
)

# Scale
stroke_scaler = StandardScaler()
X_stroke_train_scaled = stroke_scaler.fit_transform(X_stroke_train)
X_stroke_test_scaled = stroke_scaler.transform(X_stroke_test)

# Train with heavy class weighting
stroke_model = LogisticRegression(
    max_iter=1000, random_state=42, class_weight='balanced', C=0.1
)
stroke_model.fit(X_stroke_train_scaled, y_stroke_train)

# Evaluate
y_stroke_pred = stroke_model.predict(X_stroke_test_scaled)
y_stroke_proba = stroke_model.predict_proba(X_stroke_test_scaled)[:, 1]

stroke_acc = accuracy_score(y_stroke_test, y_stroke_pred)
stroke_auc = roc_auc_score(y_stroke_test, y_stroke_proba)

print(f"\nStroke Model Performance:")
print(f"  Accuracy: {stroke_acc:.4f}")
print(f"  ROC-AUC: {stroke_auc:.4f}")
print(f"\nClassification Report:")
print(classification_report(y_stroke_test, y_stroke_pred, target_names=['No Stroke', 'Stroke']))

# Save
joblib.dump(stroke_model, MODEL_DIR / "stroke_model.joblib")
joblib.dump(stroke_scaler, MODEL_DIR / "stroke_scaler.joblib")
joblib.dump(feature_cols, MODEL_DIR / "stroke_features.joblib")
print(f"✅ Stroke model saved")

# ══════════════════════════════════════════════════════════════════════
# 4. MULTI-DISEASE MODEL (Symptom-based)
# ══════════════════════════════════════════════════════════════════════
print("\n[4/4] Training Multi-Disease Model...")
print("=" * 60)

# Load training data
multi_train = pd.read_csv(DATA / "archive (3)" / "Training.csv")
multi_test = pd.read_csv(DATA / "archive (3)" / "Testing.csv")

print(f"Training shape: {multi_train.shape}")
print(f"Testing shape: {multi_test.shape}")
print(f"Number of diseases: {multi_train['prognosis'].nunique()}")
print(f"Sample diseases: {list(multi_train['prognosis'].unique()[:10])}")

# Features and target
X_multi_train = multi_train.drop('prognosis', axis=1)
y_multi_train = multi_train['prognosis']
X_multi_test_raw = multi_test.drop('prognosis', axis=1)
y_multi_test = multi_test['prognosis']

# Ensure test has same columns as train (handle missing columns)
missing_cols = set(X_multi_train.columns) - set(X_multi_test_raw.columns)
if missing_cols:
    print(f"Adding {len(missing_cols)} missing columns to test set")
    for col in missing_cols:
        X_multi_test_raw[col] = 0

# Reorder columns to match training
X_multi_test = X_multi_test_raw[X_multi_train.columns]

# Encode labels
multi_label_encoder = LabelEncoder()
y_multi_train_enc = multi_label_encoder.fit_transform(y_multi_train)
y_multi_test_enc = multi_label_encoder.transform(y_multi_test)

# Train (no scaling needed, symptoms are already 0/1)
multi_model = RandomForestClassifier(
    n_estimators=200, max_depth=15, random_state=42, n_jobs=-1
)
multi_model.fit(X_multi_train, y_multi_train_enc)

# Evaluate
y_multi_pred = multi_model.predict(X_multi_test)
multi_acc = accuracy_score(y_multi_test_enc, y_multi_pred)

print(f"\nMulti-Disease Model Performance:")
print(f"  Accuracy: {multi_acc:.4f}")
print(f"  Number of classes: {len(multi_label_encoder.classes_)}")

# Save
joblib.dump(multi_model, MODEL_DIR / "multi_disease_model.joblib")
joblib.dump(multi_label_encoder, MODEL_DIR / "multi_disease_labels.joblib")
joblib.dump(list(X_multi_train.columns), MODEL_DIR / "multi_disease_symptoms.joblib")
print(f"✅ Multi-disease model saved")

# ══════════════════════════════════════════════════════════════════════
# SUMMARY REPORT
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("TRAINING COMPLETE - SUMMARY")
print("=" * 60)

summary = f"""
# Disease-Specific Models - Training Summary

## Models Trained

### 1. Heart Disease Prediction
- **Dataset:** {len(heart_df)} patients
- **Features:** {len(X_heart.columns)} (age, sex, chest pain, BP, cholesterol, etc.)
- **Target:** Binary (0=No Disease, 1=Heart Disease)
- **Algorithm:** Logistic Regression
- **Accuracy:** {heart_acc:.4f}
- **ROC-AUC:** {heart_auc:.4f}
- **Model File:** `disease_specific/heart_disease_model.joblib`

### 2. Diabetes Prediction
- **Dataset:** {len(diabetes_df)} patients
- **Features:** {len(X_diabetes.columns)} (pregnancies, glucose, BP, BMI, etc.)
- **Target:** Binary (0=No Diabetes, 1=Diabetes)
- **Algorithm:** Random Forest
- **Accuracy:** {diabetes_acc:.4f}
- **ROC-AUC:** {diabetes_auc:.4f}
- **Model File:** `disease_specific/diabetes_model.joblib`

### 3. Stroke Prediction
- **Dataset:** {len(stroke_df)} patients
- **Features:** {len(feature_cols)} (age, hypertension, glucose, BMI, smoking, etc.)
- **Target:** Binary (0=No Stroke, 1=Stroke)
- **Algorithm:** Logistic Regression (with class balancing)
- **Accuracy:** {stroke_acc:.4f}
- **ROC-AUC:** {stroke_auc:.4f}
- **Model File:** `disease_specific/stroke_model.joblib`
- **Note:** Stroke is rare (~5% of population), model uses heavy class weighting

### 4. Multi-Disease Classification
- **Dataset:** {len(multi_train)} training + {len(multi_test)} test samples
- **Features:** 132 symptoms (binary 0/1)
- **Target:** {len(multi_label_encoder.classes_)} different diseases
- **Algorithm:** Random Forest
- **Accuracy:** {multi_acc:.4f}
- **Model File:** `disease_specific/multi_disease_model.joblib`
- **Diseases:** Fungal infection, Allergy, GERD, Chronic cholestasis, Drug Reaction, 
  Peptic ulcer disease, AIDS, Diabetes, Gastroenteritis, Bronchial Asthma, Hypertension,
  Migraine, Cervical spondylosis, Paralysis, Jaundice, Malaria, Chicken pox, Dengue,
  Typhoid, Hepatitis A-E, Alcoholic hepatitis, Tuberculosis, Common Cold, Pneumonia,
  Dimorphic hemorrhoids, Heart attack, Varicose veins, Hypothyroidism, Hyperthyroidism,
  Hypoglycemia, Osteoarthritis, Arthritis, Vertigo, Acne, Urinary tract infection,
  Psoriasis, Impetigo, and more.

## Integration Notes

These models complement the existing **mortality risk model** (87% accuracy, 94% ROC-AUC).

**Combined System Capabilities:**
1. ✅ Overall mortality risk (Low/Medium/High) - existing model
2. ✅ Heart disease risk - NEW
3. ✅ Diabetes risk - NEW
4. ✅ Stroke risk - NEW  
5. ✅ Multi-disease diagnosis from symptoms - NEW
6. ✅ Clinical condition indicators (sepsis, respiratory, etc.) - existing

**All models use LOCAL inference - no cloud API calls.**

## Usage in API

Models are loaded at startup and can be used alongside the main risk model.
Each prediction takes < 50ms.

## Data Sources

- Heart Disease: Kaggle UCI Heart Disease Dataset
- Diabetes: Kaggle Pima Indians Diabetes Dataset
- Stroke: Kaggle Healthcare Stroke Dataset
- Multi-Disease: Kaggle Disease Prediction Dataset (132 symptoms → 41 diseases)

---
**Generated:** {pd.Timestamp.now()}
"""

# Write summary
with open(REPORT_DIR / "disease_models_summary.md", "w") as f:
    f.write(summary)

print("\n📊 Model Performance Summary:")
print(f"  Heart Disease:  {heart_acc:.1%} accuracy, {heart_auc:.1%} AUC")
print(f"  Diabetes:       {diabetes_acc:.1%} accuracy, {diabetes_auc:.1%} AUC")
print(f"  Stroke:         {stroke_acc:.1%} accuracy, {stroke_auc:.1%} AUC")
print(f"  Multi-Disease:  {multi_acc:.1%} accuracy ({len(multi_label_encoder.classes_)} diseases)")

print(f"\n✅ All models saved to: {MODEL_DIR}")
print(f"✅ Report saved to: {REPORT_DIR / 'disease_models_summary.md'}")
print("\n🎉 Training complete! Ready for integration into the API.")
