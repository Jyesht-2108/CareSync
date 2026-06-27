#!/usr/bin/env python3
"""
Quick API test script to verify CareSync backend responses
"""
import requests
import json

API_URL = "http://localhost:8000"

# Test 1: Health check
print("=" * 60)
print("Test 1: Health Check")
print("=" * 60)
response = requests.get(f"{API_URL}/health")
print(json.dumps(response.json(), indent=2))

# Test 2: Low-risk patient
print("\n" + "=" * 60)
print("Test 2: Low-Risk Patient Profile")
print("=" * 60)
low_risk_payload = {
    "vitals": {
        "heart_rate": 72,
        "systolic_bp": 120,
        "diastolic_bp": 80,
        "temperature": 36.6,
        "spo2": 98
    },
    "demographics": {
        "age": 35,
        "gender": "Female",
        "smoking_status": "Never",
        "diabetes": "No",
        "hypertension": "No"
    },
    "ehr_notes": "Patient feeling well, routine checkup",
    "clinical_summary": "No concerns identified"
}
response = requests.post(f"{API_URL}/api/evaluate-risk", json=low_risk_payload)
result = response.json()
print(f"Risk Level: {result['risk_level']}")
print(f"Risk Score: {result['risk_score']:.4f}")
print(f"Confidence: {result['confidence']:.4f}")
print(f"Top Factors: {[f['factor'] for f in result['contributing_factors']]}")

# Test 3: High-risk patient
print("\n" + "=" * 60)
print("Test 3: High-Risk Patient Profile")
print("=" * 60)
high_risk_payload = {
    "vitals": {
        "heart_rate": 130,
        "systolic_bp": 90,
        "diastolic_bp": 60,
        "temperature": 38.5,
        "spo2": 88
    },
    "demographics": {
        "age": 75,
        "gender": "Male",
        "smoking_status": "Current",
        "diabetes": "Yes",
        "hypertension": "Yes"
    },
    "ehr_notes": "Chest pain, shortness of breath, dizziness",
    "clinical_summary": "Urgent cardiac evaluation needed"
}
response = requests.post(f"{API_URL}/api/evaluate-risk", json=high_risk_payload)
result = response.json()
print(f"Risk Level: {result['risk_level']}")
print(f"Risk Score: {result['risk_score']:.4f}")
print(f"Confidence: {result['confidence']:.4f}")
print(f"Top Factors: {[f['factor'] for f in result['contributing_factors']]}")

# Test 4: Medium-risk patient
print("\n" + "=" * 60)
print("Test 4: Medium-Risk Patient Profile")
print("=" * 60)
medium_risk_payload = {
    "vitals": {
        "heart_rate": 95,
        "systolic_bp": 140,
        "diastolic_bp": 90,
        "temperature": 37.2,
        "spo2": 94
    },
    "demographics": {
        "age": 55,
        "gender": "Male",
        "smoking_status": "Former",
        "diabetes": "Yes",
        "hypertension": "Yes"
    },
    "ehr_notes": "Mild fatigue, elevated blood pressure",
    "clinical_summary": "Monitor closely, medication adjustment may be needed"
}
response = requests.post(f"{API_URL}/api/evaluate-risk", json=medium_risk_payload)
result = response.json()
print(f"Risk Level: {result['risk_level']}")
print(f"Risk Score: {result['risk_score']:.4f}")
print(f"Confidence: {result['confidence']:.4f}")
print(f"Top Factors: {[f['factor'] for f in result['contributing_factors']]}")

print("\n" + "=" * 60)
print("✅ All tests completed!")
print("=" * 60)
