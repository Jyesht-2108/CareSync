# CareSync — Manual Testing Guide

This guide walks you through testing CareSync's complete functionality, including the adaptive UI behavior.

## Prerequisites
- Backend running on http://localhost:8000
- Frontend running on http://localhost:5174
- Browser open to http://localhost:5174

---

## Test Scenario 1: LOW RISK Patient

### Patient Profile: Healthy Young Adult
1. **Fill in the form with these values:**

**Patient Vitals:**
- Heart Rate: `72`
- SpO₂: `98`
- Systolic BP: `120`
- Diastolic BP: `80`
- Temperature: `36.6`

**Demographics:**
- Age: `28`
- Gender: `Female`
- Smoking: `Never`
- Diabetes: `No`
- Hypertension: `No`

**Clinical Notes:**
- Presenting Complaints: `Patient feeling well, routine checkup`
- Clinical Summary: `No concerns, continue monitoring`

2. **Click "Evaluate Risk"**

### Expected Results ✅
- **Risk Level Badge:** Green "Low" indicator
- **Risk Score:** ~3-10%
- **UI Behavior:** 
  - Full detail view displayed
  - Vitals charts visible with color-coded indicators
  - Contributing factors shown with importance bars
  - Normal font sizes and spacing
  - Patient info section visible
- **Privacy Badge:** "On-device · Local-first" visible in bottom-left

### Screenshot Checklist:
- [ ] Capture the LOW risk results view
- [ ] Verify all vitals charts are rendered
- [ ] Confirm privacy badge is visible

---

## Test Scenario 2: MEDIUM RISK Patient

### Patient Profile: Infection Concern
1. **Click "← Back" to return to the form**

2. **Fill in the form with these values:**

**Patient Vitals:**
- Heart Rate: `105`
- SpO₂: `94`
- Systolic BP: `128`
- Diastolic BP: `82`
- Temperature: `38.2`

**Demographics:**
- Age: `55`
- Gender: `Female`
- Smoking: `Never`
- Diabetes: `Yes`
- Hypertension: `No`

**Clinical Notes:**
- Presenting Complaints: `Patient presents with fever, suspected infection, moderate symptoms`
- Clinical Summary: `History of diabetes, monitoring for moderate organ dysfunction`

3. **Click "Evaluate Risk"**

### Expected Results ✅
- **Risk Level Badge:** Amber/Yellow "Medium" indicator
- **Risk Score:** ~40-60%
- **UI Behavior:**
  - Full detail view still displayed
  - Vitals may show amber warning indicators for abnormal values
  - Contributing factors highlight infection-related features
  - Standard formatting maintained
- **No Emergency Mode:** Charts and details still visible

### Screenshot Checklist:
- [ ] Capture the MEDIUM risk results view
- [ ] Note the amber/yellow color scheme
- [ ] Verify standard UI is maintained (not emergency mode)

---

## Test Scenario 3: HIGH RISK Patient (Emergency Mode)

### Patient Profile: Severe Sepsis / Critical Condition
1. **Click "← Back" to return to the form**

2. **Fill in the form with these values:**

**Patient Vitals:**
- Heart Rate: `145`
- SpO₂: `85`
- Systolic BP: `75`
- Diastolic BP: `45`
- Temperature: `38.9`

**Demographics:**
- Age: `78`
- Gender: `Female`
- Smoking: `Former`
- Diabetes: `Yes`
- Hypertension: `Yes`

**Clinical Notes:**
- Presenting Complaints: `Patient on mechanical ventilation, severe organ failure with multi-system dysfunction`
- Clinical Summary: `History of diabetes and metastatic cancer, severe infection with organ failure and dysfunction, patient on mechanical ventilation`

3. **Click "Evaluate Risk"**

### Expected Results ✅ CRITICAL
- **⚠️ EMERGENCY MODE ACTIVATED**
- **Visual Changes:**
  - Background: Deep red (red-950)
  - Large animated pulsing warning icon
  - Giant "⚠ HIGH RISK" header (5xl-6xl font with wide letter spacing)
  - "PATIENT NEEDS IMMEDIATE CARE" message in 2xl-3xl font
  - Risk score prominently displayed (should be 70-100%)
  
- **Key Concerns Section:**
  - Simplified bullet list of top risk factors
  - Large, bold white text on dark red background
  
- **CALL AMBULANCE Button:**
  - Massive red button (3xl-4xl font)
  - Text: "📞 CALL AMBULANCE"
  - Wide letter spacing for readability
  - Full width, dominant visual element
  - Sub-text: "Dial 108 (India Emergency)"
  
- **What's REMOVED:**
  - ❌ Vitals charts (stripped out)
  - ❌ Detailed patient info cards
  - ❌ Small text
  - ❌ Complex visualizations
  
- **What REMAINS:**
  - ✅ Privacy badge (still visible)
  - ✅ Small back button to return to assessment
  - ✅ Animated pulsing effects

### Screenshot Checklist:
- [ ] **CRITICAL:** Capture the HIGH risk EMERGENCY view
- [ ] Verify red color scheme dominates
- [ ] Confirm "CALL AMBULANCE" button is the largest element
- [ ] Verify simplified layout (no charts)
- [ ] Confirm wide letter spacing on main text
- [ ] Verify animated warning icon is visible

---

## Visual Comparison Test

### Compare the Three Views Side-by-Side:
1. Open all three test results in separate browser tabs/windows
2. Verify the dramatic visual difference between:
   - **Low:** Green, detailed, charts visible
   - **Medium:** Amber, detailed, warnings present
   - **High:** Red, simplified, emergency mode

### Key Differentiators to Highlight:
| Feature | Low/Medium | High (Emergency) |
|---------|------------|------------------|
| Background | Dark slate | Deep red |
| Font Size | Normal (base/sm/lg) | LARGE (3xl-6xl) |
| Charts | ✅ Visible | ❌ Hidden |
| Details | ✅ Full info | ❌ Simplified |
| Primary Action | "Back to assessment" | "CALL AMBULANCE" |
| Letter Spacing | Normal | Wide (0.15-0.2em) |
| Animations | Subtle | Pulsing/urgent |

---

## API Testing (Optional)

### Test Health Endpoint:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "model_loaded": true,
  "service": "CareSync",
  "privacy": "All processing is local — no data leaves this device"
}
```

---

## Browser Developer Tools Check

### Verify No External API Calls:
1. Open Browser Developer Tools (F12)
2. Go to Network tab
3. Submit a risk evaluation
4. **Verify:** Only `http://localhost:8000/api/evaluate-risk` appears
5. **No calls to:**
   - ❌ openai.com
   - ❌ huggingface.co
   - ❌ Any cloud AI services
   - ❌ Google Analytics
   - ❌ Third-party tracking

---

## Mobile Responsive Test

### Test on Different Screen Sizes:
1. Open DevTools (F12)
2. Click Device Toolbar icon (Ctrl+Shift+M)
3. Test on:
   - iPhone SE (375px) - Primary target
   - iPhone 12 Pro (390px)
   - iPhone 14 Pro Max (430px)
   - iPad Mini (768px)

### Verify:
- [ ] Form inputs are easily tappable
- [ ] Text is readable without zooming
- [ ] Emergency button fits on screen
- [ ] Privacy badge doesn't overlap content
- [ ] Charts scale appropriately

---

## Accessibility Quick Check

### Keyboard Navigation:
1. Tab through the form
2. Verify all inputs are reachable
3. Test Enter key to submit
4. Verify focus indicators are visible

### Color Contrast:
- [ ] Text is readable on all backgrounds
- [ ] Emergency mode has high contrast (red/white)
- [ ] Buttons have clear visual states

---

## Performance Test

### Page Load:
- Frontend should load in < 1 second
- No visible loading delays

### Risk Evaluation:
- API response should be < 200ms
- UI should update immediately
- No lag or freezing

---

## Final Checklist

### Documentation:
- [ ] README.md is updated with MIMIC-III details
- [ ] Model metrics report shows 87% accuracy
- [ ] VERIFICATION.md documents all tests
- [ ] AGENTS.md project rules are followed

### Screenshots to Capture:
1. [ ] Input form (before submission)
2. [ ] Low risk result (standard view)
3. [ ] Medium risk result (standard view with warnings)
4. [ ] High risk result (EMERGENCY MODE) - **Most Important**
5. [ ] Privacy badge visible in all views

### System Status:
- [ ] Backend running without errors
- [ ] Frontend running without errors
- [ ] Model loaded successfully
- [ ] All 5 test scenarios pass

---

## Troubleshooting

### Issue: Model predicts everything as Low
**Solution:** Clear browser cache and refresh. Ensure backend reloaded the new model.

### Issue: Emergency mode not triggering
**Solution:** Make sure clinical notes include key terms like "severe organ failure", "mechanical ventilation", "severe infection"

### Issue: API returns 422 error
**Solution:** Check that all required fields are filled and numeric values are valid

---

## Success Criteria ✅

Your testing is complete when:
1. ✅ All 3 risk levels display correctly
2. ✅ Emergency mode triggers for high-risk patients
3. ✅ UI transitions are smooth
4. ✅ Privacy badge is always visible
5. ✅ No external API calls detected
6. ✅ Screenshots captured for all scenarios
7. ✅ Mobile view is functional

**Status:** READY FOR HACKATHON DEMO
