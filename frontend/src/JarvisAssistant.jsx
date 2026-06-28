import { useState, useEffect, useRef, useCallback } from 'react';

const API_URL = 'http://localhost:8000';

function buildContextData(riskAssessmentData, patientData) {
  const vitals = patientData?.vitals ?? {
    heart_rate: parseFloat(patientData?.heart_rate),
    systolic_bp: parseFloat(patientData?.systolic_bp),
    diastolic_bp: parseFloat(patientData?.diastolic_bp),
    temperature: parseFloat(patientData?.temperature),
    spo2: parseFloat(patientData?.spo2),
  };

  const demographics = patientData?.demographics ?? {
    age: parseInt(patientData?.age, 10),
    gender: patientData?.gender,
    smoking_status: patientData?.smoking_status,
    diabetes: patientData?.diabetes,
    hypertension: patientData?.hypertension,
  };

  return {
    risk_level: riskAssessmentData?.risk_level,
    risk_score: riskAssessmentData?.risk_score,
    vitals,
    demographics,
    disease_predictions: riskAssessmentData?.disease_predictions,
    clinical_conditions: riskAssessmentData?.clinical_conditions,
  };
}

export default function JarvisAssistant({ riskAssessmentData, patientData }) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [textInput, setTextInput] = useState('');
  const [connectionStatus, setConnectionStatus] = useState('idle'); // idle | connecting | connected | error
  const [voiceStatus, setVoiceStatus] = useState('ready'); // ready | listening | thinking | speaking
  const [error, setError] = useState(null);
  const [showDisclaimer, setShowDisclaimer] = useState(true);

  const pcRef = useRef(null);
  const dcRef = useRef(null);
  const audioElRef = useRef(null);
  const micStreamRef = useRef(null);
  const messagesEndRef = useRef(null);
  const assistantTranscriptRef = useRef('');
  const connectingRef = useRef(false);

  const addMessage = useCallback((role, content) => {
    if (!content?.trim()) return;
    setMessages((prev) => [
      ...prev,
      { role, content: content.trim(), timestamp: new Date().toISOString() },
    ]);
  }, []);

  const disconnect = useCallback(() => {
    connectingRef.current = false;
    assistantTranscriptRef.current = '';

    if (dcRef.current) {
      try { dcRef.current.close(); } catch (_) { /* noop */ }
      dcRef.current = null;
    }
    if (pcRef.current) {
      try { pcRef.current.close(); } catch (_) { /* noop */ }
      pcRef.current = null;
    }
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach((t) => t.stop());
      micStreamRef.current = null;
    }
    if (audioElRef.current) {
      audioElRef.current.srcObject = null;
    }

    setConnectionStatus('idle');
    setVoiceStatus('ready');
  }, []);

  const handleServerEvent = useCallback((event) => {
    switch (event.type) {
      case 'session.created':
      case 'session.updated':
        setConnectionStatus('connected');
        setVoiceStatus('ready');
        break;

      case 'input_audio_buffer.speech_started':
        setVoiceStatus('listening');
        break;

      case 'input_audio_buffer.speech_stopped':
        setVoiceStatus('thinking');
        break;

      case 'response.created':
        assistantTranscriptRef.current = '';
        setVoiceStatus('speaking');
        break;

      case 'response.output_audio_transcript.delta':
        assistantTranscriptRef.current += event.delta || '';
        break;

      case 'response.output_audio_transcript.done':
        if (event.transcript) {
          addMessage('assistant', event.transcript);
        } else if (assistantTranscriptRef.current) {
          addMessage('assistant', assistantTranscriptRef.current);
        }
        assistantTranscriptRef.current = '';
        break;

      case 'conversation.item.input_audio_transcription.completed':
        if (event.transcript) {
          addMessage('user', event.transcript);
        }
        break;

      case 'response.done':
        setVoiceStatus('ready');
        break;

      case 'error':
        console.error('JARVIS Realtime error:', event);
        setError(event.error?.message || 'Voice session error');
        break;

      default:
        break;
    }
  }, [addMessage]);

  const connectRealtime = useCallback(async () => {
    if (connectingRef.current || pcRef.current) return;
    connectingRef.current = true;
    setConnectionStatus('connecting');
    setError(null);

    try {
      const micStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      micStreamRef.current = micStream;

      const pc = new RTCPeerConnection();
      pcRef.current = pc;

      if (!audioElRef.current) {
        audioElRef.current = document.createElement('audio');
        audioElRef.current.autoplay = true;
      }

      pc.ontrack = (e) => {
        if (audioElRef.current) {
          audioElRef.current.srcObject = e.streams[0];
        }
      };

      micStream.getTracks().forEach((track) => pc.addTrack(track, micStream));

      const dc = pc.createDataChannel('oai-events');
      dcRef.current = dc;

      dc.addEventListener('open', () => {
        setConnectionStatus('connected');
        setVoiceStatus('ready');
      });

      dc.addEventListener('message', (e) => {
        try {
          handleServerEvent(JSON.parse(e.data));
        } catch (err) {
          console.error('Failed to parse Realtime event:', err);
        }
      });

      dc.addEventListener('close', () => {
        setConnectionStatus('idle');
      });

      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      const contextData = buildContextData(riskAssessmentData, patientData);

      const response = await fetch(`${API_URL}/api/jarvis/realtime-session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sdp: offer.sdp,
          risk_assessment_context: contextData,
        }),
      });

      if (!response.ok) {
        const errText = await response.text();
        throw new Error(errText || 'Failed to start voice session');
      }

      const answerSdp = await response.text();
      await pc.setRemoteDescription({ type: 'answer', sdp: answerSdp });

      setConnectionStatus('connected');
      setVoiceStatus('ready');
    } catch (err) {
      console.error('JARVIS Realtime connect error:', err);
      setError(err.message || 'Could not connect to JARVIS voice');
      setConnectionStatus('error');
      disconnect();
    } finally {
      connectingRef.current = false;
    }
  }, [riskAssessmentData, patientData, handleServerEvent, disconnect]);

  const sendTextMessage = useCallback((text) => {
    const message = text?.trim();
    if (!message || !dcRef.current || dcRef.current.readyState !== 'open') return;

    addMessage('user', message);
    setTextInput('');
    setVoiceStatus('thinking');

    dcRef.current.send(JSON.stringify({
      type: 'conversation.item.create',
      item: {
        type: 'message',
        role: 'user',
        content: [{ type: 'input_text', text: message }],
      },
    }));
    dcRef.current.send(JSON.stringify({ type: 'response.create' }));
  }, [addMessage]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, voiceStatus]);

  useEffect(() => {
    if (isOpen) {
      connectRealtime();
    } else {
      disconnect();
    }
    return () => disconnect();
  }, [isOpen]); // eslint-disable-line react-hooks/exhaustive-deps

  const statusLabel = {
    idle: 'Offline',
    connecting: 'Connecting…',
    connected: {
      ready: '🎙️ Speak naturally',
      listening: 'Listening…',
      thinking: 'Thinking…',
      speaking: 'JARVIS speaking…',
    },
    error: 'Connection error',
  };

  const liveLabel = connectionStatus === 'connected'
    ? statusLabel.connected[voiceStatus]
    : statusLabel[connectionStatus];

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white rounded-full p-4 shadow-2xl transition-all duration-300 hover:scale-110 z-50 group"
        title="Talk to JARVIS"
      >
        <div className="relative">
          <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
          </svg>
          <span className="absolute -top-1 -right-1 w-3 h-3 bg-green-400 rounded-full animate-pulse" />
        </div>
        <span className="absolute bottom-full right-0 mb-2 px-3 py-1 bg-slate-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
          Talk to JARVIS
        </span>
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 w-96 h-[600px] bg-slate-900 rounded-2xl shadow-2xl border border-slate-700 z-50 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-cyan-600 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            {connectionStatus === 'connected' && (
              <span className={`absolute -top-1 -right-1 w-3 h-3 rounded-full ${
                voiceStatus === 'speaking' ? 'bg-green-400 animate-pulse' :
                voiceStatus === 'listening' ? 'bg-red-400 animate-pulse' :
                'bg-emerald-400'
              }`} />
            )}
          </div>
          <div>
            <h3 className="text-white font-bold text-lg">JARVIS</h3>
            <p className="text-white/70 text-xs">AI Medical Assistant</p>
          </div>
        </div>
        <button
          onClick={() => {
            disconnect();
            setIsOpen(false);
          }}
          className="text-white/70 hover:text-white transition-colors"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* One-time visible disclaimer only */}
      {showDisclaimer && (
        <div className="bg-amber-900/30 border-b border-amber-700/50 px-4 py-2 text-xs text-amber-300">
          <div className="flex items-start gap-2">
            <span className="text-base">⚠️</span>
            <div className="flex-1">
              <p className="text-amber-200/80">
                JARVIS is an AI assistant for educational purposes only. Always consult qualified medical professionals for health decisions.
              </p>
            </div>
            <button onClick={() => setShowDisclaimer(false)} className="text-amber-400 hover:text-amber-300">✕</button>
          </div>
        </div>
      )}

      {/* Live status bar */}
      <div className="px-4 py-2 bg-slate-950/80 border-b border-slate-800 flex items-center justify-between">
        <span className={`text-xs font-medium ${
          connectionStatus === 'connected' ? 'text-emerald-400' :
          connectionStatus === 'error' ? 'text-red-400' :
          'text-slate-400'
        }`}>
          {liveLabel}
        </span>
        {connectionStatus === 'connected' && (
          <span className="text-[10px] text-slate-500 uppercase tracking-wider">Continuous · Alloy voice</span>
        )}
      </div>

      {error && (
        <div className="px-4 py-2 bg-red-900/40 border-b border-red-800 text-xs text-red-300">
          {error}
          <button
            onClick={() => { setError(null); connectRealtime(); }}
            className="ml-2 underline hover:text-red-200"
          >
            Retry
          </button>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-slate-950">
        {messages.length === 0 && connectionStatus === 'connected' && (
          <div className="text-center py-8 text-slate-500 text-sm">
            <p className="mb-2">Voice session active</p>
            <p className="text-xs">Just start talking — JARVIS hears you automatically</p>
          </div>
        )}
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] rounded-2xl px-4 py-2 ${
              msg.role === 'user'
                ? 'bg-blue-600 text-white'
                : 'bg-slate-800 text-slate-200 border border-slate-700'
            }`}>
              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
              <p className="text-xs opacity-60 mt-1">{new Date(msg.timestamp).toLocaleTimeString()}</p>
            </div>
          </div>
        ))}
        {(voiceStatus === 'thinking' || voiceStatus === 'speaking') && (
          <div className="flex justify-start">
            <div className="bg-slate-800 rounded-2xl px-4 py-3 border border-slate-700">
              <div className="flex gap-1.5 items-center">
                <div className="w-1.5 h-4 bg-blue-400 rounded-full animate-pulse" style={{ animationDelay: '0ms' }} />
                <div className="w-1.5 h-6 bg-blue-400 rounded-full animate-pulse" style={{ animationDelay: '150ms' }} />
                <div className="w-1.5 h-3 bg-blue-400 rounded-full animate-pulse" style={{ animationDelay: '300ms' }} />
                <span className="text-xs text-slate-400 ml-2">{voiceStatus === 'speaking' ? 'Speaking…' : 'Processing…'}</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Text fallback input */}
      <div className="border-t border-slate-700 bg-slate-900 p-4">
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendTextMessage(textInput)}
            placeholder={connectionStatus === 'connected' ? 'Or type a question…' : 'Connecting voice…'}
            disabled={connectionStatus !== 'connected'}
            className="flex-1 bg-slate-800 text-white px-4 py-2 rounded-xl border border-slate-700 focus:outline-none focus:border-blue-500 text-sm disabled:opacity-50"
          />
          <button
            onClick={() => sendTextMessage(textInput)}
            disabled={!textInput.trim() || connectionStatus !== 'connected'}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 disabled:cursor-not-allowed text-white p-2 rounded-xl transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
        <p className="text-[10px] text-slate-500 mt-2 text-center">
          Powered by OpenAI GPT-4o Realtime · Natural conversation
        </p>
      </div>
    </div>
  );
}
