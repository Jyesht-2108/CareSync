"""
CareSync — Pydantic Schemas
============================
Request/response models for the /api/evaluate-risk endpoint.
Validates incoming patient data and structures the risk assessment output.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class VitalsInput(BaseModel):
    """
    Current patient vitals — a single snapshot.
    Units match the training data conventions:
      - heart_rate: beats per minute (normal 60-100)
      - systolic_bp / diastolic_bp: mmHg
      - temperature: degrees Celsius (normal ~36.5-37.5)
      - spo2: percent oxygen saturation (normal 95-100%)
    """
    heart_rate: float = Field(..., ge=20, le=250, description="Heart rate in BPM")
    systolic_bp: float = Field(..., ge=50, le=300, description="Systolic blood pressure in mmHg")
    diastolic_bp: float = Field(..., ge=20, le=200, description="Diastolic blood pressure in mmHg")
    temperature: float = Field(..., ge=30, le=45, description="Body temperature in °C")
    spo2: float = Field(..., ge=50, le=100, description="Oxygen saturation in %")


class DemographicsInput(BaseModel):
    """Patient demographics matching the training schema."""
    age: int = Field(..., ge=0, le=120, description="Patient age in years")
    gender: str = Field(..., pattern="^(Male|Female)$", description="Patient gender")
    smoking_status: str = Field(..., pattern="^(Never|Former|Current)$", description="Smoking status")
    diabetes: str = Field(..., pattern="^(Yes|No)$", description="Diabetes status")
    hypertension: str = Field(..., pattern="^(Yes|No)$", description="Hypertension status")


class RiskAssessmentRequest(BaseModel):
    """
    Full patient evaluation request.
    
    For the prototype, we accept a single vitals snapshot and use it as
    both the "latest" value and the mean (since we only have one reading).
    In production, this would accept a time-series array.
    """
    vitals: VitalsInput
    demographics: DemographicsInput
    ehr_notes: str = Field(
        default="",
        max_length=5000,
        description="Clinical notes / presenting complaints"
    )
    clinical_summary: str = Field(
        default="",
        max_length=5000,
        description="Clinical summary text"
    )


class ContributingFactor(BaseModel):
    """A feature that contributed significantly to the risk prediction."""
    factor: str
    importance: float


class RiskAssessmentResponse(BaseModel):
    """
    Risk assessment output with clinical condition indicators and disease predictions.
    
    Thresholds (documented assumption):
      - High:   probability >= 0.5 for class 2
      - Medium: probability >= 0.3 for class 1 (and not High)
      - Low:    otherwise
    
    These thresholds are intentionally aggressive for High-risk to minimize
    missed deteriorating patients (the key safety requirement).
    
    Clinical conditions are rule-based indicators derived from vitals and
    clinical notes - these help contextualize the risk prediction.
    
    Disease predictions use ML models trained on disease-specific datasets:
    - heart_disease: probability of heart disease (0-1)
    - diabetes: probability of diabetes (0-1)
    - stroke: probability of stroke (0-1)
    """
    risk_score: float = Field(..., description="Risk probability 0-1 (higher = more risk)")
    risk_level: str = Field(..., description="Low / Medium / High")
    contributing_factors: List[ContributingFactor]
    confidence: float = Field(..., description="Model confidence in the prediction")
    clinical_conditions: dict = Field(
        default_factory=dict,
        description="Specific clinical condition indicators (sepsis, respiratory, etc.)"
    )
    disease_predictions: dict = Field(
        default_factory=dict,
        description="Disease-specific risk predictions (heart_disease, diabetes, stroke)"
    )
