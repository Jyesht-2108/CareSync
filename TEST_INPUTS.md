# 🧪 CareSync Test Inputs - Quick Reference

Copy and paste these values into the frontend form to test different risk levels.

---

## 🟢 TEST 1: LOW RISK (Healthy Patient)

### Vitals:
```
Heart Rate: 72
SpO₂: 98
Systolic BP: 120
Diastolic BP: 80
Temperature: 36.6
```

### Demographics:
```
Age: 35
Gender: Female
Smoking: Never
Diabetes: No
Hypertension: No
```

### Clinical Notes:
```
Presenting Complaints: Patient feeling well, routine checkup
Clinical Summary: No concerns identified
```

**Expected Result:** ✅ LOW Risk (~3-10%)

---

## 🟡 TEST 2: MEDIUM RISK (Infection Concern)

### Vitals:
```
Heart Rate: 105
SpO₂: 94
Systolic BP: 140
Diastolic BP: 90
Temperature: 37.8
```

### Demographics:
```
Age: 58
Gender: Male
Smoking: Former
Diabetes: Yes
Hypertension: Yes
```

### Clinical Notes:
```
Presenting Complaints: Patient presents with fever, suspected infection, moderate symptoms
Clinical Summary: History of diabetes, monitoring for moderate organ dysfunction
```

**Expected Result:** ⚠️ MEDIUM Risk (~40-60%)

---

## 🔴 TEST 3: HIGH RISK (Critical - Emergency Mode)

### Vitals:
```
Heart Rate: 145
SpO₂: 85
Systolic BP: 75
Diastolic BP: 45
Temperature: 38.9
```

### Demographics:
```
Age: 78
Gender: Female
Smoking: Former
Diabetes: Yes
Hypertension: Yes
```

### Clinical Notes:
```
Presenting Complaints: Patient on mechanical ventilation, severe organ failure with multi-system dysfunction
Clinical Summary: History of diabetes and metastatic cancer, severe infection with organ failure and dysfunction, patient on mechanical ventilation
```

**Expected Result:** 🚨 HIGH Risk (~70-100%) - **EMERGENCY MODE ACTIVATES!**

---

## 📋 What to Look For:

### LOW RISK:
- ✅ Green color scheme
- ✅ Risk gauge showing ~4-10%
- ✅ Sparkline trends on all vitals
- ✅ All vitals marked "Normal"
- ✅ Full detail view with charts

### MEDIUM RISK:
- ⚠️ Amber/yellow color scheme
- ⚠️ Risk gauge showing ~40-60%
- ⚠️ Some vitals marked "Abnormal"
- ⚠️ Still shows full details
- ⚠️ Contributing factors highlight infection

### HIGH RISK (Emergency Mode):
- 🚨 **DRAMATIC CHANGE!**
- 🔴 Deep red background
- 🔤 Giant "⚠ HIGH RISK" text
- 📊 Charts REMOVED
- 📞 Massive "CALL AMBULANCE" button
- ⚡ Pulsing animations
- 🔠 Wide letter spacing for readability

---

## 🎯 New Visualizations Added:

1. **Sparkline Trends** - Each vital card now shows a 24-hour simulated trend line
2. **Risk Gauge** - Circular progress indicator showing risk percentage
3. **Hover Effects** - Cards highlight when you hover over them
4. **Animated Progress Bars** - Smooth fill animation on load
5. **Glow Effects** - Risk gauge has a subtle glow matching the risk level

---

## 💡 Pro Tips:

- **Test Emergency Mode First!** It's the most impressive feature
- The HIGH RISK keywords that trigger it: "severe", "organ failure", "mechanical ventilation", "dysfunction"
- Try different combinations - the model is smart!
- Watch the sparklines animate in
- Notice how abnormal vitals pulse
- The risk gauge fills smoothly when the page loads

---

**Ready to test? Start with TEST 3 (HIGH RISK) to see the emergency mode!** 🚀
