
# Disease-Specific Models - Training Summary

## Models Trained

### 1. Heart Disease Prediction
- **Dataset:** 1025 patients
- **Features:** 13 (age, sex, chest pain, BP, cholesterol, etc.)
- **Target:** Binary (0=No Disease, 1=Heart Disease)
- **Algorithm:** Logistic Regression
- **Accuracy:** 0.8098
- **ROC-AUC:** 0.9300
- **Model File:** `disease_specific/heart_disease_model.joblib`

### 2. Diabetes Prediction
- **Dataset:** 768 patients
- **Features:** 8 (pregnancies, glucose, BP, BMI, etc.)
- **Target:** Binary (0=No Diabetes, 1=Diabetes)
- **Algorithm:** Random Forest
- **Accuracy:** 0.7727
- **ROC-AUC:** 0.8283
- **Model File:** `disease_specific/diabetes_model.joblib`

### 3. Stroke Prediction
- **Dataset:** 5110 patients
- **Features:** 10 (age, hypertension, glucose, BMI, smoking, etc.)
- **Target:** Binary (0=No Stroke, 1=Stroke)
- **Algorithm:** Logistic Regression (with class balancing)
- **Accuracy:** 0.7515
- **ROC-AUC:** 0.8412
- **Model File:** `disease_specific/stroke_model.joblib`
- **Note:** Stroke is rare (~5% of population), model uses heavy class weighting

### 4. Multi-Disease Classification
- **Dataset:** 4920 training + 42 test samples
- **Features:** 132 symptoms (binary 0/1)
- **Target:** 41 different diseases
- **Algorithm:** Random Forest
- **Accuracy:** 0.9762
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
**Generated:** 2026-06-28 02:38:03.641503
