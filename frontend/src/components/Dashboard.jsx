// Home dashboard: today's summary + quick actions. Data comes from the ops
// overview endpoint when staff is signed in; otherwise shows demo info.
export default function Dashboard({ onTab }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <div className="card rounded-2xl border bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-[#0A2540]">🏥 CareVoice General Hospital — Demo</h2>
        <p className="text-sm text-slate-500">Kochi, Kerala · 12 fictional doctors · 10 specialities · 7 languages</p>
        <button onClick={() => onTab('book')} className="mt-3 rounded-full bg-[#015BBB] px-5 py-2 text-white">Book an appointment</button>
      </div>
      <div className="card rounded-2xl border bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-[#0A2540]">🧭 Hospital navigation</h2>
        <p className="text-sm text-slate-500">Coming soon — indoor wayfinding and directions are on the roadmap. No maps or directions are shown in this MVP.</p>
      </div>
      <div className="card rounded-2xl border bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-[#0A2540]">💬 How was your visit?</h2>
        <p className="text-sm text-slate-500">Feedback is collected for a future voice-feedback feature. No analysis is done in this MVP.</p>
        <button onClick={() => onTab('book')} className="mt-3 rounded-full border px-5 py-2">Leave feedback after your visit</button>
      </div>
      <div className="card rounded-2xl border bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-[#0A2540]">🚨 In an emergency</h2>
        <p className="text-sm text-slate-500">Call 108 (ambulance) or 112. CareVoice connects you — it does not dispatch ambulances.</p>
      </div>
    </div>
  )
}
