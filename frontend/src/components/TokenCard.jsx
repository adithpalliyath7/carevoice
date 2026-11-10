import { useEffect, useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { api } from '../lib/api.js'

// Digital token + QR pass + live queue position + delay announcement.
export default function TokenCard({ appointment }) {
  const [queue, setQueue] = useState(null)
  useEffect(() => {
    let alive = true
    const load = () => api.queuePosition(appointment.token).then((q) => alive && setQueue(q)).catch(() => {})
    load()
    const t = setInterval(load, 30000)
    return () => { alive = false; clearInterval(t) }
  }, [appointment.token])
  return (
    <div className="card rounded-2xl border bg-white p-6 text-center shadow-sm">
      <p className="text-xs font-bold tracking-widest text-slate-400">YOUR APPOINTMENT TOKEN</p>
      <p className="mt-2 text-4xl font-black tracking-wide text-[#0A2540]">{appointment.token}</p>
      <div className="mt-4 flex justify-center"><QRCodeSVG value={appointment.qr_payload} size={160} /></div>
      <p className="mt-3 font-semibold">{appointment.doctor_name} — {appointment.speciality}</p>
      <p className="text-slate-600">{appointment.date} at {appointment.time} · ₹{appointment.fee_inr}</p>
      {appointment.delay_minutes ? (
        <p className="mt-3 rounded-xl bg-amber-50 p-3 text-sm text-amber-800">⚠️ Doctor delayed by {appointment.delay_minutes} min: {appointment.delay_announcement}</p>
      ) : null}
      {queue && (
        <p className="mt-3 rounded-xl bg-blue-50 p-3 text-sm text-blue-900">
          {queue.queue_status === 'not_checked_in'
            ? 'Not checked in yet — check in at reception on arrival.'
            : <>Live queue: position <b>#{queue.queue_position}</b> ({queue.queue_status}) · est. wait {queue.estimated_wait_minutes} min</>}
        </p>
      )}
      <div className="mt-4 flex justify-center gap-2">
        <button onClick={() => api.checkIn(appointment.token).then(() => window.location.reload())} className="rounded-full bg-[#015BBB] px-5 py-2 text-white">✅ Check in now</button>
        <button onClick={() => window.print()} className="rounded-full border px-5 py-2">🖨️ Print / Download</button>
      </div>
      <p className="mt-3 text-xs text-slate-400">Show this token + QR at registration. Demo token — fictional booking.</p>
    </div>
  )
}
