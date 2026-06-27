import { useState } from 'react'

const API_URL = 'http://localhost:8000'

/**
 * CareSync — Privacy-preserving clinical decision-support dashboard
 * 
 * Adaptive Cognitive Load UI:
 * - Low/Medium risk: Full detail view with charts, vitals, contributing factors
 * - High risk: Stripped-down emergency view with large text, high contrast,
 *   and prominent "CALL AMBULANCE" action. Designed for stressed field workers.
 * 
 * All processing happens locally — no patient data leaves the device.
 */

/* ─── Vitals trend mini-chart (SVG sparkline) ─────────────────────── */
function VitalsChart({ label, value, unit, min, max, color }) {
  const normalMin = min
  const normalMax = max
  const pct = Math.max(0, Math.min(100, ((value - normalMin) / (normalMax - normalMin)) * 100))
  const isAbnormal = value < normalMin || value > normalMax

  // Generate sparkline data (simulated 24h trend)
  const generateSparkline = () => {
    const points = 24
    const data = []
    const variance = (normalMax - normalMin) * 0.1
    
    for (let i = 0; i < points; i++) {
      const trend = (value - normalMin) / (normalMax - normalMin)
      const noise = (Math.random() - 0.5) * variance
      const point = value + noise
      data.push(Math.max(normalMin, Math.min(normalMax, point)))
    }
    
    // Ensure last point is the current value
    data[data.length - 1] = value
    return data
  }

  const sparklineData = generateSparkline()
  const sparklinePoints = sparklineData.map((val, idx) => {
    const x = (idx / (sparklineData.length - 1)) * 100
    const y = 100 - ((val - normalMin) / (normalMax - normalMin)) * 100
    return `${x},${y}`
  }).join(' ')

  return (
    <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl p-4 border border-slate-700/50 hover:border-slate-600/50 transition-all duration-300 group">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">{label}</span>
        <span className={`text-xs font-semibold px-2 py-0.5 rounded-full transition-all duration-300 ${isAbnormal ? 'bg-amber-500/20 text-amber-400 animate-pulse' : 'bg-emerald-500/20 text-emerald-400'}`}>
          {isAbnormal ? 'Abnormal' : 'Normal'}
        </span>
      </div>
      <div className="flex items-end gap-2 mb-3">
        <span className="text-3xl font-bold text-white">{typeof value === 'number' ? value.toFixed(1) : value}</span>
        <span className="text-sm text-slate-400 mb-1">{unit}</span>
      </div>
      
      {/* Sparkline trend */}
      <div className="mb-3 h-10 relative">
        <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="w-full h-full opacity-60 group-hover:opacity-100 transition-opacity duration-300">
          <polyline
            points={sparklinePoints}
            fill="none"
            stroke={isAbnormal ? '#f59e0b' : color}
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <polyline
            points={sparklinePoints}
            fill={isAbnormal ? 'url(#gradient-warn)' : `url(#gradient-${label})`}
            opacity="0.2"
          />
          <defs>
            <linearGradient id={`gradient-${label}`} x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity="0.5"/>
              <stop offset="100%" stopColor={color} stopOpacity="0"/>
            </linearGradient>
            <linearGradient id="gradient-warn" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#f59e0b" stopOpacity="0.5"/>
              <stop offset="100%" stopColor="#f59e0b" stopOpacity="0"/>
            </linearGradient>
          </defs>
        </svg>
      </div>
      
      {/* Progress bar showing where value falls in range */}
      <div className="mt-2 h-2 bg-slate-700 rounded-full overflow-hidden relative">
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{
            width: `${pct}%`,
            background: isAbnormal
              ? 'linear-gradient(90deg, #f59e0b, #ef4444)'
              : `linear-gradient(90deg, ${color}, ${color}88)`,
          }}
        />
      </div>
      <div className="flex justify-between mt-1">
        <span className="text-[10px] text-slate-500">{min}</span>
        <span className="text-[10px] text-slate-500">{max}</span>
      </div>
    </div>
  )
}

/* ─── Privacy Badge ───────────────────────────────────────────────── */
function PrivacyBadge() {
  return (
    <div className="fixed bottom-4 left-4 z-50 flex items-center gap-2 bg-emerald-900/80 backdrop-blur-md text-emerald-300 text-xs font-medium px-3 py-2 rounded-full border border-emerald-700/50 shadow-lg shadow-emerald-900/20">
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
      </svg>
      <span>On-device · Local-first</span>
    </div>
  )
}

/* ─── Emergency / High-Risk View ──────────────────────────────────── */
function EmergencyView({ result, onReset }) {
  return (
    <div className="min-h-screen bg-red-950 flex flex-col items-center justify-center px-4 animate-pulse-slow">
      {/* Flashing danger header */}
      <div className="w-full max-w-lg mx-auto text-center">
        <div className="mb-6 flex justify-center">
          <div className="w-20 h-20 rounded-full bg-red-600 flex items-center justify-center animate-ping-slow shadow-2xl shadow-red-600/50">
            <svg className="w-10 h-10 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
        </div>

        <h1 className="text-5xl sm:text-6xl font-black text-white tracking-wider mb-4" style={{ letterSpacing: '0.15em' }}>
          ⚠ HIGH RISK
        </h1>
        <p className="text-2xl sm:text-3xl font-bold text-red-200 mb-2 tracking-wide">
          PATIENT NEEDS IMMEDIATE CARE
        </p>
        <p className="text-xl text-red-300/80 mb-8">
          Risk Score: {(result.risk_score * 100).toFixed(0)}%
        </p>

        {/* Contributing factors — simplified */}
        <div className="bg-red-900/60 rounded-2xl p-4 mb-8 border border-red-700/50">
          <p className="text-lg font-bold text-red-200 mb-3 tracking-wide">KEY CONCERNS:</p>
          {result.contributing_factors.map((f, i) => (
            <p key={i} className="text-xl font-semibold text-white mb-1 tracking-wide">
              • {f.factor}
            </p>
          ))}
        </div>

        {/* CALL AMBULANCE — dominant action */}
        <a
          href="tel:108"
          id="call-ambulance-btn"
          className="block w-full bg-red-600 hover:bg-red-500 active:bg-red-400 text-white text-3xl sm:text-4xl font-black py-6 px-8 rounded-2xl shadow-2xl shadow-red-600/40 transition-all duration-200 tracking-widest border-4 border-red-400 mb-4"
          style={{ letterSpacing: '0.2em' }}
        >
          📞 CALL AMBULANCE
        </a>
        <p className="text-sm text-red-400 mb-6">Dial 108 (India Emergency)</p>

        <button
          onClick={onReset}
          id="emergency-back-btn"
          className="text-red-400 hover:text-red-300 text-sm underline transition-colors"
        >
          ← Back to assessment
        </button>
      </div>

      <PrivacyBadge />

      <style>{`
        @keyframes ping-slow {
          0% { transform: scale(1); opacity: 1; }
          50% { transform: scale(1.15); opacity: 0.8; }
          100% { transform: scale(1); opacity: 1; }
        }
        @keyframes pulse-slow {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.95; }
        }
        .animate-ping-slow { animation: ping-slow 2s ease-in-out infinite; }
        .animate-pulse-slow { animation: pulse-slow 3s ease-in-out infinite; }
      `}</style>
    </div>
  )
}

/* ─── Standard Results View (Low / Medium) ────────────────────────── */
function ResultsView({ result, formData, onReset }) {
  const isLow = result.risk_level === 'Low'
  const riskColor = isLow ? 'emerald' : 'amber'

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 pb-24">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-slate-900/80 backdrop-blur-xl border-b border-slate-800/50">
        <div className="max-w-lg mx-auto px-4 py-3 flex items-center justify-between">
          <button onClick={onReset} className="text-slate-400 hover:text-white transition-colors" id="back-btn">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <h1 className="text-lg font-bold text-white tracking-wide">Assessment Results</h1>
          <div className="w-6" />
        </div>
      </header>

      <div className="max-w-lg mx-auto px-4 pt-6 space-y-6">
        {/* Risk Score Card with Gauge */}
        <div className={`bg-gradient-to-br from-${riskColor}-900/40 to-${riskColor}-950/40 rounded-3xl p-6 border border-${riskColor}-700/30 shadow-xl`}
          style={{
            background: isLow
              ? 'linear-gradient(135deg, rgba(6,78,59,0.4), rgba(6,78,59,0.15))'
              : 'linear-gradient(135deg, rgba(120,53,15,0.4), rgba(120,53,15,0.15))',
            borderColor: isLow ? 'rgba(16,185,129,0.3)' : 'rgba(245,158,11,0.3)',
          }}>
          <div className="text-center">
            <p className="text-sm font-medium text-slate-400 uppercase tracking-widest mb-4">Risk Level</p>
            
            {/* Circular Risk Gauge */}
            <div className="relative w-40 h-40 mx-auto mb-4">
              <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                {/* Background circle */}
                <circle
                  cx="50"
                  cy="50"
                  r="40"
                  fill="none"
                  stroke="rgba(100,116,139,0.2)"
                  strokeWidth="8"
                />
                {/* Progress circle */}
                <circle
                  cx="50"
                  cy="50"
                  r="40"
                  fill="none"
                  stroke={isLow ? '#10b981' : '#f59e0b'}
                  strokeWidth="8"
                  strokeLinecap="round"
                  strokeDasharray={`${result.risk_score * 251.2} 251.2`}
                  className="transition-all duration-1000 ease-out"
                  style={{
                    filter: `drop-shadow(0 0 8px ${isLow ? '#10b98140' : '#f59e0b40'})`
                  }}
                />
              </svg>
              {/* Center text */}
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <div className="text-4xl font-black text-white mb-1">
                  {(result.risk_score * 100).toFixed(0)}%
                </div>
                <div className="text-xs text-slate-400">Risk Score</div>
              </div>
            </div>
            
            <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-lg font-bold mb-2`}
              style={{
                backgroundColor: isLow ? 'rgba(16,185,129,0.2)' : 'rgba(245,158,11,0.2)',
                color: isLow ? '#6ee7b7' : '#fcd34d',
              }}>
              <span className="w-3 h-3 rounded-full animate-pulse" style={{ backgroundColor: isLow ? '#10b981' : '#f59e0b' }} />
              {result.risk_level}
            </div>
            <p className="text-sm text-slate-400">Confidence: {(result.confidence * 100).toFixed(0)}%</p>
          </div>
        </div>

        {/* Contributing Factors */}
        <div className="bg-slate-800/40 backdrop-blur-sm rounded-2xl p-5 border border-slate-700/40">
          <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-widest mb-4">Contributing Factors</h3>
          <div className="space-y-3">
            {result.contributing_factors.map((f, i) => (
              <div key={i} className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-xl flex items-center justify-center text-sm font-bold"
                  style={{
                    backgroundColor: i === 0 ? 'rgba(139,92,246,0.2)' : i === 1 ? 'rgba(59,130,246,0.2)' : 'rgba(107,114,128,0.2)',
                    color: i === 0 ? '#c4b5fd' : i === 1 ? '#93c5fd' : '#9ca3af',
                  }}>
                  {i + 1}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-white">{f.factor}</p>
                  <div className="mt-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all duration-1000"
                      style={{
                        width: `${Math.min(100, f.importance * 500)}%`,
                        background: i === 0 ? 'linear-gradient(90deg, #8b5cf6, #a78bfa)' : i === 1 ? 'linear-gradient(90deg, #3b82f6, #60a5fa)' : 'linear-gradient(90deg, #6b7280, #9ca3af)',
                      }} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Vitals Overview */}
        <div>
          <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-widest mb-3 px-1">Current Vitals</h3>
          <div className="grid grid-cols-2 gap-3">
            <VitalsChart label="Heart Rate" value={formData.heart_rate} unit="BPM" min={60} max={100} color="#ef4444" />
            <VitalsChart label="SpO₂" value={formData.spo2} unit="%" min={95} max={100} color="#3b82f6" />
            <VitalsChart label="Systolic BP" value={formData.systolic_bp} unit="mmHg" min={90} max={140} color="#8b5cf6" />
            <VitalsChart label="Temp" value={formData.temperature} unit="°C" min={36.1} max={37.5} color="#f59e0b" />
          </div>
        </div>

        {/* Patient Info */}
        <div className="bg-slate-800/40 backdrop-blur-sm rounded-2xl p-5 border border-slate-700/40">
          <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-widest mb-3">Patient Info</h3>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div><span className="text-slate-500">Age:</span> <span className="text-white font-medium">{formData.age}</span></div>
            <div><span className="text-slate-500">Gender:</span> <span className="text-white font-medium">{formData.gender}</span></div>
            <div><span className="text-slate-500">Smoking:</span> <span className="text-white font-medium">{formData.smoking_status}</span></div>
            <div><span className="text-slate-500">Diabetes:</span> <span className="text-white font-medium">{formData.diabetes}</span></div>
            <div><span className="text-slate-500">Hypertension:</span> <span className="text-white font-medium">{formData.hypertension}</span></div>
          </div>
        </div>
      </div>

      <PrivacyBadge />
    </div>
  )
}

/* ─── Main App ────────────────────────────────────────────────────── */
export default function App() {
  const [formData, setFormData] = useState({
    heart_rate: '',
    systolic_bp: '',
    diastolic_bp: '',
    temperature: '',
    spo2: '',
    age: '',
    gender: 'Male',
    smoking_status: 'Never',
    diabetes: 'No',
    hypertension: 'No',
    ehr_notes: '',
    clinical_summary: '',
  })
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    const payload = {
      vitals: {
        heart_rate: parseFloat(formData.heart_rate),
        systolic_bp: parseFloat(formData.systolic_bp),
        diastolic_bp: parseFloat(formData.diastolic_bp),
        temperature: parseFloat(formData.temperature),
        spo2: parseFloat(formData.spo2),
      },
      demographics: {
        age: parseInt(formData.age),
        gender: formData.gender,
        smoking_status: formData.smoking_status,
        diabetes: formData.diabetes,
        hypertension: formData.hypertension,
      },
      ehr_notes: formData.ehr_notes || '',
      clinical_summary: formData.clinical_summary || '',
    }

    try {
      const res = await fetch(`${API_URL}/api/evaluate-risk`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.detail || `Server error: ${res.status}`)
      }
      const data = await res.json()
      setResult(data)
    } catch (err) {
      setError(err.message || 'Failed to connect to the CareSync backend')
    } finally {
      setLoading(false)
    }
  }

  const resetForm = () => {
    setResult(null)
    setError(null)
  }

  // ─── Emergency View ───────────────────────────────────────────
  if (result && result.risk_level === 'High') {
    return <EmergencyView result={result} onReset={resetForm} />
  }

  // ─── Results View (Low / Medium) ──────────────────────────────
  if (result) {
    return <ResultsView result={result} formData={formData} onReset={resetForm} />
  }

  // ─── Input Form ───────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 pb-24">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-slate-900/80 backdrop-blur-xl border-b border-slate-800/50">
        <div className="max-w-lg mx-auto px-4 py-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-violet-600 to-blue-600 flex items-center justify-center shadow-lg shadow-violet-600/20">
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
              </svg>
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-wide">CareSync</h1>
              <p className="text-xs text-slate-400">Clinical Decision Support</p>
            </div>
          </div>
        </div>
      </header>

      <form onSubmit={handleSubmit} className="max-w-lg mx-auto px-4 pt-6 space-y-6">
        {/* Vitals Section */}
        <section>
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-xl bg-red-500/20 flex items-center justify-center">
              <svg className="w-4 h-4 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
              </svg>
            </div>
            <h2 className="text-lg font-semibold text-white">Patient Vitals</h2>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {[
              { name: 'heart_rate', label: 'Heart Rate', placeholder: '72', unit: 'BPM' },
              { name: 'spo2', label: 'SpO₂', placeholder: '98', unit: '%' },
              { name: 'systolic_bp', label: 'Systolic BP', placeholder: '120', unit: 'mmHg' },
              { name: 'diastolic_bp', label: 'Diastolic BP', placeholder: '80', unit: 'mmHg' },
              { name: 'temperature', label: 'Temperature', placeholder: '36.6', unit: '°C' },
            ].map(field => (
              <div key={field.name} className={field.name === 'temperature' ? 'col-span-2' : ''}>
                <label className="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-wider">{field.label}</label>
                <div className="relative">
                  <input
                    type="number"
                    step="any"
                    name={field.name}
                    id={`input-${field.name}`}
                    value={formData[field.name]}
                    onChange={handleChange}
                    placeholder={field.placeholder}
                    required
                    className="w-full bg-slate-800/60 border border-slate-700/50 rounded-xl px-4 py-3 text-white placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-violet-500/50 focus:border-violet-500/50 transition-all text-base"
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-500">{field.unit}</span>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Demographics Section */}
        <section>
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-xl bg-blue-500/20 flex items-center justify-center">
              <svg className="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </div>
            <h2 className="text-lg font-semibold text-white">Demographics</h2>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-wider">Age</label>
              <input
                type="number"
                name="age"
                id="input-age"
                value={formData.age}
                onChange={handleChange}
                placeholder="45"
                required
                className="w-full bg-slate-800/60 border border-slate-700/50 rounded-xl px-4 py-3 text-white placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-violet-500/50 focus:border-violet-500/50 transition-all text-base"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-wider">Gender</label>
              <select
                name="gender"
                id="input-gender"
                value={formData.gender}
                onChange={handleChange}
                className="w-full bg-slate-800/60 border border-slate-700/50 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-violet-500/50 focus:border-violet-500/50 transition-all text-base appearance-none"
              >
                <option value="Male">Male</option>
                <option value="Female">Female</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-wider">Smoking</label>
              <select
                name="smoking_status"
                id="input-smoking"
                value={formData.smoking_status}
                onChange={handleChange}
                className="w-full bg-slate-800/60 border border-slate-700/50 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-violet-500/50 focus:border-violet-500/50 transition-all text-base appearance-none"
              >
                <option value="Never">Never</option>
                <option value="Former">Former</option>
                <option value="Current">Current</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-wider">Diabetes</label>
              <select
                name="diabetes"
                id="input-diabetes"
                value={formData.diabetes}
                onChange={handleChange}
                className="w-full bg-slate-800/60 border border-slate-700/50 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-violet-500/50 focus:border-violet-500/50 transition-all text-base appearance-none"
              >
                <option value="No">No</option>
                <option value="Yes">Yes</option>
              </select>
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-wider">Hypertension</label>
              <select
                name="hypertension"
                id="input-hypertension"
                value={formData.hypertension}
                onChange={handleChange}
                className="w-full bg-slate-800/60 border border-slate-700/50 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-violet-500/50 focus:border-violet-500/50 transition-all text-base appearance-none"
              >
                <option value="No">No</option>
                <option value="Yes">Yes</option>
              </select>
            </div>
          </div>
        </section>

        {/* Clinical Notes Section */}
        <section>
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-xl bg-violet-500/20 flex items-center justify-center">
              <svg className="w-4 h-4 text-violet-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h2 className="text-lg font-semibold text-white">Clinical Notes</h2>
          </div>
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-wider">Presenting Complaints</label>
              <textarea
                name="ehr_notes"
                id="input-ehr-notes"
                value={formData.ehr_notes}
                onChange={handleChange}
                placeholder="e.g. Patient presented with chest pain and shortness of breath"
                rows={2}
                className="w-full bg-slate-800/60 border border-slate-700/50 rounded-xl px-4 py-3 text-white placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-violet-500/50 focus:border-violet-500/50 transition-all text-sm resize-none"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-wider">Clinical Summary</label>
              <textarea
                name="clinical_summary"
                id="input-clinical-summary"
                value={formData.clinical_summary}
                onChange={handleChange}
                placeholder="e.g. Follow-up recommended in 2 weeks"
                rows={2}
                className="w-full bg-slate-800/60 border border-slate-700/50 rounded-xl px-4 py-3 text-white placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-violet-500/50 focus:border-violet-500/50 transition-all text-sm resize-none"
              />
            </div>
          </div>
        </section>

        {/* Error Display */}
        {error && (
          <div className="bg-red-900/30 border border-red-700/50 rounded-xl p-4 text-red-300 text-sm">
            <p className="font-medium">⚠ Error</p>
            <p className="mt-1 text-red-400">{error}</p>
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          id="submit-btn"
          disabled={loading}
          className="w-full bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-500 hover:to-blue-500 disabled:from-slate-700 disabled:to-slate-700 text-white font-bold py-4 px-6 rounded-2xl shadow-xl shadow-violet-600/20 transition-all duration-300 text-lg tracking-wide disabled:cursor-not-allowed"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-3">
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Analyzing...
            </span>
          ) : (
            'Evaluate Risk'
          )}
        </button>
      </form>

      <PrivacyBadge />
    </div>
  )
}
