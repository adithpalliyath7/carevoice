import { useRef, useState } from 'react'
import { api } from '../lib/api.js'

// Voice input: MediaRecorder -> Prisma STT -> rule-based converse.
// Repeat / pause / slow-down controls for Timbre playback; language can be
// switched mid-conversation; unclear speech asks the user to repeat.
export default function VoiceAssistant({ language, setLanguage, languages, seniorMode, onEmergency, onTranscript }) {
  const [recording, setRecording] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [reply, setReply] = useState('')
  const [history, setHistory] = useState([])
  const [error, setError] = useState('')
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(1.0)
  const mediaRef = useRef(null)
  const audioRef = useRef(null)
  const chunksRef = useRef([])

  const playText = async (text, slow = false) => {
    try {
      const blob = await api.speak({ text, language, speed: slow ? 0.85 : speed, senior_mode: seniorMode })
      const url = URL.createObjectURL(blob)
      if (audioRef.current) audioRef.current.pause()
      const a = new Audio(url)
      audioRef.current = a
      setPlaying(true)
      a.onended = () => setPlaying(false)
      a.play()
    } catch (e) {
      setError(e.code === 'gnani_not_configured'
        ? 'Voice replies are unavailable: Gnani API key is not configured on the server.'
        : `Speech failed: ${e.message}`)
    }
  }

  const handleTranscript = async (text) => {
    setTranscript(text)
    onTranscript && onTranscript(text)
    try {
      const res = await api.converse(text, language, {}, seniorMode)
      if (res.emergency) { onEmergency && onEmergency(res); return }
      setReply(res.reply_text || '')
      setHistory((h) => [...h, { you: text, ai: res.reply_text || '' }])
      if (res.reply_text) playText(res.reply_text, seniorMode)
    } catch (e) {
      setError(`Could not understand that: ${e.message}`)
    }
  }

  const toggleRecord = async () => {
    if (recording) {
      mediaRef.current?.stop()
      setRecording(false)
      return
    }
    setError('')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const rec = new MediaRecorder(stream)
      chunksRef.current = []
      rec.ondataavailable = (e) => chunksRef.current.push(e.data)
      rec.onstop = async () => {
        stream.getTracks().forEach((tr) => tr.stop())
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        try {
          const sttLang = language === 'auto' ? 'indic-auto' : `${language}-IN`
          const result = await api.transcribe(blob, sttLang)
          handleTranscript(result.transcript)
        } catch (e) {
          setError(e.code === 'gnani_not_configured'
            ? 'Transcription unavailable: Gnani API key is not configured on the server.'
            : `Transcription failed: ${e.message}`)
        }
      }
      mediaRef.current = rec
      rec.start()
      setRecording(true)
      // Senior mode: no recording timeout. Otherwise cap at 30 s (Prisma limit).
      if (!seniorMode) setTimeout(() => { if (rec.state === 'recording') { rec.stop(); setRecording(false) } }, 30000)
    } catch {
      setError('Microphone access was denied. You can type instead.')
    }
  }

  const pauseAudio = () => { audioRef.current?.pause(); setPlaying(false) }

  return (
    <div className="card rounded-2xl border bg-white p-5 shadow-sm">
      <h2 className="text-lg font-semibold text-[#0A2540]">🎙️ AI Receptionist — speak naturally</h2>
      <p className="text-sm text-slate-500">Malayalam, Hindi, Tamil, Telugu, Kannada, Bengali, English — including code-mixed speech. Switch language any time.</p>
      <div className="mt-3 flex flex-wrap gap-2">
        <select value={language} onChange={(e) => setLanguage(e.target.value)} className="rounded-xl border px-3 py-2" aria-label="Language">
          {(languages || []).map((l) => <option key={l.code} value={l.code}>{l.native} ({l.name})</option>)}
          <option value="auto">Auto / Code-mix</option>
        </select>
        <button onClick={toggleRecord} className={`rounded-full px-5 py-2 font-semibold text-white ${recording ? 'bg-red-600 animate-pulse' : 'bg-[#015BBB]'}`}>
          {recording ? '● Stop & send' : '🎙️ Tap to speak'}
        </button>
        <button onClick={() => reply && playText(reply)} className="rounded-full border px-4 py-2">🔁 Repeat</button>
        <button onClick={() => reply && playText(reply, true)} className="rounded-full border px-4 py-2">🐢 Slower (0.85×)</button>
        {playing && <button onClick={pauseAudio} className="rounded-full border px-4 py-2">⏸ Pause</button>}
      </div>
      <form className="mt-3 flex gap-2" onSubmit={(e) => { e.preventDefault(); const v = e.target.text.value.trim(); if (v) { handleTranscript(v); e.target.reset() } }}>
        <input name="text" placeholder="Or type here — e.g. 'book cardiology tomorrow 10 am'" className="flex-1 rounded-xl border px-3 py-2" />
        <button className="rounded-xl bg-[#0A2540] px-4 py-2 text-white">Send</button>
      </form>
      {error && <p className="mt-3 rounded-xl bg-amber-50 p-3 text-sm text-amber-800">{error}</p>}
      {transcript && <p className="mt-3 text-sm"><b>You:</b> {transcript}</p>}
      {reply && <p className="mt-1 text-sm"><b>CareVoice:</b> {reply}</p>}
      {history.length > 0 && (
        <details className="mt-3 text-sm text-slate-600">
          <summary>Conversation history ({history.length})</summary>
          {history.map((h, i) => <p key={i} className="mt-1">🧑 {h.you}<br />🤖 {h.ai}</p>)}
        </details>
      )}
    </div>
  )
}
