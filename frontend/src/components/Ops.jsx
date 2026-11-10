import { useEffect, useState } from 'react'
import { api } from '../lib/api.js'

// Staff dashboard (demo login only — real JWT/Supabase Auth required before
// production). Today's appointments, live queue, walk-in booking, availability
// editor, delay announcements, cancellations, waitlist, analytics.
export default function Ops({ language }) {
  const [role, setRole] = useState('')
  const [email, setEmail] = useState('receptionist@demo')
  const [password, setPassword] = useState('demo1234')
  const [appts, setAppts] = useState([])
  const [analytics, setAnalytics] = useState(null)
  const [langStats, setLangStats] = useState(null)
  const [queue, setQueue] = useState([])
  const [qDoctor, setQDoctor] = useState('dr-anitha-nair')
  const [msg, setMsg] = useState('')
  const [waitlist, setWaitlist] = useState([])
  const [cancels, setCancels] = useState([])
  const today = new Date().toISOString().slice(0, 10)

  const load = async (r) => {
    const a = await api.opsAnalyticsOverview(r)
    setAnalytics(a)
    setLangStats(await api.opsAnalyticsLanguage(r))
    setAppts((await api.opsAppointments(r, { date: today })).appointments)
    setQueue((await api.opsQueue(r, qDoctor, today)).queue)
    setWaitlist((await api.opsWaitlist(r)).waitlist)
    setCancels((await api.opsCancellations(r, today)).cancellations)
  }
  useEffect(() => { if (role) load(role).catch((e) => setMsg(e.message)) }, [role])

  const login = async () => {
    try {
      const res = await api.opsLogin(email, password)
      setRole(res.role); setMsg(res.warning)
    } catch (e) { setMsg(e.message) }
  }

  if (!role) {
    return (
      <div className="card mx-auto max-w-md rounded-2xl border bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-[#0A2540]">Staff sign-in (demo)</h2>
        <p className="text-sm text-slate-500">receptionist@demo / admin@demo, password <b>demo1234</b>. DEMO ONLY — replace with real auth before production.</p>
        <input value={email} onChange={(e) => setEmail(e.target.value)} className="mt-3 w-full rounded-xl border px-3 py-2" />
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="mt-2 w-full rounded-xl border px-3 py-2" />
        <button onClick={login} className="mt-3 w-full rounded-full bg-[#015BBB] px-5 py-2 text-white">Sign in</button>
        {msg && <p className="mt-2 text-sm text-amber-700">{msg}</p>}
      </div>
    )
  }

  const bar = (label, value, max) => (
    <div className="mt-1 flex items-center gap-2 text-sm">
      <span className="w-28 truncate">{label}</span>
      <div className="h-4 flex-1 rounded bg-slate-100"><div className="h-4 rounded bg-[#015BBB]" style={{ width: `${max ? Math.round((value / max) * 100) : 0}%` }} /></div>
      <span className="w-8 text-right">{value}</span>
    </div>
  )

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-[#0A2540]">Staff dashboard — {role}</h2>
        <button onClick={() => setRole('')} className="rounded-full border px-4 py-1 text-sm">Sign out</button>
      </div>
      {msg && <p className="rounded-xl bg-amber-50 p-3 text-sm text-amber-800">{msg}</p>}
      {analytics && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[['Total today', analytics.total], ['Booked', analytics.booked], ['Checked in', analytics.checked_in], ['Completed', analytics.completed], ['Cancelled', analytics.cancelled], ['No-show', analytics.no_show], ['Walk-ins', analytics.walk_in], ['Avg wait (min)', analytics.avg_wait_minutes]].map(([l, v]) => (
            <div key={l} className="card rounded-2xl border bg-white p-4 shadow-sm"><p className="text-xs text-slate-500">{l}</p><p className="text-2xl font-bold text-[#0A2540]">{v}</p></div>
          ))}
        </div>
      )}
      {analytics && (
        <div className="card rounded-2xl border bg-white p-5 shadow-sm">
          <h3 className="font-semibold">Appointments by speciality (today)</h3>
          {Object.entries(analytics.by_speciality).map(([k, v]) => bar(k, v, Math.max(...Object.values(analytics.by_speciality), 1)))}
          <h3 className="mt-4 font-semibold">Language usage (voice + bookings)</h3>
          {langStats && Object.entries(langStats.by_language).map(([k, v]) => bar(k, v, Math.max(...Object.values(langStats.by_language), 1)))}
          {langStats && Object.keys(langStats.by_language).length === 0 && <p className="text-sm text-slate-500">No voice sessions yet this run.</p>}
        </div>
      )}
      <div className="card rounded-2xl border bg-white p-5 shadow-sm">
        <h3 className="font-semibold">Today's appointments ({appts.length})</h3>
        {appts.map((a) => (
          <div key={a.token} className="mt-2 flex flex-wrap items-center gap-2 rounded-xl border p-3 text-sm">
            <span className={`rounded-full px-2 py-0.5 text-xs ${a.source === 'walk-in' ? 'bg-orange-100' : 'bg-blue-100'}`}>{a.source === 'walk-in' ? 'Walk-in' : 'Online'}</span>
            <b>{a.token}</b><span>{a.patient_name}</span><span>{a.doctor_name}</span><span>{a.time}</span><span>{a.status}</span>
            <button onClick={async () => { await api.opsCheckIn(role, a.token); load(role) }} className="rounded-full border px-3 py-1">Check in</button>
          </div>
        ))}
        {appts.length === 0 && <p className="text-sm text-slate-500">No appointments today yet.</p>}
      </div>
      <div className="card rounded-2xl border bg-white p-5 shadow-sm">
        <h3 className="font-semibold">Live queue</h3>
        <div className="mt-2 flex gap-2">
          <select value={qDoctor} onChange={(e) => { setQDoctor(e.target.value); api.opsQueue(role, e.target.value, today).then((q) => setQueue(q.queue)) }} className="rounded-xl border px-3 py-2">
            <option value="dr-anitha-nair">Dr. Anitha Nair</option><option value="dr-rahul-menon">Dr. Rahul Menon</option><option value="dr-arun-kumar">Dr. Arun Kumar</option>
          </select>
          <button onClick={async () => { await api.opsCallNext(role, qDoctor, today); load(role) }} className="rounded-full bg-[#015BBB] px-4 py-2 text-white">📣 Call next</button>
        </div>
        {queue.map((e, i) => (
          <div key={e.token} className="mt-2 flex flex-wrap items-center gap-2 rounded-xl border p-3 text-sm">
            <b>#{e.position}</b><span>{e.token}</span><span>{e.patient_name}</span><span>{e.status}</span>
            <button onClick={() => { const nq = [...queue]; if (i > 0) { [nq[i - 1], nq[i]] = [nq[i], nq[i - 1]]; setQueue(nq) } }} className="rounded-full border px-2 py-1">↑</button>
            <button onClick={() => { const nq = [...queue]; if (i < nq.length - 1) { [nq[i + 1], nq[i]] = [nq[i], nq[i + 1]]; setQueue(nq) } }} className="rounded-full border px-2 py-1">↓</button>
            <button onClick={async () => { await api.opsQueueAction(role, e.token, 'mark-done'); load(role) }} className="rounded-full border px-3 py-1">Done</button>
            <button onClick={async () => { await api.opsQueueAction(role, e.token, 'mark-no-show'); load(role) }} className="rounded-full border px-3 py-1">No-show</button>
          </div>
        ))}
        {queue.length === 0 && <p className="text-sm text-slate-500">Queue is empty — check patients in to add them.</p>}
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="card rounded-2xl border bg-white p-5 shadow-sm">
          <h3 className="font-semibold">Walk-in booking</h3>
          <form className="mt-2 grid gap-2" onSubmit={async (e) => {
            e.preventDefault()
            const f = e.target
            try {
              const a = await api.opsWalkIn(role, { doctor_id: f.doctor.value, date: f.date.value, time: f.time.value, patient_name: f.name.value, patient_phone: f.phone.value, language })
              setMsg(`Walk-in booked: ${a.token}`); load(role)
            } catch (err) { setMsg(err.message) }
          }}>
            <select name="doctor" className="rounded-xl border px-3 py-2"><option value="dr-anitha-nair">Dr. Anitha Nair — General</option><option value="dr-rahul-menon">Dr. Rahul Menon — Cardiology</option><option value="dr-arun-kumar">Dr. Arun Kumar — Orthopedics</option></select>
            <input name="date" type="date" defaultValue={today} className="rounded-xl border px-3 py-2" />
            <input name="time" placeholder="Time HH:MM, e.g. 09:00" className="rounded-xl border px-3 py-2" />
            <input name="name" placeholder="Patient name" className="rounded-xl border px-3 py-2" />
            <input name="phone" placeholder="Phone" className="rounded-xl border px-3 py-2" />
            <button className="rounded-full bg-[#015BBB] px-4 py-2 text-white">Book walk-in</button>
          </form>
        </div>
        <div className="card rounded-2xl border bg-white p-5 shadow-sm">
          <h3 className="font-semibold">Delay announcement</h3>
          <form className="mt-2 grid gap-2" onSubmit={async (e) => {
            e.preventDefault(); const f = e.target
            await api.opsDelay(role, f.doctor.value, { minutes: +f.minutes.value, message: f.message.value, language })
            setMsg('Delay published — patients see it on their token and doctor page.'); load(role)
          }}>
            <select name="doctor" className="rounded-xl border px-3 py-2"><option value="dr-anitha-nair">Dr. Anitha Nair</option><option value="dr-rahul-menon">Dr. Rahul Menon</option></select>
            <input name="minutes" type="number" placeholder="Delay in minutes" className="rounded-xl border px-3 py-2" />
            <input name="message" placeholder="Message, e.g. Doctor delayed by 30 minutes" className="rounded-xl border px-3 py-2" />
            <button className="rounded-full bg-[#015BBB] px-4 py-2 text-white">Publish delay</button>
          </form>
          <h3 className="mt-4 font-semibold">Availability (admin only)</h3>
          <p className="text-sm text-slate-500">Weekly hours editor is available via the API (PUT /api/ops/doctors/{"{id}"}/availability, admin role). Block a slot:</p>
          <form className="mt-2 flex gap-2" onSubmit={async (e) => { e.preventDefault(); const f = e.target; await api.opsBlockSlot(role, 'dr-anitha-nair', { date: f.date.value, time: f.time.value, reason: f.reason.value }); setMsg('Slot blocked.') }}>
            <input name="date" type="date" defaultValue={today} className="rounded-xl border px-3 py-1 text-sm" />
            <input name="time" placeholder="09:00" className="w-20 rounded-xl border px-3 py-1 text-sm" />
            <input name="reason" placeholder="Reason" className="flex-1 rounded-xl border px-3 py-1 text-sm" />
            <button className="rounded-full border px-3 py-1 text-sm">Block</button>
          </form>
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="card rounded-2xl border bg-white p-5 shadow-sm">
          <h3 className="font-semibold">Waitlist ({waitlist.length})</h3>
          {waitlist.map((w) => <p key={w.id} className="mt-1 text-sm">{w.id} · {w.doctor_id} · {w.date} · {w.status}{w.offer ? ` — offered ${w.offer.time}` : ''}</p>)}
          {waitlist.length === 0 && <p className="text-sm text-slate-500">No one waiting.</p>}
        </div>
        <div className="card rounded-2xl border bg-white p-5 shadow-sm">
          <h3 className="font-semibold">Cancellations today ({cancels.length})</h3>
          {cancels.map((c, i) => <p key={i} className="mt-1 text-sm">{c.token} · {c.reason} · by {c.cancelled_by}</p>)}
          {cancels.length === 0 && <p className="text-sm text-slate-500">None today.</p>}
        </div>
      </div>
    </div>
  )
}
