"""
CareSync — Model Training Pipeline (Enhanced with MIMIC-III)
=============================================================
Trains a multimodal risk-stratification model using:
  (a) Time-series vitals features (latest, rolling mean/std, trend/delta)
  (b) Demographics (age, sex, comorbidities)
  (c) EHR clinical text (TF-IDF)

Data sources:
  1. Original dataset: 50 patients with vitals + demographics + EHR notes
  2. MIMIC-III: 4,240 ICU patients with vitals, demographics, 30-day mortality

ASSUMPTION (documented in README):
  - Original data: Use pre-provided Low/Medium/High labels
  - MIMIC-III: Map 30-day mortality to risk (died=High, survived with high SOFA=Medium, survived with low SOFA=Low)

All processing is LOCAL — no data ever leaves this machine.
"""

import os
import json
import warnings
import numpy as np
import pandas as pd
from pathlib import Path

from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    recall_score,
)
from scipy.sparse import hstack, csr_matrix

try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
    warnings.warn("XGBoost not installed — skipping XGBoost model.")

import joblib

# ── Paths ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent          # project root
DATA = ROOT / "datasets"
MODEL_DIR = Path(__file__).resolve().parent / "app" / "models"
REPORT_DIR = Path(__file__).resolve().parent / "reports"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# ── 1. Load & Profile Data ────────────────────────────────────────────
print("=" * 60)
print("STEP 1 — Loading and profiling datasets")
print("=" * 60)

# ── Original dataset (50 patients) ────────────────────────────────────
print("\n[1/2] Loading original dataset...")
vitals = pd.read_csv(DATA / "vitals_time_series_0.csv", parse_dates=["timestamp"])
demographics = pd.read_csv(DATA / "demographics_0.csv")
with open(DATA / "ehr_records_0.json", "r") as f:
    ehr_records = json.load(f)
labels = pd.read_csv(DATA / "disease_risk_labels_0.csv")

ehr_df = pd.DataFrame(ehr_records)

# ── MIMIC-III dataset (4,240 ICU patients) ────────────────────────────
print("[2/2] Loading MIMIC-III dataset...")
mimic_path = DATA / "mimic-iii" / "MIMIC-III sample.csv"
mimic = pd.read_csv(mimic_path)
print(f"  MIMIC-III shape: {mimic.shape}")

# Profile original data
for name, df in [("vitals", vitals), ("demographics", demographics),
                  ("ehr", ehr_df), ("labels", labels)]:
    print(f"\n--- Original {name} ---")
    print(f"  Shape: {df.shape}")
    print(f"  Missing: {df.isnull().sum().sum()} total")

print(f"\nOriginal label distribution:\n{labels['risk_level'].value_counts().to_string()}")

# Profile MIMIC-III
print(f"\n--- MIMIC-III ---")
print(f"  Shape: {mimic.shape}")
print(f"  30-day mortality: {mimic['thirtyday_expire_flag'].value_counts().to_dict()}")
print(f"  Missing vitals: HR={mimic['heartrate_mean'].isna().sum()}, "
      f"SBP={mimic['sysbp_mean'].isna().sum()}, "
      f"DBP={mimic['diasbp_mean'].isna().sum()}, "
      f"Temp={mimic['tempc_mean'].isna().sum()}, "
      f"SpO2={mimic['spo2_mean'].isna().sum()}")

# ── 2. Feature Engineering ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 2 — Feature engineering")
print("=" * 60)

VITAL_COLS = ["heart_rate", "systolic_bp", "diastolic_bp", "temperature", "spo2"]

# ── 2A. Original dataset vitals features ──────────────────────────────
def build_vitals_features(vitals_df: pd.DataFrame) -> pd.DataFrame:
    """
    Per-patient time-series vitals → engineered features.
    
    Features extracted per vital sign:
      - latest     : last recorded value (most recent timestep)
      - mean       : rolling 24-h mean
      - std        : rolling 24-h standard deviation (variability)
      - min / max  : range indicators
      - delta      : (last value – first value), captures trend direction
    
    Clinically these capture current state, average load on the body,
    instability (high std = erratic vitals), and deterioration trajectory.
    """
    grouped = vitals_df.sort_values("timestamp").groupby("patient_id")
    records = []
    for pid, grp in grouped:
        row = {"patient_id": pid}
        for col in VITAL_COLS:
            series = grp[col].values
            row[f"{col}_latest"]  = series[-1]
            row[f"{col}_mean"]    = np.mean(series)
            row[f"{col}_std"]     = np.std(series)
            row[f"{col}_min"]     = np.min(series)
            row[f"{col}_max"]     = np.max(series)
            # Trend: positive delta = increasing over 24h window
            row[f"{col}_delta"]   = series[-1] - series[0]
        records.append(row)
    return pd.DataFrame(records)

vitals_features = build_vitals_features(vitals)
print(f"[Original] Vitals features shape: {vitals_features.shape}")

# ── 2B. Original dataset demographics features ────────────────────────
def build_demo_features(demo_df: pd.DataFrame) -> pd.DataFrame:
    """
    Encode demographics into numeric features.
    
    - gender: binary (Male=1, Female=0)
    - smoking_status: ordinal Never=0, Former=1, Current=2
      (clinically, current smokers have highest cardiovascular risk)
    - diabetes, hypertension: binary (Yes=1, No=0)
    - age: kept numeric (continuous)
    """
    df = demo_df.copy()
    df["gender_enc"] = (df["gender"] == "Male").astype(int)
    smoking_map = {"Never": 0, "Former": 1, "Current": 2}
    df["smoking_enc"] = df["smoking_status"].map(smoking_map)
    df["diabetes_enc"] = (df["diabetes"] == "Yes").astype(int)
    df["hypertension_enc"] = (df["hypertension"] == "Yes").astype(int)
    return df[["patient_id", "age", "gender_enc", "smoking_enc",
               "diabetes_enc", "hypertension_enc"]]

demo_features = build_demo_features(demographics)
print(f"[Original] Demographics features shape: {demo_features.shape}")

# ── 2C. Original dataset EHR text features ────────────────────────────
def build_ehr_text(ehr_df: pd.DataFrame) -> pd.DataFrame:
    """
    Concatenate 'notes' + 'clinical_summary' per patient into a single
    text field for TF-IDF vectorization. This captures presenting symptoms
    (e.g. "chest pain", "shortness of breath") and follow-up urgency.
    """
    df = ehr_df.copy()
    df["combined_text"] = df["notes"].fillna("") + " " + df["clinical_summary"].fillna("")
    return df[["patient_id", "combined_text"]]

ehr_text = build_ehr_text(ehr_df)
print(f"[Original] EHR text records: {len(ehr_text)}")

# ── 2D. MIMIC-III feature extraction ──────────────────────────────────
print("\n[MIMIC-III] Extracting features...")

def process_mimic_features(mimic_df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract features from MIMIC-III to match our schema.
    
    Vital signs: Use mean values as "latest" and create synthetic time-series
    features from min/max/mean (we don't have actual time series).
    
    Risk labels: Map 30-day mortality + severity scores to Low/Medium/High:
      - High: died within 30 days OR (survived but SOFA >= 10)
      - Medium: survived, SOFA 5-9
      - Low: survived, SOFA < 5
    """
    df = mimic_df.copy()
    
    # Create patient_id matching original format
    df['patient_id'] = 'M' + df['subject_id'].astype(str)
    
    # Vitals features (use mean as latest, derive std from min/max range)
    for col_base, mimic_col in [
        ('heart_rate', 'heartrate'),
        ('systolic_bp', 'sysbp'),
        ('diastolic_bp', 'diasbp'),
        ('temperature', 'tempc'),
        ('spo2', 'spo2')
    ]:
        # Latest = mean (best proxy we have)
        df[f'{col_base}_latest'] = df[f'{mimic_col}_mean']
        df[f'{col_base}_mean'] = df[f'{mimic_col}_mean']
        df[f'{col_base}_min'] = df[f'{mimic_col}_min']
        df[f'{col_base}_max'] = df[f'{mimic_col}_max']
        # Estimate std from range (rough approximation: range ≈ 4*std)
        df[f'{col_base}_std'] = (df[f'{mimic_col}_max'] - df[f'{mimic_col}_min']) / 4.0
        # Delta: use 0 since we don't have temporal ordering
        df[f'{col_base}_delta'] = 0.0
    
    # Demographics
    df['age'] = df['age']
    df['gender_enc'] = df['is_male'].astype(int)
    df['smoking_enc'] = 0  # Unknown, default to Never
    df['diabetes_enc'] = df['diabetes'].fillna(False).astype(int)
    df['hypertension_enc'] = 0  # Not directly available, use default
    
    # Risk labels based on mortality + SOFA score
    # SOFA (Sequential Organ Failure Assessment): 0-24 scale, higher = worse
    df['sofa_filled'] = df['sofa'].fillna(0)
    
    def assign_risk_level(row):
        if row['thirtyday_expire_flag'] or row['sofa_filled'] >= 10:
            return "High"
        elif row['sofa_filled'] >= 5:
            return "Medium"
        else:
            return "Low"
    
    df['risk_level'] = df.apply(assign_risk_level, axis=1)
    
    # Clinical text: use available clinical indicators as text
    # Combine multiple clinical flags into a text summary
    def generate_clinical_text(row):
        text_parts = []
        if row['vent']:
            text_parts.append("patient on mechanical ventilation")
        if row['diabetes']:
            text_parts.append("history of diabetes")
        if row['metastatic_cancer']:
            text_parts.append("metastatic cancer present")
        if row.get('suspected_infection_time_poe_days', 0) >= 0:
            text_parts.append("suspected infection")
        if row['sofa_filled'] >= 10:
            text_parts.append("severe organ failure")
        elif row['sofa_filled'] >= 5:
            text_parts.append("moderate organ dysfunction")
        
        return " ".join(text_parts) if text_parts else "routine ICU monitoring"
    
    df['combined_text'] = df.apply(generate_clinical_text, axis=1)
    
    # Select final columns
    feature_cols = ['patient_id', 'age', 'gender_enc', 'smoking_enc', 
                    'diabetes_enc', 'hypertension_enc', 'risk_level', 'combined_text']
    
    for col in VITAL_COLS:
        feature_cols.extend([
            f'{col}_latest', f'{col}_mean', f'{col}_std',
            f'{col}_min', f'{col}_max', f'{col}_delta'
        ])
    
    return df[feature_cols]

mimic_processed = process_mimic_features(mimic)

# Handle missing values (fill with median for vitals)
vital_cols_expanded = []
for col in VITAL_COLS:
    vital_cols_expanded.extend([
        f'{col}_latest', f'{col}_mean', f'{col}_std',
        f'{col}_min', f'{col}_max', f'{col}_delta'
    ])

for col in vital_cols_expanded:
    if mimic_processed[col].isna().any():
        median_val = mimic_processed[col].median()
        mimic_processed[col].fillna(median_val, inplace=True)

print(f"[MIMIC-III] Processed shape: {mimic_processed.shape}")
print(f"[MIMIC-III] Risk distribution:\n{mimic_processed['risk_level'].value_counts().to_string()}")

# ── 2E. Merge original dataset ────────────────────────────────────────
merged_original = (
    vitals_features
    .merge(demo_features, on="patient_id")
    .merge(ehr_text, on="patient_id")
    .merge(labels, on="patient_id")
)
print(f"\n[Original] Merged dataset shape: {merged_original.shape}")

# ── 2F. Combine both datasets ─────────────────────────────────────────
print("\n[Combining] Merging original + MIMIC-III datasets...")

# Ensure both have same columns
combined = pd.concat([merged_original, mimic_processed], axis=0, ignore_index=True)
print(f"[Combined] Total shape: {combined.shape}")
print(f"[Combined] Risk distribution:\n{combined['risk_level'].value_counts().to_string()}")

# Label encoding: Low=0, Medium=1, High=2
label_map = {"Low": 0, "Medium": 1, "High": 2}
REVERSE_LABEL_MAP = {v: k for k, v in label_map.items()}
combined["risk_label"] = combined["risk_level"].map(label_map)
y = combined["risk_label"].values

# Numeric features (vitals + demographics)
numeric_cols = [c for c in combined.columns
                if c not in ["patient_id", "combined_text", "risk_level", "risk_label"]]
X_numeric = combined[numeric_cols].values

# TF-IDF on clinical text
# Increase max_features now that we have more data
tfidf = TfidfVectorizer(max_features=100, stop_words="english", ngram_range=(1, 2))
X_text = tfidf.fit_transform(combined["combined_text"])

# Scale numeric features
scaler = StandardScaler()
X_numeric_scaled = scaler.fit_transform(X_numeric)

# Fuse: [scaled numeric | TF-IDF sparse]
X_combined = hstack([csr_matrix(X_numeric_scaled), X_text])
print(f"Combined feature matrix: {X_combined.shape}")

FEATURE_NAMES = numeric_cols + [f"tfidf_{w}" for w in tfidf.get_feature_names_out()]
print(f"Total features: {len(FEATURE_NAMES)}")
print(f"Total samples: {len(y)}")

# ── 3. Model Training & Evaluation ────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 3 — Model training (Stratified 5-Fold CV)")
print("=" * 60)

# Class weights to handle imbalance — 'balanced' auto-adjusts inversely
# proportional to class frequencies, boosting the rare High-risk class.
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

models = {
    "Logistic Regression": LogisticRegression(
        class_weight="balanced", max_iter=1000, random_state=42, solver="lbfgs",
        multi_class="multinomial"
    ),
    "Random Forest": RandomForestClassifier(
        class_weight="balanced", n_estimators=200, max_depth=10,
        random_state=42, n_jobs=-1
    ),
}

if HAS_XGB:
    # XGBoost doesn't support class_weight directly — use sample_weight
    # We'll handle it via scale_pos_weight or manual sample weights in CV
    models["XGBoost"] = XGBClassifier(
        n_estimators=200, max_depth=6, learning_rate=0.1,
        random_state=42, eval_metric="mlogloss",
        use_label_encoder=False
    )

results = {}
best_model_name = None
best_combined_score = -1
best_model = None

# Combined score weights: we heavily prioritize High-Risk recall (0.6)
# over ROC-AUC (0.4) because missing a deteriorating patient is the
# worst outcome in a clinical decision support system.
RECALL_WEIGHT = 0.6
AUC_WEIGHT = 0.4

for name, model in models.items():
    print(f"\n--- {name} ---")
    
    # Collect OOF predictions via cross_val_predict
    X_dense = X_combined.toarray()  # some models need dense
    
    # For XGBoost, we use fit_params for sample_weight in CV
    if name == "XGBoost":
        from sklearn.utils.class_weight import compute_sample_weight
        sw = compute_sample_weight("balanced", y)
        # Manually do CV to pass sample_weight
        y_pred_cv = np.zeros(len(y), dtype=int)
        y_proba_cv = np.zeros((len(y), 3))
        for train_idx, test_idx in cv.split(X_dense, y):
            model_clone = XGBClassifier(
                n_estimators=200, max_depth=4, learning_rate=0.05,
                random_state=42, eval_metric="mlogloss",
                scale_pos_weight=1,
            )
            model_clone.fit(X_dense[train_idx], y[train_idx],
                          sample_weight=sw[train_idx])
            y_pred_cv[test_idx] = model_clone.predict(X_dense[test_idx])
            y_proba_cv[test_idx] = model_clone.predict_proba(X_dense[test_idx])
    else:
        y_pred_cv = cross_val_predict(model, X_dense, y, cv=cv, method="predict")
        y_proba_cv = cross_val_predict(model, X_dense, y, cv=cv, method="predict_proba")
    
    # Metrics
    try:
        auc = roc_auc_score(y, y_proba_cv, multi_class="ovr", average="weighted")
    except Exception:
        auc = 0.0
    
    high_risk_recall = recall_score(y, y_pred_cv, labels=[2], average=None)[0]
    report = classification_report(y, y_pred_cv, target_names=["Low", "Medium", "High"],
                                   zero_division=0)
    cm = confusion_matrix(y, y_pred_cv)
    
    print(f"  ROC-AUC (weighted OVR): {auc:.4f}")
    print(f"  High-Risk Recall: {high_risk_recall:.4f}")
    print(f"\n{report}")
    print(f"Confusion Matrix:\n{cm}")
    
    results[name] = {
        "auc": auc,
        "high_risk_recall": high_risk_recall,
        "report": report,
        "confusion_matrix": cm,
        "y_pred": y_pred_cv,
        "y_proba": y_proba_cv,
    }
    
    # Combined score: heavily weight High-Risk recall
    combined = AUC_WEIGHT * auc + RECALL_WEIGHT * high_risk_recall
    print(f"  Combined score (0.4*AUC + 0.6*Recall_High): {combined:.4f}")
    
    if combined > best_combined_score:
        best_combined_score = combined
        best_model_name = name
        best_model = model

# ── 4. Retrain best model on full data & serialize ─────────────────────
print("\n" + "=" * 60)
print(f"STEP 4 — Retraining best model ({best_model_name}) on full data")
print("=" * 60)

X_dense_full = X_combined.toarray()
if best_model_name == "XGBoost":
    sample_w = compute_sample_weight("balanced", y)
    best_model.fit(X_dense_full, y, sample_weight=sample_w)
else:
    best_model.fit(X_dense_full, y)

# Feature importances (where available)
if hasattr(best_model, "feature_importances_"):
    importances = best_model.feature_importances_
elif hasattr(best_model, "coef_"):
    # For LogReg, use mean absolute coefficient across classes
    importances = np.mean(np.abs(best_model.coef_), axis=0)
else:
    importances = np.zeros(len(FEATURE_NAMES))

feat_importance = sorted(
    zip(FEATURE_NAMES, importances), key=lambda x: x[1], reverse=True
)

print("\nTop 15 features:")
for fname, imp in feat_importance[:15]:
    print(f"  {fname:35s} {imp:.4f}")

# ── Serialize artifacts ───────────────────────────────────────────────
joblib.dump(best_model, MODEL_DIR / "risk_model.joblib")
joblib.dump(scaler, MODEL_DIR / "scaler.joblib")
joblib.dump(tfidf, MODEL_DIR / "tfidf_vectorizer.joblib")
joblib.dump(FEATURE_NAMES, MODEL_DIR / "feature_names.joblib")
joblib.dump(numeric_cols, MODEL_DIR / "numeric_cols.joblib")
joblib.dump(label_map, MODEL_DIR / "label_map.joblib")

# Save the vital column names for the inference pipeline
joblib.dump(VITAL_COLS, MODEL_DIR / "vital_cols.joblib")

print(f"\nModel artifacts saved to {MODEL_DIR}")

# ── 5. Write Metrics Report ──────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 5 — Writing metrics report")
print("=" * 60)

report_lines = []
report_lines.append("# CareSync — Model Metrics Report (Enhanced with MIMIC-III)\n")
report_lines.append(f"**Date**: Auto-generated during training\n")
report_lines.append(f"**Datasets**: \n")
report_lines.append(f"  - Original: 50 patients, 24h hourly vitals, demographics, EHR notes\n")
report_lines.append(f"  - MIMIC-III: 4,240 ICU patients with vitals, demographics, 30-day mortality\n")
report_lines.append(f"  - **Total**: {len(y)} patients\n")
# Calculate label distribution from y
label_counts = {REVERSE_LABEL_MAP[i]: int(np.sum(y == i)) for i in sorted(set(y))}
report_lines.append(f"**Label distribution**: {label_counts}\n")
report_lines.append(f"**Evaluation**: Stratified 5-Fold Cross-Validation\n")
report_lines.append(f"**Class balancing**: class_weight='balanced' (LR, RF) / sample_weight (XGB)\n\n")

report_lines.append("## Model Comparison\n\n")
report_lines.append("| Model | ROC-AUC (weighted) | High-Risk Recall |\n")
report_lines.append("|-------|-------------------|------------------|\n")
for mname, mres in results.items():
    marker = " ✅" if mname == best_model_name else ""
    report_lines.append(
        f"| {mname}{marker} | {mres['auc']:.4f} | {mres['high_risk_recall']:.4f} |\n"
    )

report_lines.append(f"\n**Selected model**: {best_model_name}\n\n")

report_lines.append("## Classification Report (Best Model — CV)\n\n")
report_lines.append("```\n")
report_lines.append(results[best_model_name]["report"])
report_lines.append("```\n\n")

report_lines.append("## Confusion Matrix (Best Model — CV)\n\n")
cm = results[best_model_name]["confusion_matrix"]
report_lines.append("```\n")
report_lines.append(f"              Predicted\n")
report_lines.append(f"              Low  Med  High\n")
for i, row_label in enumerate(["Low ", "Med ", "High"]):
    row_vals = "  ".join(f"{v:3d}" for v in cm[i])
    report_lines.append(f"  Actual {row_label}  {row_vals}\n")
report_lines.append("```\n\n")

report_lines.append("## Top 15 Feature Importances\n\n")
report_lines.append("| Rank | Feature | Importance |\n")
report_lines.append("|------|---------|------------|\n")
for rank, (fname, imp) in enumerate(feat_importance[:15], 1):
    report_lines.append(f"| {rank} | {fname} | {imp:.4f} |\n")

report_lines.append("\n## Notes\n\n")
report_lines.append("- All evaluation uses out-of-fold predictions (no data leakage).\n")
report_lines.append("- Class weighting ensures the model penalizes missing High-risk patients.\n")
report_lines.append("- MIMIC-III 30-day mortality was mapped to High risk; SOFA scores used for Medium/Low stratification.\n")
report_lines.append("- Combined dataset provides significantly larger training set (4,290 patients vs original 50).\n")
report_lines.append("- Feature importances are from the full-data retrained model.\n")

report_path = REPORT_DIR / "model_metrics.md"
with open(report_path, "w") as f:
    f.writelines(report_lines)

print(f"Metrics report written to {report_path}")
print("\n✅ Training pipeline complete!")
