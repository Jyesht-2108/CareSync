"""
Comprehensive Test Suite for Risk Assessment Model
===================================================
Tests the hybrid risk assessment system to ensure it correctly identifies
high-risk patients based on vitals, disease risks, and clinical conditions.
"""

import requests
import json
from typing import Dict

API_URL = "http://localhost:8000"

def test_case(name: str, payload: Dict, expected_risk: str) -> bool:
    """Run a single test case"""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")
    
    try:
        response = requests.post(f"{API_URL}/api/evaluate-risk", json=payload)
        response.raise_for_status()
        result = response.json()
        
        print(f"✓ Request successful")
        print(f"  Risk Level: {result['risk_level']} (expected: {expected_risk})")
        print(f"  Risk Score: {result['risk_score']:.2%}")
        print(f"  Confidence: {result['confidence']:.2%}")
        
        if 'clinical_conditions' in result:
            if 'news2_score' in result['clinical_conditions']:
                print(f"  NEWS2 Score: {result['clinical_conditions']['news2_score']} ({result['clinical_conditions'].get('news2_risk', 'N/A')})")
            if 'primary_assessment' in result['clinical_conditions']:
                print(f"  Assessment: {result['clinical_conditions']['primary_assessment']}")
        
        if 'disease_predictions' in result and result['disease_predictions']:
            print(f"  Disease Risks:")
            for disease, risk in result['disease_predictions'].items():
                if risk is not None:
                    print(f"    - {disease}: {risk:.2%}")
        
        print(f"  Contributing Factors:")
        for factor in result.get('contributing_factors', [])[:3]:
            print(f"    - {factor['factor']}")
        
        # Check if result matches expectation
        passed = result['risk_level'] == expected_risk
        if passed:
            print(f"\n✅ PASSED: Risk level matches expected ({expected_risk})")
        else:
            print(f"\n❌ FAILED: Expected {expected_risk}, got {result['risk_level']}")
        
        return passed
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def run_tests():
    """Run comprehensive test suite"""
    
    print("=" * 60)
    print("CareSync Risk Assessment - Test Suite")
    print("=" * 60)
    print("\nMake sure the backend is running on http://localhost:8000")
    print("Start it with: uvicorn app.main:app --reload")
    
    # Check if backend is running
    try:
        response = requests.get(f"{API_URL}/health")
        print(f"\n✓ Backend is healthy: {response.json()}")
    except:
        print(f"\n❌ ERROR: Backend not running. Start it first!")
        return
    
    results = []
    
    # ═══ TEST 1: Normal Patient - Should be LOW ═══
    results.append(test_case(
        "Normal Healthy Patient",
        {
            "vitals": {
                "heart_rate": 75,
                "systolic_bp": 120,
                "diastolic_bp": 80,
                "temperature": 36.8,
                "spo2": 98
            },
            "demographics": {
                "age": 35,
                "gender": "Male",
                "smoking_status": "Never",
                "diabetes": "No",
                "hypertension": "No"
            },
            "ehr_notes": "Routine checkup. Patient feeling well.",
            "clinical_summary": "No concerns noted."
        },
        expected_risk="Low"
    ))
    
    # ═══ TEST 2: Severe Hypoxia - Should be HIGH ═══
    results.append(test_case(
        "Severe Hypoxia (Critical Safety Override)",
        {
            "vitals": {
                "heart_rate": 110,
                "systolic_bp": 100,
                "diastolic_bp": 65,
                "temperature": 37.2,
                "spo2": 85  # CRITICAL!
            },
            "demographics": {
                "age": 55,
                "gender": "Female",
                "smoking_status": "Never",
                "diabetes": "No",
                "hypertension": "No"
            },
            "ehr_notes": "",  # NO CLINICAL NOTES!
            "clinical_summary": ""
        },
        expected_risk="High"
    ))
    
    # ═══ TEST 3: Abnormal Vitals Without Text - Should be MEDIUM or HIGH ═══
    results.append(test_case(
        "Multiple Abnormal Vitals (No Clinical Notes)",
        {
            "vitals": {
                "heart_rate": 125,  # Tachycardia
                "systolic_bp": 95,  # Hypotension
                "diastolic_bp": 60,
                "temperature": 38.5,  # Fever
                "spo2": 92  # Low oxygen
            },
            "demographics": {
                "age": 65,
                "gender": "Male",
                "smoking_status": "Former",
                "diabetes": "Yes",
                "hypertension": "Yes"
            },
            "ehr_notes": "",  # NO CLINICAL NOTES!
            "clinical_summary": ""
        },
        expected_risk="High"  # Should be High due to NEWS2 score
    ))
    
    # ═══ TEST 4: Stroke Risk Profile - Should be HIGH ═══
    results.append(test_case(
        "High Stroke Risk Patient",
        {
            "vitals": {
                "heart_rate": 95,
                "systolic_bp": 180,  # Hypertension
                "diastolic_bp": 100,
                "temperature": 37.0,
                "spo2": 96
            },
            "demographics": {
                "age": 72,
                "gender": "Male",
                "smoking_status": "Current",
                "diabetes": "Yes",
                "hypertension": "Yes"
            },
            "ehr_notes": "Patient reports weakness on left side",
            "clinical_summary": "Possible TIA, urgent evaluation needed"
        },
        expected_risk="High"
    ))
    
    # ═══ TEST 5: Severe Bradycardia - Should be HIGH ═══
    results.append(test_case(
        "Severe Bradycardia (Safety Override)",
        {
            "vitals": {
                "heart_rate": 32,  # CRITICAL!
                "systolic_bp": 105,
                "diastolic_bp": 70,
                "temperature": 36.5,
                "spo2": 97
            },
            "demographics": {
                "age": 68,
                "gender": "Female",
                "smoking_status": "Never",
                "diabetes": "No",
                "hypertension": "No"
            },
            "ehr_notes": "",
            "clinical_summary": ""
        },
        expected_risk="High"
    ))
    
    # ═══ TEST 6: Diabetic with Infection - Should be MEDIUM/HIGH ═══
    results.append(test_case(
        "Diabetic Patient with Fever",
        {
            "vitals": {
                "heart_rate": 105,
                "systolic_bp": 110,
                "diastolic_bp": 75,
                "temperature": 39.2,  # High fever
                "spo2": 95
            },
            "demographics": {
                "age": 58,
                "gender": "Male",
                "smoking_status": "Never",
                "diabetes": "Yes",
                "hypertension": "Yes"
            },
            "ehr_notes": "Patient reports chills and fatigue. Wound on foot looks infected.",
            "clinical_summary": "Suspected diabetic foot infection"
        },
        expected_risk="Medium"  # Could be High depending on NEWS2
    ))
    
    # ═══ TEST 7: Hypertensive Emergency - Should be HIGH ═══
    results.append(test_case(
        "Hypertensive Emergency",
        {
            "vitals": {
                "heart_rate": 105,
                "systolic_bp": 225,  # CRITICAL!
                "diastolic_bp": 120,
                "temperature": 37.0,
                "spo2": 96
            },
            "demographics": {
                "age": 55,
                "gender": "Female",
                "smoking_status": "Never",
                "diabetes": "No",
                "hypertension": "Yes"
            },
            "ehr_notes": "Severe headache, nausea",
            "clinical_summary": ""
        },
        expected_risk="High"
    ))
    
    # ═══ TEST 8: Elderly with Borderline Vitals - Should be MEDIUM ═══
    results.append(test_case(
        "Elderly Patient with Borderline Vitals",
        {
            "vitals": {
                "heart_rate": 92,
                "systolic_bp": 100,
                "diastolic_bp": 65,
                "temperature": 38.1,
                "spo2": 94
            },
            "demographics": {
                "age": 82,
                "gender": "Female",
                "smoking_status": "Never",
                "diabetes": "No",
                "hypertension": "No"
            },
            "ehr_notes": "Fall at home yesterday. Some confusion.",
            "clinical_summary": "Monitor for 24 hours"
        },
        expected_risk="Medium"
    ))
    
    # ═══ Summary ═══
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total} ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("✅ ALL TESTS PASSED!")
    else:
        print(f"⚠️  {total - passed} test(s) failed")
        print("\nFailed tests indicate the model may need adjustment.")
        print("Review the output above to see which scenarios failed.")


if __name__ == "__main__":
    run_tests()
