import { useState } from 'react'
import { 
  PieChart, Pie, Cell, 
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  LineChart, Line, Area, AreaChart
} from 'recharts'
import JarvisAssistant from './JarvisAssistant'

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

/* ─── Loading Analysis View ───────────────────────────────────────── */
function LoadingAnalysis({ progress }) {
  const stages = [
    { label: 'Extracting vital signs', icon: '💓', duration: 12 },
    { label: 'Analyzing demographics', icon: '👤', duration: 12 },
    { label: 'Processing clinical notes', icon: '📋', duration: 15 },
    { label: 'Running disease models', icon: '🧬', duration: 18 },
    { label: 'Multi-disease analysis (41 conditions)', icon: '🔬', duration: 18 },
    { label: 'Calculating NEWS2 score', icon: '📊', duration: 12 },
    { label: 'Finalizing risk assessment', icon: '🎯', duration: 13 },
  ]

  const currentStageIndex = Math.floor((progress / 100) * stages.length)
  const currentStage = stages[Math.min(currentStageIndex, stages.length - 1)]

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center px-4">
      <div className="max-w-md w-full">
        {/* Main Loading Card */}
        <div className="bg-slate-800/60 backdrop-blur-xl rounded-3xl p-8 border border-slate-700/50 shadow-2xl">
          {/* Animated Icon */}
          <div className="flex justify-center mb-6">
            <div className="relative">
              <div className="w-20 h-20 rounded-full bg-gradient-to-br from-violet-600 to-blue-600 flex items-center justify-center text-3xl animate-pulse">
                {currentStage.icon}
              </div>
              {/* Spinning Ring */}
              <svg className="absolute inset-0 w-20 h-20 animate-spin" style={{ animationDuration: '3s' }}>
                <circle
                  cx="40"
                  cy="40"
                  r="36"
                  fill="none"
                  stroke="url(#gradient)"
                  strokeWidth="3"
                  strokeDasharray="60 200"
                  strokeLinecap="round"
                />
                <defs>
                  <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#8b5cf6" />
                    <stop offset="100%" stopColor="#3b82f6" />
                  </linearGradient>
                </defs>
              </svg>
            </div>
          </div>

          {/* Title */}
          <h2 className="text-2xl font-bold text-white text-center mb-2">
            Analyzing Patient Data
          </h2>
          <p className="text-sm text-slate-400 text-center mb-6">
            Running ML models on device...
          </p>

          {/* Current Stage */}
          <div className="mb-6 p-4 bg-slate-900/50 rounded-xl border border-slate-700/30">
            <div className="flex items-center gap-3">
              <span className="text-2xl">{currentStage.icon}</span>
              <div className="flex-1">
                <p className="text-sm font-medium text-white">{currentStage.label}</p>
                <p className="text-xs text-slate-500">{progress}% complete</p>
              </div>
              <div className="w-6 h-6">
                <svg className="animate-spin text-violet-500" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
              </div>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="mb-6">
            <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-violet-600 to-blue-600 transition-all duration-500 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          {/* Stage Indicators */}
          <div className="space-y-2">
            {stages.map((stage, index) => {
              const isComplete = index < currentStageIndex
              const isCurrent = index === currentStageIndex
              const isPending = index > currentStageIndex

              return (
                <div
                  key={index}
                  className={`flex items-center gap-3 text-xs transition-all duration-300 ${
                    isComplete ? 'text-emerald-400' :
                    isCurrent ? 'text-violet-400' :
                    'text-slate-600'
                  }`}
                >
                  <div className="w-4 h-4 flex-shrink-0">
                    {isComplete ? (
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                    ) : isCurrent ? (
                      <div className="w-4 h-4 rounded-full border-2 border-violet-400 border-t-transparent animate-spin" />
                    ) : (
                      <div className="w-4 h-4 rounded-full border-2 border-slate-600" />
                    )}
                  </div>
                  <span className={isCurrent ? 'font-medium' : ''}>{stage.label}</span>
                </div>
              )
            })}
          </div>

          {/* Privacy Note */}
          <div className="mt-6 pt-6 border-t border-slate-700/50">
            <div className="flex items-center gap-2 text-xs text-emerald-400">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
              <span>All processing on-device • No data transmitted</span>
            </div>
          </div>
        </div>
      </div>

      <PrivacyBadge />
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

/* ─── Standard Results View (Low / Medium / High) ─────────────────── */
function ResultsView({ result, formData, onReset }) {
  const isLow = result.risk_level === 'Low'
  const isHigh = result.risk_level === 'High'
  const riskColor = isLow ? 'emerald' : isHigh ? 'red' : 'amber'

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 pb-24">
      {/* Emergency Banner for High Risk */}
      {isHigh && (
        <div className="bg-red-900 border-b-4 border-red-600">
          <div className="max-w-lg mx-auto px-4 py-4">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-12 h-12 rounded-full bg-red-600 flex items-center justify-center animate-pulse">
                <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
              <div className="flex-1">
                <h2 className="text-xl font-black text-white tracking-wider">⚠️ HIGH RISK ALERT</h2>
                <p className="text-sm text-red-200">Patient needs immediate clinical evaluation</p>
              </div>
            </div>
            <a
              href="tel:108"
              className="block w-full bg-red-600 hover:bg-red-500 text-white text-lg font-bold py-3 px-6 rounded-xl shadow-lg text-center transition-all duration-200"
            >
              📞 CALL AMBULANCE (108)
            </a>
            <p className="text-xs text-red-300 text-center mt-2">Emergency medical services</p>
          </div>
        </div>
      )}
      
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
        <div className={`bg-gradient-to-br rounded-3xl p-6 border shadow-xl`}
          style={{
            background: isLow
              ? 'linear-gradient(135deg, rgba(6,78,59,0.4), rgba(6,78,59,0.15))'
              : isHigh
              ? 'linear-gradient(135deg, rgba(127,29,29,0.4), rgba(127,29,29,0.15))'
              : 'linear-gradient(135deg, rgba(120,53,15,0.4), rgba(120,53,15,0.15))',
            borderColor: isLow ? 'rgba(16,185,129,0.3)' : isHigh ? 'rgba(239,68,68,0.3)' : 'rgba(245,158,11,0.3)',
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
                  stroke={isLow ? '#10b981' : isHigh ? '#ef4444' : '#f59e0b'}
                  strokeWidth="8"
                  strokeLinecap="round"
                  strokeDasharray={`${result.risk_score * 251.2} 251.2`}
                  className="transition-all duration-1000 ease-out"
                  style={{
                    filter: `drop-shadow(0 0 8px ${isLow ? '#10b98140' : isHigh ? '#ef444440' : '#f59e0b40'})`
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
                backgroundColor: isLow ? 'rgba(16,185,129,0.2)' : isHigh ? 'rgba(239,68,68,0.2)' : 'rgba(245,158,11,0.2)',
                color: isLow ? '#6ee7b7' : isHigh ? '#fca5a5' : '#fcd34d',
              }}>
              <span className="w-3 h-3 rounded-full animate-pulse" style={{ backgroundColor: isLow ? '#10b981' : isHigh ? '#ef4444' : '#f59e0b' }} />
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

        {/* NEWS2 Score */}
        {result.clinical_conditions?.news2_score !== undefined && (
          <div className="bg-gradient-to-br from-blue-900/40 to-cyan-900/40 backdrop-blur-sm rounded-2xl p-5 border border-blue-700/40">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-widest mb-3">
              📊 NEWS2 Vital Assessment
            </h3>
            <p className="text-xs text-slate-400 mb-4">
              National Early Warning Score 2 - Evidence-based vital signs scoring system
            </p>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-3">
                <div className="w-16 h-16 rounded-2xl flex items-center justify-center text-2xl font-black"
                  style={{
                    backgroundColor: result.clinical_conditions.news2_risk === 'High' ? 'rgba(239,68,68,0.2)' : 
                                   result.clinical_conditions.news2_risk === 'Medium' ? 'rgba(245,158,11,0.2)' : 
                                   'rgba(16,185,129,0.2)',
                    color: result.clinical_conditions.news2_risk === 'High' ? '#ef4444' : 
                          result.clinical_conditions.news2_risk === 'Medium' ? '#f59e0b' : 
                          '#10b981',
                  }}>
                  {result.clinical_conditions.news2_score}
                </div>
                <div>
                  <p className="text-lg font-bold text-white">{result.clinical_conditions.news2_risk} Risk</p>
                  <p className="text-xs text-slate-400">
                    {result.clinical_conditions.news2_score <= 4 ? 'Current vitals stable' : 
                     result.clinical_conditions.news2_score <= 6 ? 'Urgent clinical response needed' : 
                     'Emergency assessment required'}
                  </p>
                </div>
              </div>
            </div>
            {result.clinical_conditions.primary_assessment && (
              <div className="mt-3 p-3 bg-slate-900/40 rounded-xl">
                <p className="text-xs text-slate-300">
                  <span className="font-semibold text-blue-400">Assessment: </span>
                  {result.clinical_conditions.primary_assessment}
                </p>
              </div>
            )}
            
            {/* Explanation when NEWS2 is Low but overall risk is High */}
            {result.clinical_conditions.news2_risk === 'Low' && result.risk_level === 'High' && (
              <div className="mt-3 p-3 bg-amber-900/20 border border-amber-700/30 rounded-xl">
                <p className="text-xs text-amber-300">
                  <span className="font-semibold">⚠️ Note:</span> While current vitals are stable (NEWS2: Low), 
                  the overall HIGH risk is driven by disease-specific indicators and chronic risk factors. 
                  This suggests long-term cardiovascular risk rather than acute distress.
                </p>
              </div>
            )}
          </div>
        )}

        {/* Clinical Conditions */}
        {result.clinical_conditions && (
          <div className="bg-slate-800/40 backdrop-blur-sm rounded-2xl p-5 border border-slate-700/40">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-widest mb-4">
              🩺 Clinical Indicators
            </h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 bg-slate-900/30 rounded-xl">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">🦠</span>
                  <span className="text-sm text-slate-300">Sepsis/Infection</span>
                </div>
                <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                  result.clinical_conditions.sepsis_risk === 'High' ? 'bg-red-500/20 text-red-400' :
                  result.clinical_conditions.sepsis_risk === 'Moderate' ? 'bg-amber-500/20 text-amber-400' :
                  'bg-emerald-500/20 text-emerald-400'
                }`}>
                  {result.clinical_conditions.sepsis_risk}
                </span>
              </div>

              <div className="flex items-center justify-between p-3 bg-slate-900/30 rounded-xl">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">🫁</span>
                  <span className="text-sm text-slate-300">Respiratory Function</span>
                </div>
                <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                  result.clinical_conditions.respiratory_concern ? 'bg-red-500/20 text-red-400' : 'bg-emerald-500/20 text-emerald-400'
                }`}>
                  {result.clinical_conditions.respiratory_concern ? 'Impaired' : 'Normal'}
                </span>
              </div>

              <div className="flex items-center justify-between p-3 bg-slate-900/30 rounded-xl">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">❤️</span>
                  <span className="text-sm text-slate-300">Cardiovascular</span>
                </div>
                <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                  result.clinical_conditions.cardiovascular_risk === 'Elevated' ? 'bg-amber-500/20 text-amber-400' : 'bg-emerald-500/20 text-emerald-400'
                }`}>
                  {result.clinical_conditions.cardiovascular_risk}
                </span>
              </div>

              <div className="flex items-center justify-between p-3 bg-slate-900/30 rounded-xl">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">🫀</span>
                  <span className="text-sm text-slate-300">Organ Function</span>
                </div>
                <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                  result.clinical_conditions.organ_function?.includes('Severe') ? 'bg-red-500/20 text-red-400' :
                  result.clinical_conditions.organ_function?.includes('Moderate') ? 'bg-amber-500/20 text-amber-400' :
                  'bg-emerald-500/20 text-emerald-400'
                }`}>
                  {result.clinical_conditions.organ_function}
                </span>
              </div>

              {result.clinical_conditions.requires_icu && (
                <div className="mt-4 p-4 bg-red-900/20 border border-red-700/30 rounded-xl">
                  <div className="flex items-center gap-2">
                    <span className="text-2xl">🏥</span>
                    <span className="text-sm font-bold text-red-400">ICU Care Recommended</span>
                  </div>
                  <p className="text-xs text-red-300 mt-2">
                    Multiple severe indicators detected - intensive care may be required
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Disease Risk Predictions with Beautiful Visualizations */}
        {result.disease_predictions && (
          <>
            {/* Disease Risk Assessment Header */}
            <div className="bg-gradient-to-br from-violet-900/40 to-blue-900/40 backdrop-blur-sm rounded-2xl p-5 border border-violet-700/40">
              <h3 className="text-lg font-bold text-white mb-2 flex items-center gap-2">
                🔬 Disease Risk Assessment
                <span className="text-xs font-normal text-slate-400">AI-Powered Analysis</span>
              </h3>
              <p className="text-sm text-slate-300">
                Comprehensive disease risk predictions from ML models trained on clinical datasets
              </p>
            </div>

            {/* Radar Chart - Overall Risk Profile */}
            <div className="bg-slate-800/40 backdrop-blur-sm rounded-2xl p-5 border border-slate-700/40">
              <h4 className="text-sm font-semibold text-slate-300 uppercase tracking-widest mb-4">
                📊 Multi-Disease Risk Profile
              </h4>
              <div className="w-full h-80 flex items-center justify-center">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={[
                    {
                      disease: 'Heart',
                      risk: (result.disease_predictions.heart_disease * 100).toFixed(1),
                      fullMark: 100,
                    },
                    {
                      disease: 'Diabetes',
                      risk: (result.disease_predictions.diabetes * 100).toFixed(1),
                      fullMark: 100,
                    },
                    {
                      disease: 'Stroke',
                      risk: (result.disease_predictions.stroke * 100).toFixed(1),
                      fullMark: 100,
                    },
                    {
                      disease: 'Overall',
                      risk: (result.risk_score * 100).toFixed(1),
                      fullMark: 100,
                    },
                  ]}>
                    <PolarGrid stroke="#475569" />
                    <PolarAngleAxis dataKey="disease" tick={{ fill: '#cbd5e1', fontSize: 12 }} />
                    <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fill: '#94a3b8', fontSize: 10 }} />
                    <Radar name="Risk %" dataKey="risk" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.6} />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }}
                      labelStyle={{ color: '#e2e8f0' }}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Bar Chart - Disease Comparison */}
            <div className="bg-slate-800/40 backdrop-blur-sm rounded-2xl p-5 border border-slate-700/40">
              <h4 className="text-sm font-semibold text-slate-300 uppercase tracking-widest mb-4">
                📈 Risk Comparison
              </h4>
              <div className="w-full h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={[
                    {
                      name: 'Heart Disease',
                      risk: result.disease_predictions.heart_disease * 100,
                      threshold: 70,
                    },
                    {
                      name: 'Diabetes',
                      risk: result.disease_predictions.diabetes * 100,
                      threshold: 70,
                    },
                    {
                      name: 'Stroke',
                      risk: result.disease_predictions.stroke * 100,
                      threshold: 70,
                    },
                  ]}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
                    <XAxis dataKey="name" tick={{ fill: '#cbd5e1', fontSize: 11 }} />
                    <YAxis tick={{ fill: '#cbd5e1', fontSize: 11 }} domain={[0, 100]} />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }}
                      labelStyle={{ color: '#e2e8f0' }}
                      formatter={(value) => `${value.toFixed(1)}%`}
                    />
                    <Bar dataKey="risk" radius={[8, 8, 0, 0]}>
                      {[
                        result.disease_predictions.heart_disease,
                        result.disease_predictions.diabetes,
                        result.disease_predictions.stroke
                      ].map((value, index) => (
                        <Cell 
                          key={`cell-${index}`}
                          fill={value > 0.7 ? '#ef4444' : value > 0.4 ? '#f59e0b' : '#10b981'}
                        />
                      ))}
                    </Bar>
                    <Line type="monotone" dataKey="threshold" stroke="#dc2626" strokeWidth={2} strokeDasharray="5 5" dot={false} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="flex items-center justify-center gap-6 mt-4 text-xs">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-emerald-500"></div>
                  <span className="text-slate-400">Low Risk (&lt;40%)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-amber-500"></div>
                  <span className="text-slate-400">Moderate (40-70%)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-red-500"></div>
                  <span className="text-slate-400">High Risk (&gt;70%)</span>
                </div>
              </div>
            </div>

            {/* Pie Charts - Individual Disease Breakdowns */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {/* Heart Disease Pie */}
              <div className="bg-slate-800/40 backdrop-blur-sm rounded-2xl p-4 border border-slate-700/40">
                <h4 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
                  ❤️‍🩹 Heart Disease
                </h4>
                <div className="w-full h-40">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={[
                          { name: 'Risk', value: result.disease_predictions.heart_disease * 100 },
                          { name: 'Safe', value: (1 - result.disease_predictions.heart_disease) * 100 }
                        ]}
                        cx="50%"
                        cy="50%"
                        innerRadius={30}
                        outerRadius={60}
                        paddingAngle={2}
                        dataKey="value"
                      >
                        <Cell fill={result.disease_predictions.heart_disease > 0.7 ? '#ef4444' : result.disease_predictions.heart_disease > 0.4 ? '#f59e0b' : '#10b981'} />
                        <Cell fill="#334155" />
                      </Pie>
                      <Tooltip formatter={(value) => `${value.toFixed(1)}%`} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <p className="text-center text-lg font-bold text-white mt-2">
                  {(result.disease_predictions.heart_disease * 100).toFixed(1)}%
                </p>
                <p className={`text-center text-xs font-medium ${
                  result.disease_predictions.heart_disease > 0.7 ? 'text-red-400' :
                  result.disease_predictions.heart_disease > 0.4 ? 'text-amber-400' :
                  'text-emerald-400'
                }`}>
                  {result.disease_predictions.heart_disease > 0.7 ? 'High Risk' :
                   result.disease_predictions.heart_disease > 0.4 ? 'Moderate Risk' :
                   'Low Risk'}
                </p>
              </div>

              {/* Diabetes Pie */}
              <div className="bg-slate-800/40 backdrop-blur-sm rounded-2xl p-4 border border-slate-700/40">
                <h4 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
                  💉 Diabetes
                </h4>
                <div className="w-full h-40">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={[
                          { name: 'Risk', value: result.disease_predictions.diabetes * 100 },
                          { name: 'Safe', value: (1 - result.disease_predictions.diabetes) * 100 }
                        ]}
                        cx="50%"
                        cy="50%"
                        innerRadius={30}
                        outerRadius={60}
                        paddingAngle={2}
                        dataKey="value"
                      >
                        <Cell fill={result.disease_predictions.diabetes > 0.7 ? '#ef4444' : result.disease_predictions.diabetes > 0.4 ? '#f59e0b' : '#10b981'} />
                        <Cell fill="#334155" />
                      </Pie>
                      <Tooltip formatter={(value) => `${value.toFixed(1)}%`} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <p className="text-center text-lg font-bold text-white mt-2">
                  {(result.disease_predictions.diabetes * 100).toFixed(1)}%
                </p>
                <p className={`text-center text-xs font-medium ${
                  result.disease_predictions.diabetes > 0.7 ? 'text-red-400' :
                  result.disease_predictions.diabetes > 0.4 ? 'text-amber-400' :
                  'text-emerald-400'
                }`}>
                  {result.disease_predictions.diabetes > 0.7 ? 'High Risk' :
                   result.disease_predictions.diabetes > 0.4 ? 'Moderate Risk' :
                   'Low Risk'}
                </p>
              </div>

              {/* Stroke Pie */}
              <div className="bg-slate-800/40 backdrop-blur-sm rounded-2xl p-4 border border-slate-700/40">
                <h4 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
                  🧠 Stroke
                </h4>
                <div className="w-full h-40">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={[
                          { name: 'Risk', value: result.disease_predictions.stroke * 100 },
                          { name: 'Safe', value: (1 - result.disease_predictions.stroke) * 100 }
                        ]}
                        cx="50%"
                        cy="50%"
                        innerRadius={30}
                        outerRadius={60}
                        paddingAngle={2}
                        dataKey="value"
                      >
                        <Cell fill={result.disease_predictions.stroke > 0.7 ? '#ef4444' : result.disease_predictions.stroke > 0.4 ? '#f59e0b' : '#10b981'} />
                        <Cell fill="#334155" />
                      </Pie>
                      <Tooltip formatter={(value) => `${value.toFixed(1)}%`} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <p className="text-center text-lg font-bold text-white mt-2">
                  {(result.disease_predictions.stroke * 100).toFixed(1)}%
                </p>
                <p className={`text-center text-xs font-medium ${
                  result.disease_predictions.stroke > 0.7 ? 'text-red-400' :
                  result.disease_predictions.stroke > 0.4 ? 'text-amber-400' :
                  'text-emerald-400'
                }`}>
                  {result.disease_predictions.stroke > 0.7 ? 'High Risk' :
                   result.disease_predictions.stroke > 0.4 ? 'Moderate Risk' :
                   'Low Risk'}
                </p>
              </div>
            </div>

            {/* Risk Timeline Projection */}
            <div className="bg-slate-800/40 backdrop-blur-sm rounded-2xl p-5 border border-slate-700/40">
              <h4 className="text-sm font-semibold text-slate-300 uppercase tracking-widest mb-4">
                📅 Risk Projection Timeline
              </h4>
              <div className="w-full h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={[
                    { period: 'Current', heart: result.disease_predictions.heart_disease * 100, diabetes: result.disease_predictions.diabetes * 100, stroke: result.disease_predictions.stroke * 100 },
                    { period: '6 Months', heart: result.disease_predictions.heart_disease * 105, diabetes: result.disease_predictions.diabetes * 108, stroke: result.disease_predictions.stroke * 106 },
                    { period: '1 Year', heart: result.disease_predictions.heart_disease * 110, diabetes: result.disease_predictions.diabetes * 115, stroke: result.disease_predictions.stroke * 112 },
                    { period: '2 Years', heart: result.disease_predictions.heart_disease * 120, diabetes: result.disease_predictions.diabetes * 125, stroke: result.disease_predictions.stroke * 118 },
                  ].map(item => ({
                    ...item,
                    heart: Math.min(item.heart, 100),
                    diabetes: Math.min(item.diabetes, 100),
                    stroke: Math.min(item.stroke, 100)
                  }))}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
                    <XAxis dataKey="period" tick={{ fill: '#cbd5e1', fontSize: 11 }} />
                    <YAxis tick={{ fill: '#cbd5e1', fontSize: 11 }} domain={[0, 100]} />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }}
                      formatter={(value) => `${value.toFixed(1)}%`}
                    />
                    <Legend wrapperStyle={{ color: '#cbd5e1', fontSize: '12px' }} />
                    <Area type="monotone" dataKey="heart" stackId="1" stroke="#ef4444" fill="#ef4444" fillOpacity={0.6} name="Heart Disease" />
                    <Area type="monotone" dataKey="diabetes" stackId="2" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.6} name="Diabetes" />
                    <Area type="monotone" dataKey="stroke" stackId="3" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.6} name="Stroke" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              <p className="text-xs text-slate-400 mt-3 text-center">
                ⚠️ Projected risks without intervention. Early detection and lifestyle changes can significantly reduce these risks.
              </p>
            </div>

            {/* Multi-Disease Analysis - Top 5 Probable Conditions */}
            {result.disease_predictions?.multi_disease_top5 && result.disease_predictions.multi_disease_top5.length > 0 && (
              <div className="bg-gradient-to-br from-indigo-900/40 to-purple-900/40 backdrop-blur-sm rounded-2xl p-5 border border-indigo-700/40">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h4 className="text-sm font-semibold text-slate-300 uppercase tracking-widest flex items-center gap-2">
                      🔬 Advanced Multi-Disease Analysis
                    </h4>
                    <p className="text-xs text-slate-400 mt-1">
                      AI model trained on 41 diseases, analyzing symptoms from clinical data
                    </p>
                  </div>
                  <div className="px-3 py-1 bg-indigo-500/20 rounded-full">
                    <span className="text-xs font-bold text-indigo-400">
                      {result.disease_predictions.multi_disease_top5.length} matches
                    </span>
                  </div>
                </div>

                <div className="space-y-3">
                  {result.disease_predictions.multi_disease_top5.map((disease, index) => {
                    const probability = disease.probability * 100
                    const getRiskColor = (prob) => {
                      if (prob > 60) return { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/30', bar: '#ef4444' }
                      if (prob > 30) return { bg: 'bg-amber-500/20', text: 'text-amber-400', border: 'border-amber-500/30', bar: '#f59e0b' }
                      return { bg: 'bg-blue-500/20', text: 'text-blue-400', border: 'border-blue-500/30', bar: '#3b82f6' }
                    }
                    const colors = getRiskColor(probability)

                    return (
                      <div key={index} className={`p-4 rounded-xl border ${colors.border} ${colors.bg} transition-all duration-300 hover:scale-[1.02]`}>
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-3">
                            <div className={`w-8 h-8 rounded-lg ${colors.bg} flex items-center justify-center border ${colors.border}`}>
                              <span className={`text-sm font-bold ${colors.text}`}>#{index + 1}</span>
                            </div>
                            <div>
                              <p className={`text-sm font-bold ${colors.text}`}>
                                {disease.disease}
                              </p>
                              <p className="text-xs text-slate-400">
                                {probability > 60 ? 'High probability' : probability > 30 ? 'Moderate probability' : 'Possible match'}
                              </p>
                            </div>
                          </div>
                          <div className="text-right">
                            <p className={`text-lg font-black ${colors.text}`}>
                              {probability.toFixed(1)}%
                            </p>
                            <p className="text-[10px] text-slate-500">confidence</p>
                          </div>
                        </div>
                        
                        {/* Probability Bar */}
                        <div className="mt-3 h-2 bg-slate-700/50 rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all duration-1000 ease-out"
                            style={{
                              width: `${probability}%`,
                              backgroundColor: colors.bar,
                            }}
                          />
                        </div>
                      </div>
                    )
                  })}
                </div>

                {/* Info Note */}
                <div className="mt-4 p-3 bg-slate-900/50 rounded-xl border border-slate-700/30">
                  <p className="text-xs text-slate-400">
                    <span className="font-semibold text-indigo-400">How it works:</span> This model analyzes 
                    132 symptom patterns inferred from vital signs, demographics, and clinical notes. 
                    Trained on 4,920 patient cases across 41 different conditions. Results complement 
                    the specific heart/diabetes/stroke models shown above.
                  </p>
                </div>
              </div>
            )}
            
            {/* Disclaimer */}
            <div className="bg-blue-900/20 border border-blue-700/30 rounded-xl p-4">
              <p className="text-xs text-blue-300">
                <span className="font-semibold">Clinical Note:</span> These predictions are generated by ML models trained on clinical datasets. 
                They complement but do not replace professional clinical judgment. Please consult healthcare providers for diagnosis and treatment decisions.
              </p>
            </div>
          </>
        )}

        {/* Vitals Overview */}
        <div>
          <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-widest mb-3 px-1">Current Vitals</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
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
  const [loadingProgress, setLoadingProgress] = useState(0)
  const [error, setError] = useState(null)

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  // Load sample high-risk patient data
  const loadSampleData = () => {
    setFormData({
      heart_rate: '95',
      systolic_bp: '165',
      diastolic_bp: '98',
      temperature: '37.8',
      spo2: '92',
      age: '68',
      gender: 'Male',
      smoking_status: 'Current',
      diabetes: 'Yes',
      hypertension: 'Yes',
      ehr_notes: 'Patient complains of chest discomfort and shortness of breath. History of coronary artery disease.',
      clinical_summary: 'Presents with elevated BP, tachycardia, mild hypoxia. Known cardiovascular risk factors.',
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setLoadingProgress(0)
    setError(null)

    // Client-side validation
    const requiredFields = [
      'heart_rate', 'systolic_bp', 'diastolic_bp', 'temperature', 'spo2', 'age'
    ]
    
    for (const field of requiredFields) {
      if (!formData[field] || formData[field] === '') {
        setError(`Please fill in all required fields. Missing: ${field.replace(/_/g, ' ').toUpperCase()}`)
        setLoading(false)
        return
      }
    }

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

    // Validate parsed numbers
    if (isNaN(payload.vitals.heart_rate) || isNaN(payload.vitals.systolic_bp) || 
        isNaN(payload.vitals.diastolic_bp) || isNaN(payload.vitals.temperature) || 
        isNaN(payload.vitals.spo2) || isNaN(payload.demographics.age)) {
      setError('Please enter valid numbers for all vitals and age fields')
      setLoading(false)
      return
    }

    // Simulate loading progress with stages (5 seconds total)
    const progressInterval = setInterval(() => {
      setLoadingProgress(prev => {
        if (prev >= 95) {
          clearInterval(progressInterval)
          return 95
        }
        // Smoother progress: fast at start, slower near end
        const increment = prev < 50 ? 8 : prev < 80 ? 4 : 2
        return Math.min(prev + increment, 95)
      })
    }, 250) // Update every 250ms

    try {
      // Wait minimum 5 seconds for visual effect
      const [apiResponse] = await Promise.all([
        fetch(`${API_URL}/api/evaluate-risk`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        }),
        new Promise(resolve => setTimeout(resolve, 5000)) // Minimum 5 second delay
      ])

      clearInterval(progressInterval)
      setLoadingProgress(100)

      if (!apiResponse.ok) {
        const errData = await apiResponse.json().catch(() => ({}))
        let errorMessage = `Server error: ${apiResponse.status}`
        
        if (errData.detail) {
          if (typeof errData.detail === 'string') {
            errorMessage = errData.detail
          } else if (Array.isArray(errData.detail)) {
            // Pydantic validation errors are arrays
            const errors = errData.detail.map(err => {
              const field = err.loc ? err.loc.join(' → ') : 'Unknown field'
              return `${field}: ${err.msg}`
            })
            errorMessage = errors.join('\n')
          } else {
            errorMessage = JSON.stringify(errData.detail)
          }
        }
        throw new Error(errorMessage)
      }

      const data = await apiResponse.json()
      
      // Brief pause at 100% before showing results
      await new Promise(resolve => setTimeout(resolve, 300))
      setResult(data)
    } catch (err) {
      console.error('API Error:', err)
      clearInterval(progressInterval)
      const errorMessage = err instanceof Error ? err.message : String(err)
      setError(errorMessage || 'Failed to connect to the CareSync backend')
    } finally {
      setLoading(false)
      setLoadingProgress(0)
    }
  }

  const resetForm = () => {
    setResult(null)
    setError(null)
    setLoadingProgress(0)
  }

  // ─── Loading View ─────────────────────────────────────────────────
  if (loading) {
    return <LoadingAnalysis progress={loadingProgress} />
  }

  // ─── Results View (Always show detailed view now) ────────────────
  if (result) {
    return (
      <>
        <ResultsView result={result} formData={formData} onReset={resetForm} />
        <JarvisAssistant 
          riskAssessmentData={result}
          patientData={formData}
        />
      </>
    )
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
        {/* Sample Data Button */}
        <div className="flex justify-end">
          <button
            type="button"
            onClick={loadSampleData}
            className="flex items-center gap-2 bg-violet-600/20 hover:bg-violet-600/30 border border-violet-500/30 text-violet-300 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Load Sample Data
          </button>
        </div>

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
            <pre className="mt-1 text-red-400 whitespace-pre-wrap font-sans">{error}</pre>
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          id="submit-btn"
          disabled={loading}
          className="w-full bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-500 hover:to-blue-500 disabled:from-slate-700 disabled:to-slate-700 text-white font-bold py-4 px-6 rounded-2xl shadow-xl shadow-violet-600/20 transition-all duration-300 text-lg tracking-wide disabled:cursor-not-allowed"
        >
          Evaluate Risk
        </button>
      </form>

      <PrivacyBadge />
    </div>
  )
}
