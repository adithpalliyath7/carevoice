import { useEffect, useState } from 'react'
import { api } from '../lib/api.js'
import VoiceAssistant from './VoiceAssistant.jsx'
import TokenCard from './TokenCard.jsx'

// Full booking flow: language -> voice/text -> doctor -> slot -> explicit
// confirm -> token. Includes family-member booking + waitlist on full slots.
export default function BookingFlow({ language, setLanguage, languages, seniorMode, onEmergency }) {
  const [speciality, setSpeciality] = useState('')
  const [doctors, setDoctors] = useState([])
  const [doctor, setDoctor] = useState(null)
  const [date, setDate] = useState('')
  const [slots, setSlots] = useState([])
  const [slot, setSlot] = useState('')
  const [patientName, setPatientName] = useState('')
  const [phone, setPhone] = useState('')
  const [familyMember, setFamilyMember] = useState('')
  const [relation, setRelation] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const [appointment, setAppointment] = useState(null)
  const [error, setError] = useState('')
  const [waitlistId, setWaitlistId] = useState('')
  const [waitlistStatus, setWaitlistStatus] = useState('')
  const [feedback, setFeedback] = useState('')

  useEffect(() => { api.doctors().then((d) => setDoctors(d.doctors)).catch(() => {}) }, [])
  useEffect(() => { if (speciality) api.doctors({ speciality }).then((d) => setDoctors(d.doctors)).catch(() => {}) }, [speciality])

  const pickDoctor = async (d) => {
    setDoctor(d)
    const days = (await api.doctor(d.id)).next_7_days
    setDate(days[0])
    const s = await api.slots(d.id, days[0])
    setSlots(s.slots)
  }
  const changeDate = async (d) => { setDate(d); setSlot(''); setSlots((await api.slots(doctor.id, d)).slots) }

  const book = async () => {
    setError('')
    if (!confirmed) { setError('Please tick the confirmation checkbox first.'); return }
    try {
      const appt = await api.book({ doctor_id: doctor.id, date, time: slot, patient_name: patientName,
        patient_phone: phone, for_family_member: familyMember ? `${familyMember} (${relation})` : null,
        confirmed: true, language })
      setAppointment(appt)
    } catch (e) {
      setError(e.body?.error === 'confirmation_required' ? 'Please confirm explicitly before booking.' : e.message)
    }
  }

  const joinWaitlist = async () => {
    try {
      const w = await api.joinWaitlist({ doctor_id: doctor.id, date, patient_name: patientName || 'Patient', phone, language })
      setWaitlistId(w.id); setWaitlistStatus('Joined waitlist — we will offer you the slot if it frees up.')
    } catch (e) { setError(e.message) }
  }
  const checkWaitlist = async () => {
    const w = await api.waitlistEntry(waitlistId)
    setWaitlistStatus(`Status: ${w.status}${w.offer ? ` — slot ${w.offer.time} offered until ${w.offer.expires_at}` : ''}`)
  }

  if (appointment) return <TokenCard appointment={appointment} />

  return (
    <div className="grid gap-4">
      <VoiceAssistant language={language} setLanguage={setLanguage} languages={languages} seniorMode={seniorMode} onEmergency={onEmergency}
        onTranscript={(text) => { const m = text.match(/cardiology|dermatology|orthopedic|paediatric|pediatric|gynaecolog|neurology|ent|dental|eye|general/i); if (m) setSpeciality(m[0].toLowerCase()) }} />
      <div className="card rounded-2xl border bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-[#0A2540]">1 · Choose speciality & doctor</h2>
        <select value={speciality} onChange={(e) => setSpeciality(e.target.value)} className="mt-2 w-full rounded-xl border px-3 py-2">
          <option value="">All specialities</option>
          {['General Physician', 'Cardiology', 'Dermatology', 'Orthopedics', 'Paediatrics', 'Gynaecology', 'Neurology', 'ENT', 'Dental', 'Ophthalmology'].map((s) => <option key={s}>{s}</option>)}
        </select>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {doctors.map((d) => (
            <button key={d.id} onClick={() => pickDoctor(d)} className={`rounded-2xl border p-4 text-left ${doctor?.id === d.id ? 'border-[#015BBB] ring-2 ring-blue-200' : ''}`}>
              <p className="font-semibold">{d.name}</p>
              <p className="text-sm text-slate-500">{d.speciality} · {d.qualification} · {d.experience_years} yrs</p>
              <p className="text-sm">⭐ {d.rating} · ₹{d.fee_inr} · {d.languages.join(', ').toUpperCase()}</p>
            </button>
          ))}
        </div>
      </div>
      {doctor && (
        <div className="card rounded-2xl border bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold text-[#0A2540]">2 · Pick date & time — {doctor.name}</h2>
          {doctor.delay_minutes ? <p className="mt-2 rounded-xl bg-amber-50 p-3 text-sm text-amber-800">⚠️ Doctor delayed by {doctor.delay_minutes} min: {doctor.delay_announcement}</p> : null}
          <input type="date" value={date} onChange={(e) => changeDate(e.target.value)} className="mt-2 rounded-xl border px-3 py-2" />
          <div className="mt-3 flex flex-wrap gap-2">
            {slots.map((s) => (
              <button key={s.time} disabled={!s.available} onClick={() => setSlot(s.time)}
                className={`rounded-full px-4 py-2 ${s.available ? (slot === s.time ? 'bg-[#015BBB] text-white' : 'border') : 'cursor-not-allowed bg-slate-100 text-slate-400 line-through'}`}>
                {s.time}
              </button>
            ))}
          </div>
          {slots.length > 0 && slots.every((s) => !s.available) && (
            <div className="mt-3 rounded-xl bg-blue-50 p-3 text-sm">
              All slots are full for this day. <button onClick={joinWaitlist} className="font-semibold text-[#015BBB] underline">Join the waitlist</button> — if someone cancels, the slot is offered to you first (30 min to accept).
            </div>
          )}
          {waitlistStatus && <p className="mt-2 text-sm text-blue-900">{waitlistStatus} {waitlistId && <button onClick={checkWaitlist} className="underline">Check status</button>}</p>}
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            <input value={patientName} onChange={(e) => setPatientName(e.target.value)} placeholder="Patient name *" className="rounded-xl border px-3 py-2" />
            <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="Phone *" className="rounded-xl border px-3 py-2" />
            <input value={familyMember} onChange={(e) => setFamilyMember(e.target.value)} placeholder="Booking for a family member? Their name (optional)" className="rounded-xl border px-3 py-2" />
            <input value={relation} onChange={(e) => setRelation(e.target.value)} placeholder="Relation, e.g. mother / father / spouse" className="rounded-xl border px-3 py-2" />
          </div>
          {slot && patientName && phone && (
            <div className="mt-4 rounded-2xl bg-slate-50 p-4">
              <h3 className="font-semibold">Please review before confirming</h3>
              <p className="text-sm text-slate-600">{doctor.name} · {doctor.speciality} · {date} at {slot} · ₹{doctor.fee_inr} · Patient: {patientName}{familyMember ? ` (for ${familyMember}, ${relation})` : ''}</p>
              <label className="mt-3 flex items-start gap-2 text-sm">
                <input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} className="mt-1 h-5 w-5" />
                I confirm this booking — doctor, date, time and patient details are correct.
              </label>
              <button onClick={book} disabled={!confirmed} className="mt-3 rounded-full bg-[#015BBB] px-6 py-3 font-semibold text-white disabled:opacity-40">Confirm booking</button>
            </div>
          )}
          {error && <p className="mt-3 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        </div>
      )}
      <div className="card rounded-2xl border bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-[#0A2540]">Find my appointment</h2>
        <form className="mt-2 flex gap-2" onSubmit={async (e) => { e.preventDefault(); const tk = e.target.token.value.trim(); if (tk) setAppointment(await api.appointment(tk)) }}>
          <input name="token" placeholder="Enter token, e.g. CV-20261110-AB12" className="flex-1 rounded-xl border px-3 py-2" />
          <button className="rounded-xl bg-[#0A2540] px-4 py-2 text-white">Find</button>
        </form>
        {appointment === null && feedback && <p className="mt-2 text-sm text-green-700">{feedback}</p>}
      </div>
    </div>
  )
}
