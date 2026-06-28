# Sample Data Button Feature

## What Was Added

A "Load Sample Data" button that instantly fills the form with realistic high-risk patient data for testing.

## Location

The button appears in the top-right of the form, just above the "Patient Vitals" section.

## Sample Data Loaded

When clicked, the button fills the form with:

### Vitals (High Risk Profile)
- **Heart Rate:** 95 BPM (elevated/tachycardia)
- **Blood Pressure:** 165/98 mmHg (Stage 2 hypertension)
- **Temperature:** 37.8°C (mild fever)
- **SpO2:** 92% (mild hypoxia)

### Demographics
- **Age:** 68 years (elderly)
- **Gender:** Male
- **Smoking Status:** Current smoker
- **Diabetes:** Yes
- **Hypertension:** Yes

### Clinical Notes
- **EHR Notes:** "Patient complains of chest discomfort and shortness of breath. History of coronary artery disease."
- **Clinical Summary:** "Presents with elevated BP, tachycardia, mild hypoxia. Known cardiovascular risk factors."

## Expected Risk Assessment

This sample data should trigger a **HIGH RISK** assessment because:
- Multiple cardiovascular risk factors (smoking, diabetes, hypertension)
- Elevated vital signs (high BP, tachycardia)
- Respiratory concern (low SpO2)
- Elderly patient with significant medical history
- Symptomatic presentation (chest discomfort, SOB)

## Usage

1. Open the app (localhost:5173)
2. Look for the purple "Load Sample Data" button (top-right, with lightning bolt icon)
3. Click it - all fields populate instantly
4. Click "Evaluate Risk" to see the results
5. Perfect for testing JARVIS voice assistant!

## Benefits

✅ **No more typing** - Instant data entry
✅ **Consistent testing** - Same data every time
✅ **Realistic scenario** - Clinically accurate high-risk profile
✅ **Demo-friendly** - Quick turnaround for presentations
✅ **JARVIS testing** - Immediately test voice features with rich context

## Customization

To change the sample data, edit the `loadSampleData()` function in `frontend/src/App.jsx` around line 1030.

You can create multiple sample scenarios:
- Low risk patient (healthy vitals)
- Medium risk (some concerns)
- High risk (current implementation)
- Critical emergency (extreme values)

## Visual Design

- **Color:** Purple/violet theme matching the app
- **Icon:** Lightning bolt (⚡) for "quick action"
- **Position:** Top-right, non-intrusive
- **Style:** Consistent with the app's glassmorphism design
