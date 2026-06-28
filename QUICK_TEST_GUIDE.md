# 30-Second Test Guide: Verify the Contradiction Fix

## What to Test
Verify that the system now explains why risk can be HIGH even when NEWS2 (vitals) shows Low.

---

## Test Steps

### 1. Open Browser
Navigate to: **http://localhost:5173**

### 2. Enter Patient Data (Copy-Paste Ready)

**Demographics:**
- Age: `68`
- Gender: `Male`
- Diabetes: `Yes`
- Hypertension: `Yes`
- Smoking Status: `Former`

**Current Vitals:**
- Heart Rate: `75`
- Systolic BP: `125`
- Diastolic BP: `82`
- SpO2: `97`
- Temperature: `36.8`

**Clinical Notes:**
```
Routine follow-up visit. Patient reports taking medications as prescribed. No current symptoms.
```

### 3. Click "Evaluate Risk"

Wait ~5 seconds for loading animation.

---

## What You Should See ✅

### Overall Risk Card
- **Risk Level:** HIGH (60-75%)
- **Color:** Red/Orange
- **Primary Assessment:** "High disease risk detected (vitals currently stable)"

### NEWS2 Card (This is the key!)
- **Score:** 0-4
- **Risk Level:** Low Risk (GREEN indicator)
- **Status Text:** "Current vitals stable"
- **📋 Assessment Section:** Should say "High disease risk detected (vitals currently stable)"
- **⚠️ AMBER WARNING BOX:** Should appear below with explanation:
  > "While current vitals are stable (NEWS2: Low), the overall HIGH risk is driven by disease-specific indicators and chronic risk factors. This suggests long-term cardiovascular risk rather than acute distress."

### Disease Predictions
- **Heart Disease:** 65-75% (explains the HIGH overall risk)
- **Diabetes Risk:** May show elevated

---

## Success Criteria

✅ Overall risk shows HIGH  
✅ NEWS2 shows Low Risk with green color  
✅ **Amber warning box is VISIBLE** in NEWS2 card  
✅ Warning explains "vitals currently stable"  
✅ No apparent contradiction - everything makes sense  

---

## If You Don't See the Warning Box

1. **Hard refresh browser:** Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
2. **Check servers are running:**
   - Backend: http://localhost:8000/health
   - Frontend: http://localhost:5173
3. **Check browser console** (F12) for errors

---

## What This Proves

The system correctly identifies and explains scenarios where:
- **Long-term disease risk** is HIGH (chronic conditions)
- **Acute vital stability** is LOW risk (current vitals normal)
- Both assessments are correct and now clearly explained

This is a **common real-world medical scenario** (e.g., diabetic patient on medication).

---

## Alternative Test (If First Test Doesn't Trigger)

Try patient with even more chronic risk factors:

**Demographics:**
- Age: `72`
- Gender: `Male`
- Diabetes: `Yes`
- Hypertension: `Yes`
- Smoking Status: `Current`

**Vitals:** (same stable vitals)
- HR: `78`, BP: `128/80`, SpO2: `96%`, Temp: `37.0`

**Notes:**
```
Patient has family history of heart disease. Taking metformin, lisinopril, and atorvastatin daily.
```

This should **definitely** trigger HIGH disease risk with Low NEWS2.

---

## Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| Page blank | Hard refresh: Cmd+Shift+R |
| No amber box | Make sure Age > 65, Diabetes=Yes, Hypertension=Yes |
| Backend error | Check terminal: `cd backend && source venv/bin/activate && uvicorn backend.app.main:app --reload --port 8000` |
| Frontend error | Check terminal: `cd frontend && npm run dev` |

---

## Expected Time
**Total test time:** 30-60 seconds  
**Loading animation:** 5 seconds  
**Verification:** 10 seconds  

---

## Files Updated (For Reference)

- `backend/app/main.py` (lines 820-827): Detection logic
- `frontend/src/App.jsx` (lines 514-523): Warning banner
- Both servers auto-reloaded with changes

---

## Status

✅ **Backend:** Running on port 8000  
✅ **Frontend:** Running on port 5173  
✅ **All Models:** Loaded successfully  
✅ **Fix:** Deployed and active  
✅ **Ready:** For testing NOW  

---

## Bottom Line

Open browser → Enter data → Click button → **Look for amber warning box** → Done! ✅
