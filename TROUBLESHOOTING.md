# CareSync - Troubleshooting Guide

## Issue: Empty/Blank UI

### Quick Fix Steps:

#### 1. Kill All Existing Processes
```bash
# Kill processes on port 8000 (backend)
lsof -ti:8000 | xargs kill -9

# Kill processes on port 5173 (frontend)
lsof -ti:5173 | xargs kill -9

# Kill processes on port 5174 (alternative frontend)
lsof -ti:5174 | xargs kill -9
```

#### 2. Use the Automated Start Script
```bash
cd /Users/prince/Desktop/ieee-dataport-hackathon
./START_SERVERS.sh
```

OR manually:

#### 3. Start Backend Manually
```bash
# Terminal 1 - Backend
cd /Users/prince/Desktop/ieee-dataport-hackathon/backend
source ../venv/bin/activate  # or: source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Wait for: "✅ All disease models loaded successfully"

#### 4. Start Frontend Manually
```bash
# Terminal 2 - Frontend
cd /Users/prince/Desktop/ieee-dataport-hackathon/frontend
npm run dev
```

Look for: "Local: http://localhost:5173/"

#### 5. Clear Browser Cache
- **Chrome/Edge**: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
- **Safari**: Cmd+Option+R
- **Firefox**: Cmd+Shift+R (Mac) or Ctrl+F5 (Windows)

#### 6. Check Browser Console
1. Open browser (Chrome recommended)
2. Go to http://localhost:5173
3. Press F12 or Cmd+Option+I
4. Click "Console" tab
5. Look for errors (red text)

---

## Common Errors & Solutions

### Error: "Cannot find module 'app.main'"
**Solution:** You're not in the backend directory
```bash
cd backend
uvicorn app.main:app --reload
```

### Error: "Module not found" (frontend)
**Solution:** Install dependencies
```bash
cd frontend
npm install
npm run dev
```

### Error: "Port 8000 already in use"
**Solution:** Kill the process
```bash
lsof -ti:8000 | xargs kill -9
# Then restart backend
```

### Error: "Port 5173 already in use"
**Solution:** Kill the process
```bash
lsof -ti:5173 | xargs kill -9
# Then restart frontend
```

### Error: Blank screen but no console errors
**Solutions:**
1. Check if backend is actually running: http://localhost:8000/health
2. Check if frontend is on a different port: http://localhost:5174
3. Check API_URL in frontend code matches backend port

### Error: "Failed to connect to backend"
**Solutions:**
1. Verify backend is running: `curl http://localhost:8000/health`
2. Check CORS settings in backend/app/main.py
3. Check API_URL in frontend/src/App.jsx is "http://localhost:8000"

### Error: Models not loading
**Solution:** Train the models first
```bash
cd backend
python train_model.py
python train_disease_models.py
```

---

## Verification Checklist

Run these commands to verify everything is working:

### 1. Check Backend Health
```bash
curl http://localhost:8000/health
```
Expected: `{"status":"healthy","model_loaded":true,...}`

### 2. Test Backend API
```bash
curl -X POST http://localhost:8000/api/evaluate-risk \
  -H "Content-Type: application/json" \
  -d '{
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
    "ehr_notes": "",
    "clinical_summary": ""
  }'
```
Expected: JSON with `risk_level`, `risk_score`, etc.

### 3. Check Frontend Dev Server
Open browser: http://localhost:5173
Expected: CareSync input form

### 4. Check Browser Console
Press F12 → Console tab
Expected: No red errors

---

## Complete Reset (Nuclear Option)

If nothing works, do a complete reset:

```bash
# 1. Kill everything
lsof -ti:8000 | xargs kill -9
lsof -ti:5173 | xargs kill -9

# 2. Clean frontend
cd frontend
rm -rf node_modules
rm package-lock.json
npm install

# 3. Restart backend
cd ../backend
source ../venv/bin/activate
uvicorn app.main:app --reload &

# 4. Wait 3 seconds
sleep 3

# 5. Restart frontend
cd ../frontend
npm run dev
```

---

## Debug Mode

### Enable Verbose Logging (Backend)
```bash
cd backend
uvicorn app.main:app --reload --log-level debug
```

### Enable Verbose Logging (Frontend)
Add to `frontend/src/App.jsx` at the top:
```javascript
console.log('App loaded')
```

Then check browser console (F12)

---

## Port Configuration

### Default Ports:
- Backend: **8000**
- Frontend: **5173** (or 5174 if 5173 is busy)

### Change Ports:

**Backend:**
```bash
uvicorn app.main:app --reload --port 8001
```
Then update `frontend/src/App.jsx`:
```javascript
const API_URL = 'http://localhost:8001'
```

**Frontend:**
Edit `frontend/vite.config.js`:
```javascript
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 3000  // Your custom port
  }
})
```

---

## Still Not Working?

### Check These:

1. **Is Python environment activated?**
   ```bash
   which python
   # Should show: /Users/prince/Desktop/ieee-dataport-hackathon/venv/bin/python
   ```

2. **Are models trained?**
   ```bash
   ls backend/app/models/*.joblib
   # Should show: risk_model.joblib, scaler.joblib, etc.
   ```

3. **Are dependencies installed?**
   ```bash
   # Backend
   pip list | grep fastapi
   
   # Frontend  
   cd frontend && npm list react
   ```

4. **Is browser cache cleared?**
   - Hard refresh: Cmd+Shift+R

5. **Try different browser:**
   - Chrome (recommended)
   - Firefox
   - Safari

6. **Check firewall/antivirus:**
   - May be blocking ports 8000 or 5173

---

## Contact Info (for presentation day)

If demo breaks during presentation:

1. **Have backup videos/screenshots ready**
2. **Show the automated tests instead:**
   ```bash
   cd backend
   python test_risk_assessment.py
   ```
3. **Show the code and explain the architecture**
4. **Show the model training reports in `backend/reports/`**

---

## Quick Status Check

Run this to see what's running:
```bash
echo "Backend (8000):" && lsof -ti:8000 && echo "Running ✅" || echo "Not running ❌"
echo "Frontend (5173):" && lsof -ti:5173 && echo "Running ✅" || echo "Not running ❌"
```

---

**Last Updated:** Now  
**For:** IEEE DataPort Hackathon Demo
