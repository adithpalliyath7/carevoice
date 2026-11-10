import { useState } from 'react'
import { api } from '../lib/api.js'

// 3-state emergency flow (design reference only — Indian demo contacts).
// State 1: huge red SOS + call buttons. State 2: help-requested (only AFTER
// the user taps Call/SOS — never claims responders are dispatched).
// State 3: nearby departments ONLY with location consent + real data.
export default function Emergency({ language, seniorMode, onClose }) {
  const [stage, setStage] = useState(1)
  const [payload, setPayload] = useState(null)
  const [called, setCalled] = useState(null)
  const [locNote, setLocNote] = useState('')

  const load = async (withLocation) => {
    try {
      if (withLocation) {
        const pos = await new Promise((res, rej) => navigator.geolocation.getCurrentPosition(res, rej, { timeout: 8000 }))
        const p = await api.emergency({ language, latitude: pos.coords.latitude, longitude: pos.coords.longitude, consent_given: true })
        setPayload(p); setLocNote('Location shared by you — not stored.')
      } else {
        setPayload(await api.emergency({ language, consent_given: false }))
      }
    } catch {
      setPayload(await api.emergency({ language, consent_given: false }))
      setLocNote('Location permission was not granted — showing contacts only.')
    }
  }

  const sos = async () => { await load(false); setStage(2) }
  const call = (which) => { setCalled(which); setStage(2) }

  if (stage === 1) {
    return (
      <div className="fixed inset-0 z-50 overflow-auto bg-red-50 p-4">
        <div className="mx-auto max-w-lg rounded-3xl bg-white p-6 text-center shadow-xl">
          <p className="text-sm font-bold tracking-widest text-red-600">🚨 EMERGENCY</p>
          <h2 className="mt-2 text-2xl font-bold text-[#0A2540]">Are you in an emergency?</h2>
          <p className="mt-2 text-slate-600">Press the button below — help will reach you soon.</p>
          <button onClick={sos} className="mt-6 h-44 w-44 rounded-full bg-red-600 text-3xl font-black text-white shadow-lg ring-8 ring-red-200">SOS</button>
          <p className="mt-4 text-xs text-slate-400">CareVoice does not dispatch ambulances. It connects you to 108 / 112 and the hospital.</p>
          <button onClick={onClose} className="mt-4 rounded-full border px-5 py-2">Close</button>
        </div>
      </div>
    )
  }

  const tel = (n) => `tel:${n.replace(/[^+0-9]/g, '')}`
  return (
    <div className="fixed inset-0 z-50 overflow-auto bg-red-50 p-4">
      <div className="mx-auto max-w-lg rounded-3xl bg-white p-6 shadow-xl">
        <h2 className="text-2xl font-bold text-red-700">🆘 {called ? 'You have requested help — stay on the call' : 'Call for help now'}</h2>
        <p className="mt-2 text-slate-600">Speak calmly. Stay on the line. Do not hang up.</p>
        <div className="mt-4 grid gap-3">
          <a href="tel:108" onClick={() => call('108')} className="rounded-2xl bg-red-600 px-5 py-4 text-center text-xl font-bold text-white">📞 Call 108 — Ambulance</a>
          <a href="tel:112" onClick={() => call('112')} className="rounded-2xl bg-red-600 px-5 py-4 text-center text-xl font-bold text-white">📞 Call 112 — National Emergency</a>
          <a href={tel(payload?.hospital?.casualty_phone || '+914840000001')} onClick={() => call('casualty')} className="rounded-2xl bg-[#0A2540] px-5 py-4 text-center text-xl font-bold text-white">🏥 Call hospital casualty (demo number)</a>
        </div>
        {called && <p className="mt-4 rounded-xl bg-amber-50 p-3 text-sm text-amber-800">You tapped Call {called}. This app does not track whether the call connected — stay on the line with the operator. No responder name or ETA is shown because none has been confirmed.</p>}
        <div className="mt-4 flex flex-wrap gap-2">
          <button onClick={() => load(true)} className="rounded-full border px-4 py-2">📍 Share my location (with your permission)</button>
          <button onClick={() => setStage(3)} className="rounded-full border px-4 py-2">Nearby emergency departments</button>
          <button onClick={onClose} className="rounded-full border px-4 py-2">Close</button>
        </div>
        {locNote && <p className="mt-2 text-xs text-slate-500">{locNote}</p>}
        {stage === 3 && (
          <div className="mt-4 rounded-2xl border p-4">
            <h3 className="font-semibold">Nearby emergency departments</h3>
            {payload?.nearby_departments?.length ? payload.nearby_departments.map((d) => (
              <div key={d.name} className="mt-2">
                <p className="font-semibold">{d.name} — {d.location}</p>
                <p className="text-sm text-slate-600">About {d.distance_km} km away (straight-line estimate only). Demo hospital — not a live directory.</p>
                <a className="text-[#015BBB] underline" href={d.maps_url} target="_blank" rel="noreferrer">Open directions in Google Maps (demo location)</a>
              </div>
            )) : <p className="mt-2 text-sm text-slate-600">{payload?.nearby_note || 'Enable location to see nearby departments.'}</p>}
          </div>
        )}
      </div>
    </div>
  )
}
