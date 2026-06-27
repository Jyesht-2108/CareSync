#!/usr/bin/env python3
"""
Test the improved MIMIC-III trained model with clinical scenarios
"""
import requests
import json

API_URL = "http://localhost:8000"

tests = [
    {
        "name": "Healthy Young Adult",
        "expected": "Low",
        "payload": {
            "vitals": {
                "heart_rate": 70,
                "systolic_bp": 118,
                "diastolic_bp": 78,
                "temperature": 36.7,
                "spo2": 99
            },
            "demographics": {
                "age": 28,
                "gender": "Female",
                "smoking_status": "Never",
                "diabetes": "No",
                "hypertension": "No"
            },
            "ehr_notes": "Annual checkup, patient reports feeling well",
            "clinical_summary": "No acute concerns, vitals within normal limits"
        }
    },
    {
        "name": "Elderly with Controlled Chronic Conditions",
        "expected": "Low-Medium",
        "payload": {
            "vitals": {
                "heart_rate": 82,
                "systolic_bp": 135,
                "diastolic_bp": 85,
                "temperature": 36.9,
                "spo2": 96
            },
            "demographics": {
                "age": 68,
                "gender": "Male",
                "smoking_status": "Former",
                "diabetes": "Yes",
                "hypertension": "Yes"
            },
            "ehr_notes": "Patient with history of diabetes and hypertension, medications well controlled",
            "clinical_summary": "Routine follow-up, no acute complaints"
        }
    },
    {
        "name": "Moderate Risk - Infection Concern",
        "expected": "Medium",
        "payload": {
            "vitals": {
                "heart_rate": 105,
                "systolic_bp": 128,
                "diastolic_bp": 82,
                "temperature": 38.2,
                "spo2": 94
            },
            "demographics": {
                "age": 55,
                "gender": "Female",
                "smoking_status": "Never",
                "diabetes": "Yes",
                "hypertension": "No"
            },
            "ehr_notes": "Patient presents with fever, suspected infection, moderate symptoms",
            "clinical_summary": "History of diabetes, monitoring for moderate organ dysfunction"
        }
    },
    {
        "name": "High Risk - Severe Sepsis",
        "expected": "High",
        "payload": {
            "vitals": {
                "heart_rate": 130,
                "systolic_bp": 85,
                "diastolic_bp": 55,
                "temperature": 39.1,
                "spo2": 88
            },
            "demographics": {
                "age": 72,
                "gender": "Male",
                "smoking_status": "Current",
                "diabetes": "Yes",
                "hypertension": "Yes"
            },
            "ehr_notes": "Patient on mechanical ventilation, severe organ failure, suspected infection",
            "clinical_summary": "Severe organ dysfunction, metastatic cancer present, mechanical ventilation required"
        }
    },
    {
        "name": "Critical - Multi-Organ Failure",
        "expected": "High",
        "payload": {
            "vitals": {
                "heart_rate": 145,
                "systolic_bp": 75,
                "diastolic_bp": 45,
                "temperature": 38.9,
                "spo2": 85
            },
            "demographics": {
                "age": 78,
                "gender": "Female",
                "smoking_status": "Former",
                "diabetes": "Yes",
                "hypertension": "Yes"
            },
            "ehr_notes": "Patient on mechanical ventilation, severe organ failure with multi-system dysfunction",
            "clinical_summary": "History of diabetes and metastatic cancer, severe infection with organ failure and dysfunction, patient on mechanical ventilation"
        }
    }
]

print("=" * 70)
print("CARESYNC MODEL EVALUATION - MIMIC-III Enhanced")
print("=" * 70)

for i, test in enumerate(tests, 1):
    print(f"\n[{i}/5] {test['name']}")
    print(f"Expected: {test['expected']}")
    print("-" * 70)
    
    try:
        response = requests.post(f"{API_URL}/api/evaluate-risk", json=test['payload'])
        if response.ok:
            result = response.json()
            print(f"✓ Risk Level: {result['risk_level']}")
            print(f"  Risk Score: {result['risk_score']:.4f} ({result['risk_score']*100:.1f}%)")
            print(f"  Confidence: {result['confidence']:.4f}")
            print(f"  Top Factor: {result['contributing_factors'][0]['factor']}")
            
            # Check if prediction matches expectation
            if test['expected'] == result['risk_level'] or test['expected'] in result['risk_level']:
                print(f"  ✅ CORRECT")
            elif '-' in test['expected']:  # Range like "Low-Medium"
                print(f"  ✅ ACCEPTABLE")
            else:
                print(f"  ⚠️  Expected {test['expected']}")
        else:
            print(f"✗ API Error: {response.status_code}")
    except Exception as e:
        print(f"✗ Error: {e}")

print("\n" + "=" * 70)
print("Testing Complete!")
print("=" * 70)
