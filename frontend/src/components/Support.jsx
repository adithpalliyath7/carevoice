import { useState } from 'react'
import { api } from '../lib/api.js'

// AI Receptionist: greeting, routing, process questions, glossary,
// prepare-for-visit, post-visit (doctor notes only), escalation.
// Safety banner on every screen: no diagnosis, no treatment advice.
const SAFETY = 'CareVoice explains processes — it does not diagnose or give treatment advice. For medical concerns, contact a qualified professional.'

export default function Support({ language, seniorMode, onEmergency }) {
  const [q, setQ] = useState('')
  const [answer, setAnswer] = useState(null)
  const [term, setTerm] = useState('')
  const [glossary, setGlossary] = useState(null)
  const [prep, setPrep] = useState(null)
  const [token, setToken] = useState('')
  const [postVisit, setPostVisit] = useState(null)
  const [esc, setEsc] = useState(null)
  const [severity, setSeverity] = useState('routine')
  const [concern, setConcern] = useState('')
  const [error, setError] = useState('')

  const ask = async (text) => {
    try { setAnswer(await api.supportAsk(text || q, language)) } catch (e) { setError(e.message) }
  }
  const askVoice = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const rec = new MediaRecorder(stream)
      const chunks = []
      rec.ondataavailable = (e) => chunks.push(e.data)
      rec.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop())
        const res = await api.transcribe(new Blob(chunks, { type: 'audio/webm' }), `${language}-IN`)
        setQ(res.transcript); ask(res.transcript)
      }
      rec.start(); setTimeout(() => rec.stop(), 8000)
    } catch { setError('Microphone unavailable — please type your question.') }
  }

  return (
    <div className="grid gap-4">
      <div className="rounded-2xl border-2 border-amber-300 bg-amber-50 p-4 text-sm font-medium text-amber-900">⚠️ {SAFETY}</div>
      <div className="card rounded-2xl border bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-[#0A2540]">👋 AI Receptionist — ask in simple language</h2>
        <p className="text-sm text-slate-500">I can explain how booking, tokens, reports and billing work. I cannot diagnose or advise treatment.</p>
        <div className="mt-3 flex gap-2">
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. How do I book? What should I bring?" className="flex-1 rounded-xl border px-3 py-2" />
          <button onClick={() => ask()} className="rounded-xl bg-[#015BBB] px-4 py-2 text-white">Ask</button>
          <button onClick={askVoice} className="rounded-xl border px-4 py-2">🎙️ Voice</button>
        </div>
        {answer && (
          <div className="mt-3 rounded-xl bg-blue-50 p-4 text-sm">
            {answer.status === 'answered' ? <p>{answer.answer}</p> : (
              <><p><b>Not covered by CareVoice.</b> {answer.message}</p>
              <p className="mt-2 font-semibold">Questions to ask your doctor:</p>
              <ul className="list-disc pl-5">{answer.questions_to_ask.map((x) => <li key={x}>{x}</li>)}</ul></>)}
          </div>
        )}
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      </div>
      <div className="card rounded-2xl border bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-[#0A2540]">📖 Medical terms, simply explained</h2>
        <form className="mt-2 flex gap-2" onSubmit={async (e) => { e.preventDefault(); setGlossary(await api.glossary(term, language)) }}>
          <input value={term} onChange={(e) => setTerm(e.target.value)} placeholder="e.g. BP, ECG, prescription" className="flex-1 rounded-xl border px-3 py-2" />
          <button className="rounded-xl bg-[#0A2540] px-4 py-2 text-white">Look up</button>
        </form>
        {glossary && Object.entries(glossary.results).map(([k, v]) => <p key={k} className="mt-2 text-sm"><b>{k}:</b> {v}</p>)}
      </div>
      <div className="card rounded-2xl border bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-[#0A2540]">🧳 Prepare for my visit</h2>
        <form className="mt-2 flex gap-2" onSubmit={async (e) => { e.preventDefault(); setPrep(await api.prepareVisit({ speciality: e.target.spec.value })) }}>
          <input name="spec" placeholder="Speciality, e.g. cardiology" className="flex-1 rounded-xl border px-3 py-2" />
          <button className="rounded-xl bg-[#0A2540] px-4 py-2 text-white">Get checklist</button>
        </form>
        {prep && <><ul className="mt-3 list-disc pl-5 text-sm">{prep.prep_checklist.map((x) => <li key={x}>{x}</li>)}</ul>
        <p className="mt-2 text-sm font-semibold">Questions to ask the doctor:</p>
        <ul className="list-disc pl-5 text-sm">{prep.questions_to_ask.map((x) => <li key={x}>{x}</li>)}</ul>
        <p className="mt-2 text-xs text-slate-500">{prep.label}</p></>}
      </div>
      <div className="card rounded-2xl border bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-[#0A2540]">📋 Post-visit instructions</h2>
        <form className="mt-2 flex gap-2" onSubmit={async (e) => { e.preventDefault(); setPostVisit(await api.postVisit(token)) }}>
          <input value={token} onChange={(e) => setToken(e.target.value)} placeholder="Appointment token" className="flex-1 rounded-xl border px-3 py-2" />
          <button className="rounded-xl bg-[#0A2540] px-4 py-2 text-white">View</button>
        </form>
        {postVisit && <p className="mt-3 rounded-xl bg-slate-50 p-3 text-sm">{postVisit.status === 'on_file' ? postVisit.instructions : postVisit.note}</p>}
      </div>
      <div className="card rounded-2xl border bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-[#0A2540]">😟 I'm worried — escalate</h2>
        <div className="mt-2 flex flex-wrap gap-2">
          {['routine', 'urgent', 'emergency'].map((s) => (
            <button key={s} onClick={() => setSeverity(s)} className={`rounded-full px-4 py-2 ${severity === s ? (s === 'emergency' ? 'bg-red-600 text-white' : 'bg-[#015BBB] text-white') : 'border'}`}>{s}</button>
          ))}
        </div>
        <div className="mt-3 flex gap-2">
          <input value={concern} onChange={(e) => setConcern(e.target.value)} placeholder="Describe your concern briefly" className="flex-1 rounded-xl border px-3 py-2" />
          <button onClick={async () => { const r = await api.escalate({ concern, severity, language }); setEsc(r); if (r.severity === 'emergency') onEmergency && onEmergency() }} className="rounded-xl bg-[#0A2540] px-4 py-2 text-white">Send</button>
        </div>
        {esc && <p className="mt-3 rounded-xl bg-blue-50 p-3 text-sm">Reference <b>{esc.reference_id}</b> · {esc.next_step}</p>}
        <button onClick={onEmergency} className="mt-4 w-full rounded-2xl bg-red-600 px-5 py-4 text-xl font-bold text-white">🚨 Emergency — press for help</button>
      </div>
    </div>
  )
}
