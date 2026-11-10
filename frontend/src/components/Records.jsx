import { useEffect, useState } from 'react'
import { api } from '../lib/api.js'

// Records: upload (drag/drop + picker), list grouped by date with doctor/kind
// filters, detail with OCR-unverified label, voice search, 24h share link,
// reminders. Never presents OCR text as verified medical data.
export default function Records({ language }) {
  const [records, setRecords] = useState([])
  const [kind, setKind] = useState('')
  const [doctor, setDoctor] = useState('')
  const [selected, setSelected] = useState(null)
  const [share, setShare] = useState('')
  const [reminders, setReminders] = useState([])
  const [msg, setMsg] = useState('')
  const [phone, setPhone] = useState('')

  const load = async () => {
    const r = await api.records({ kind: kind || undefined, doctor: doctor || undefined })
    setRecords(r.records)
    setReminders((await api.reminders()).reminders)
  }
  useEffect(() => { load() }, [kind, doctor])

  const upload = async (file) => {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('kind', document.getElementById('rec-kind').value)
    fd.append('doctor_name', document.getElementById('rec-doctor').value)
    fd.append('date', document.getElementById('rec-date').value)
    fd.append('patient_name', document.getElementById('rec-patient').value)
    fd.append('patient_phone', phone)
    try { await api.uploadRecord(fd); setMsg('Uploaded. OCR text is unverified — check the original file.'); load() }
    catch (e) { setMsg(`Upload failed: ${e.message}`) }
  }

  const voiceSearch = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const rec = new MediaRecorder(stream); const chunks = []
      rec.ondataavailable = (e) => chunks.push(e.data)
      rec.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop())
        const res = await api.transcribe(new Blob(chunks, { type: 'audio/webm' }), `${language}-IN`)
        const r = await api.recordVoiceSearch(res.transcript)
        setRecords(r.records); setMsg(`Voice search: "${res.transcript}" — ${r.records.length} result(s).`)
      }
      rec.start(); setTimeout(() => rec.stop(), 8000)
    } catch { setMsg('Microphone unavailable.') }
  }

  return (
    <div className="grid gap-4">
      <div className="card rounded-2xl border bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-[#0A2540]">📄 Upload prescription / report</h2>
        <p className="text-sm text-slate-500">PDF, JPG or PNG, up to 10 MB. Demo only — do not upload real patient data.</p>
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          <input id="rec-patient" placeholder="Patient name (optional)" className="rounded-xl border px-3 py-2" />
          <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="Patient phone (for download access)" className="rounded-xl border px-3 py-2" />
          <input id="rec-doctor" placeholder="Doctor name" className="rounded-xl border px-3 py-2" />
          <input id="rec-date" type="date" className="rounded-xl border px-3 py-2" />
          <select id="rec-kind" className="rounded-xl border px-3 py-2">
            <option value="prescription">Prescription</option><option value="lab_report">Lab report</option>
            <option value="scan">Scan</option><option value="discharge">Discharge summary</option><option value="other">Other</option>
          </select>
          <label className="flex cursor-pointer items-center justify-center rounded-xl border-2 border-dashed px-3 py-2 text-[#015BBB]">
            📎 Choose file
            <input type="file" accept=".pdf,.jpg,.jpeg,.png" className="hidden" onChange={(e) => e.target.files[0] && upload(e.target.files[0])} />
          </label>
        </div>
        {msg && <p className="mt-2 text-sm text-slate-600">{msg}</p>}
      </div>
      <div className="card rounded-2xl border bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-lg font-semibold text-[#0A2540]">My records</h2>
          <button onClick={voiceSearch} className="rounded-full border px-3 py-1 text-sm">🎙️ Voice search</button>
          <input value={doctor} onChange={(e) => setDoctor(e.target.value)} placeholder="Filter by doctor" className="rounded-xl border px-3 py-1 text-sm" />
          <select value={kind} onChange={(e) => setKind(e.target.value)} className="rounded-xl border px-3 py-1 text-sm">
            <option value="">All kinds</option><option value="prescription">Prescription</option>
            <option value="lab_report">Lab report</option><option value="scan">Scan</option>
            <option value="discharge">Discharge</option><option value="other">Other</option>
          </select>
        </div>
        {records.length === 0 && <p className="mt-3 text-sm text-slate-500">No records yet.</p>}
        {records.map((r) => (
          <button key={r.id} onClick={() => setSelected(r)} className="mt-2 block w-full rounded-xl border p-3 text-left">
            <p className="font-semibold">{r.filename}</p>
            <p className="text-sm text-slate-500">{r.date} · {r.kind} · {r.doctor_name || '—'} · OCR: {r.ocr_status}</p>
          </button>
        ))}
      </div>
      {selected && (
        <div className="card rounded-2xl border bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold">{selected.filename}</h2>
          <p className="mt-1 rounded-xl bg-amber-50 p-3 text-sm text-amber-800">⚠️ OCR — unverified, check original. Extracted text is not verified medical data.</p>
          {selected.fields?.medicines?.length > 0 && <>
            <p className="mt-3 font-semibold">Medicines found (extracted, unverified):</p>
            <ul className="list-disc pl-5 text-sm">{selected.fields.medicines.map((m, i) => <li key={i}>{m.name} — {m.dosage}</li>)}</ul></>}
          {selected.fields?.dates_found?.length > 0 && <p className="mt-2 text-sm">Dates found: {selected.fields.dates_found.join(', ')}</p>}
          {selected.extracted_text && <details className="mt-2 text-sm"><summary>Extracted text</summary><pre className="whitespace-pre-wrap">{selected.extracted_text}</pre></details>}
          <div className="mt-3 flex flex-wrap gap-2">
            <a className="rounded-full bg-[#015BBB] px-4 py-2 text-white" href={`/api/records/${selected.id}/download`} target="_blank" rel="noreferrer">⬇️ Download</a>
            <button onClick={async () => { const s = await api.shareRecord(selected.id); setShare(`${window.location.origin}${s.url} (expires ${s.expires_at})`); navigator.clipboard?.writeText(`${window.location.origin}${s.url}`) }} className="rounded-full border px-4 py-2">🔗 Share (24h link)</button>
            <button onClick={async () => { const r = await api.createReminder({ record_id: selected.id, type: 'prescription_refill', due_date: new Date(Date.now() + 7 * 864e5).toISOString().slice(0, 10), note: `Refill — ${selected.filename}`, language }); setMsg(`Reminder set for ${r.due_date}.`); load() }} className="rounded-full border px-4 py-2">⏰ Remind me in 7 days</button>
          </div>
          {share && <p className="mt-2 break-all text-sm text-green-700">Share link copied: {share}</p>}
        </div>
      )}
      <div className="card rounded-2xl border bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-[#0A2540]">⏰ Reminders (due soon)</h2>
        {reminders.length === 0 && <p className="text-sm text-slate-500">No reminders. MVP: no SMS/email is sent.</p>}
        {reminders.map((r) => <p key={r.id} className="mt-1 text-sm">{r.type.replace('_', ' ')} · due {r.due_date} · {r.days_until_due === 0 ? 'due today' : `${r.days_until_due} days`} · {r.note || ''}</p>)}
      </div>
    </div>
  )
}
