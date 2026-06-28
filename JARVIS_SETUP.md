# JARVIS Voice Assistant - Setup Guide

## Overview

JARVIS is a voice-enabled AI medical assistant integrated into CareSync that allows ASHA workers to:
- **Ask questions** about risk assessments in natural language
- **Understand medical terminology** and vital signs
- **Get guidance** on when to refer patients to doctors
- **Speak naturally** using voice recognition and text-to-speech
- **Interact in Hinglish** (Hindi-English mix) when helpful

## Features

### 🎤 Voice Input
- Uses Web Speech API for voice recognition
- Supports Indian English (en-IN)
- Click "Hold to Speak" button to activate microphone
- Automatically transcribes speech to text

### 🔊 Voice Output
- Text-to-Speech for all AI responses
- Speaks responses automatically after generation
- Click "Stop Speaking" to interrupt

### 💬 Chat Interface
- Clean message history
- User messages (blue) and AI responses (dark)
- Timestamps for all messages
- Scrollable conversation

### 🤖 Context-Aware
- Automatically includes current patient data in context
- Understands risk assessment results
- Knows about vital signs, demographics, disease predictions
- References NEWS2 scores and clinical conditions

### ⚠️ Safety Features
- Disclaimer shown on first interaction
- AI states it's not a replacement for doctors
- Always mentions emergency number (108) when appropriate
- Emphasizes consulting medical professionals

---

## Setup Instructions

### Step 1: Get OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Sign in or create an account
3. Click "Create new secret key"
4. Copy the API key (starts with `sk-...`)
5. **Important:** Save it securely - you won't see it again!

### Step 2: Configure Backend

1. Open the backend `.env` file:
   ```bash
   nano /Users/prince/Desktop/ieee-dataport-hackathon/backend/.env
   ```

2. Replace `your_openai_api_key_here` with your actual API key:
   ```env
   OPENAI_API_KEY=sk-your-actual-api-key-here
   ```

3. Save and close (Ctrl+X, then Y, then Enter)

### Step 3: Restart Backend Server

The backend needs to be restarted to load the new API key:

```bash
# Stop the current backend process (if running)
# Then restart:
cd /Users/prince/Desktop/ieee-dataport-hackathon
source venv/bin/activate
cd backend
uvicorn app.main:app --reload --port 8000
```

You should see:
```
✅ OpenAI client initialized for JARVIS assistant
```

If you see:
```
⚠️  OPENAI_API_KEY not configured - JARVIS feature will be unavailable
```
Then the API key wasn't loaded correctly.

### Step 4: Test JARVIS

1. Open browser: http://localhost:5173
2. Complete a risk assessment (enter patient data and click "Evaluate Risk")
3. Look for the **floating blue button** in bottom-right corner
4. Click the button - JARVIS chat window should open
5. JARVIS will speak a disclaimer automatically
6. Try asking: "Why is the risk high?" or "What should I do?"

---

## Usage Examples

### Questions You Can Ask JARVIS:

**Understanding Risk:**
- "Why is the risk score so high?"
- "What does NEWS2 mean?"
- "Explain the heart disease risk"
- "What are the contributing factors?"

**Vital Signs:**
- "Is the blood pressure normal?"
- "Why is SpO2 important?"
- "What does low oxygen mean?"
- "Explain the heart rate reading"

**Next Steps:**
- "What should I do now?"
- "Does this patient need a doctor?"
- "Should I call an ambulance?"
- "What are the warning signs?"

**General Medical:**
- "What is diabetes?"
- "How do I check blood pressure?"
- "What are symptoms of a heart attack?"
- "What is a stroke?"

---

## Technical Details

### Backend API Endpoint

**POST** `/api/jarvis/chat`

Request:
```json
{
  "message": "Why is the risk high?",
  "risk_assessment_context": {
    "risk_level": "High",
    "risk_score": 0.72,
    "vitals": { ... },
    "demographics": { ... },
    "disease_predictions": { ... },
    "clinical_conditions": { ... }
  },
  "conversation_history": [
    {"role": "user", "content": "Previous question"},
    {"role": "assistant", "content": "Previous answer"}
  ]
}
```

Response:
```json
{
  "success": true,
  "message": "The high risk is primarily due to...",
  "role": "assistant",
  "model": "gpt-4o"
}
```

### Model Used

- **Model:** GPT-4o (OpenAI's latest multimodal model)
- **Temperature:** 0.7 (balanced creativity and accuracy)
- **Max Tokens:** 500 (concise responses)
- **Context:** Includes last 3 message exchanges (6 messages)

### System Prompt

JARVIS is configured with a specialized system prompt that:
- Identifies as an AI assistant for ASHA workers
- Always includes medical disclaimers
- Uses simple, clear language (Hinglish when helpful)
- Explains medical terms in plain language
- Emphasizes patient safety and referral when needed
- Shows empathy and support for ASHA workers

---

## Browser Compatibility

### Voice Recognition (Speech-to-Text)
✅ **Chrome/Edge:** Full support  
✅ **Safari:** Full support  
⚠️ **Firefox:** Limited support (may not work)  
✅ **Mobile Chrome (Android):** Full support  
✅ **Mobile Safari (iOS):** Full support  

### Text-to-Speech (Voice Output)
✅ **All modern browsers:** Supported via Web Speech API

### Fallback
If voice recognition doesn't work:
- Users can still type messages manually
- All functionality works via text input

---

## Privacy & Security

### Data Handling
- ⚠️ **JARVIS is the ONLY feature that sends data externally** (to OpenAI)
- Patient data context is sent to OpenAI API for conversation
- All other ML models run 100% locally
- No conversation history is stored on server

### What is Sent to OpenAI:
- User's question/message
- Current risk assessment summary
- Patient demographics (age, gender, conditions)
- Vital signs (heart rate, blood pressure, etc.)
- Disease predictions
- Last 3 message exchanges

### What is NOT Sent:
- Patient name or identifiers
- EHR notes with identifying information
- Full conversation history (only last 6 messages)

### OpenAI's Data Policy:
- API calls are NOT used for training models
- Data is NOT retained after 30 days
- See: https://openai.com/policies/api-data-usage-policies

---

## Troubleshooting

### "JARVIS service unavailable" Error

**Cause:** OpenAI API key not configured or invalid

**Solution:**
1. Check `.env` file has correct API key
2. Restart backend server
3. Check backend logs for: `✅ OpenAI client initialized`
4. Verify API key is valid at https://platform.openai.com/api-keys

### Voice Recognition Not Working

**Cause:** Browser doesn't support Web Speech API

**Solution:**
- Use Chrome, Edge, or Safari
- Allow microphone permissions when prompted
- Use text input as fallback (type instead of speak)

### JARVIS Not Speaking Responses

**Cause:** Text-to-Speech might be blocked or volume is off

**Solution:**
- Check system volume
- Check browser audio settings
- Click "Stop Speaking" and let it try again
- Some browsers require user interaction first

### Button Not Visible

**Cause:** Component not loaded or frontend not updated

**Solution:**
1. Hard refresh browser (Cmd+Shift+R / Ctrl+Shift+R)
2. Check browser console (F12) for errors
3. Restart frontend server: `cd frontend && npm run dev`

### API Rate Limits

**Cause:** Too many requests to OpenAI API

**Solution:**
- OpenAI has rate limits per API key
- Free tier: Limited requests per minute
- Upgrade to paid tier for higher limits
- See: https://platform.openai.com/account/limits

---

## Cost Estimates

### OpenAI API Pricing (GPT-4o)

- **Input:** $2.50 per 1M tokens (~750k words)
- **Output:** $10.00 per 1M tokens (~750k words)

### Per Conversation Estimate:
- Average question: ~200 tokens (~$0.0005)
- Average response: ~400 tokens (~$0.004)
- **Total per exchange:** ~$0.0045 (~₹0.38)

### For Hackathon Demo:
- 50 conversations × 5 exchanges each = 250 exchanges
- **Estimated cost:** $1.12 (₹95)
- Very affordable for demonstration!

### For Production:
- 1000 patients/month × 3 conversations each = 3000 exchanges
- **Estimated cost:** $13.50/month (₹1,140/month)
- Still very affordable compared to hiring phone support

---

## Demo Tips

### For Judges:

1. **Start Simple:**
   - "What does this risk score mean?"
   - "Why is it showing high risk?"

2. **Show Context Awareness:**
   - "What's concerning about the vital signs?"
   - "Should this patient see a doctor?"

3. **Demonstrate Voice:**
   - Click "Hold to Speak"
   - Ask: "What should the ASHA worker do next?"
   - JARVIS will respond with voice

4. **Show Safety Features:**
   - JARVIS always mentions consulting doctors
   - References emergency number (108)
   - Provides disclaimers

5. **Highlight User Empathy:**
   - Ask: "I'm worried about this patient, what should I do?"
   - JARVIS shows empathy for ASHA workers

### Key Talking Points:

✅ **Accessibility:** Voice interface for ASHA workers with varying literacy  
✅ **Context-Aware:** Understands current patient assessment  
✅ **Safety-First:** Always emphasizes professional medical consultation  
✅ **Bilingual Ready:** Can respond in Hinglish for local workers  
✅ **Educational:** Explains medical terms in simple language  
✅ **Supportive:** Shows empathy for challenging fieldwork  

---

## Future Enhancements (Not Implemented Yet)

### Potential Improvements:
- **Multilingual:** Full Hindi, Tamil, Telugu support
- **Offline Mode:** On-device small language model
- **SMS Integration:** Send summaries via SMS
- **Voice Commands:** "Call doctor", "Show vitals" shortcuts
- **Training Mode:** Quiz ASHA workers on medical knowledge
- **Case History:** Remember previous conversations per patient

---

## Support

### If Something Doesn't Work:

1. **Check Backend Logs:**
   ```bash
   # Look for errors in terminal running backend
   ```

2. **Check Frontend Console:**
   ```
   Open browser → F12 → Console tab
   ```

3. **Verify API Key:**
   ```bash
   cat backend/.env
   # Should show: OPENAI_API_KEY=sk-...
   ```

4. **Test Backend Health:**
   ```bash
   curl http://localhost:8000/health
   # Should show: "jarvis_available": true
   ```

---

## Summary

JARVIS adds a powerful conversational AI layer to CareSync that:
- Makes the system more accessible to ASHA workers
- Provides real-time medical guidance
- Explains complex medical information simply
- Supports both voice and text interaction
- Maintains safety through disclaimers and emphasis on professional care

**Setup Time:** 5 minutes  
**Cost:** ~$1-2 for demo, ~$15/month production  
**Impact:** Huge accessibility improvement for field workers!

---

## Quick Start Checklist

- [ ] Get OpenAI API key from https://platform.openai.com/api-keys
- [ ] Add API key to `backend/.env` file
- [ ] Restart backend server
- [ ] Verify: `✅ OpenAI client initialized` in logs
- [ ] Open http://localhost:5173
- [ ] Complete a risk assessment
- [ ] Click blue JARVIS button (bottom-right)
- [ ] Ask: "Why is the risk high?"
- [ ] ✅ JARVIS responds with voice!

**Status:** JARVIS is ready to demo! 🎉
