# CareSync — Privacy-Preserving Clinical Decision Support

CareSync is a local/edge-first clinical decision-support dashboard designed for frontline health workers (ASHA volunteers / rural PHC staff). It fuses a patient's time-series vitals with their EHR notes and demographics to output a single risk score (Low / Medium / High).

## Key Features
- **Adaptive Cognitive Load UI:** The dashboard automatically adjusts its UI based on the patient's risk level. For Low/Medium risk, it shows full details (vitals charts, normal text). For High risk, it collapses into a simplified, high-contrast "emergency" view with a bold "CALL AMBULANCE" action, optimized for stressed field workers.
- **Privacy-Preserving (Local-First):** All processing happens on-device. No patient data is sent to external APIs (like OpenAI/HuggingFace/cloud services). The model uses a locally trained Logistic Regression model and TF-IDF for text.
- **High-Performance ML Model:** Trained on 4,290 patients with 87% accuracy and 94% ROC-AUC, capable of accurately stratifying patient risk levels.

## Setup Instructions

### Prerequisites
- Python 3.10+
- Node.js (for React frontend)

### 1. Backend Setup
The backend runs on FastAPI and loads a pre-trained scikit-learn/XGBoost model.

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Run the training script (if you need to retrain the model)
# Note: The provided pre-trained model artifacts are already in backend/app/models/
python backend/train_model.py

# Start the FastAPI server
uvicorn backend.app.main:app --reload --port 8000
```
The backend API will run on `http://127.0.0.1:8000`.

### 2. Frontend Setup
The frontend is a mobile-first Vite + React app styled with Tailwind CSS.

```bash
cd frontend

# Install dependencies
npm install

# Start the Vite development server
npm run dev
```
The frontend will run on `http://localhost:5173`.

## Architecture & Model Choices

### Privacy-Preserving Architecture
To satisfy strict clinical privacy requirements, CareSync is architected as an "edge/local-first" application. 
- The backend relies on lightweight scikit-learn and XGBoost rather than external LLM APIs.
- The React application is designed to communicate with a locally-hosted API, avoiding cloud processing of sensitive PHI (Personal Health Information).

### Model Selection
We evaluated Logistic Regression, Random Forest, and XGBoost using stratified 5-fold cross-validation on a combined dataset of 4,290 patients.

**Training Data:**
- **Original Dataset:** 50 patients with 24-hour time-series vitals, demographics, and clinical EHR notes
- **MIMIC-III Dataset:** 4,240 ICU patients from the MIMIC-III Clinical Database with vitals, demographics, and 30-day mortality outcomes

**The Challenge:** The original dataset had only 50 patients, heavily imbalanced (30 Low, 15 Medium, 5 High). By integrating MIMIC-III data from IEEE DataPort, we achieved:
- **4,290 total patients** (86x larger dataset)
- **Balanced distribution:** 1,700 Low, 1,487 Medium, 1,103 High risk patients
- **Dramatic performance improvement:** 87% accuracy (up from 50%), 94.2% ROC-AUC (up from 59%)

**The Choice:** Logistic Regression was selected as the final model for its optimal balance of:
- **High-Risk Recall:** 58.4% (critical for not missing deteriorating patients)
- **Overall Accuracy:** 87%
- **ROC-AUC:** 94.2% (excellent discrimination)
- **Interpretability:** Clear feature importances for clinical transparency

**Features:** 
- *Vitals*: latest value, 24h rolling mean, rolling std, min, max, delta (or min/max-derived for MIMIC-III)
- *Demographics*: Age, gender, smoking status, diabetes, hypertension
- *EHR Notes*: Lightweight local TF-IDF (max 100 features) on clinical summaries

### Labeling Logic Assumption
**Original Dataset:** The dataset contains a `disease_risk_labels_0.csv` file mapping patient IDs to Low/Medium/High risk levels. We assumed the provided labels are the clinical ground truth to train the supervised model.

**MIMIC-III Dataset:** For the 4,240 ICU patients, we derived risk labels using a clinically grounded rule combining 30-day mortality outcomes with SOFA (Sequential Organ Failure Assessment) scores:
- **High Risk:** Patients who died within 30 days OR survived with SOFA ≥ 10 (severe organ failure)
- **Medium Risk:** Survived patients with SOFA 5-9 (moderate organ dysfunction)
- **Low Risk:** Survived patients with SOFA < 5 (minimal organ dysfunction)

This mapping ensures the model learns to identify both mortality risk and critical illness severity, which are the key outcomes for frontline clinical decision support.

**Data Source Attribution:**
- Original synthetic dataset provided for hackathon baseline
- MIMIC-III data obtained from IEEE DataPort platform (as permitted by hackathon rules for additional training data)

No manual clinical scoring rubrics (like MEWS/NEWS) were hardcoded because the combined dataset provided sufficient labeled supervision. This rationale is documented in `backend/train_model.py`.

## Evaluation Metrics

**Model Performance (5-Fold Cross-Validation on 4,290 patients):**
- **Accuracy:** 87%
- **ROC-AUC (weighted):** 94.2%
- **High-Risk Recall:** 58.4% (critical metric for patient safety)
- **Low-Risk Precision:** 90% (minimizes false alarms)
- **Medium-Risk Recall:** 95%

For full details on feature importances and fold-by-fold results, see `backend/reports/model_metrics.md`.
