import { useEffect, useState } from 'react'
import { api } from './lib/api.js'
import { t } from './lib/i18n.js'
import BookingFlow from './components/BookingFlow.jsx'
import Records from './components/Records.jsx'
import Support from './components/Support.jsx'
import Ops from './components/Ops.jsx'
import Emergency from './components/Emergency.jsx'
import Dashboard from './components/Dashboard.jsx'

export default function App() {
  const [tab, setTab] = useState('book')
  const [language, setLanguage] = useState('en')
  const [languages, setLanguages] = useState([])
  const [health, setHealth] = useState(null)
  const [seniorMode, setSeniorMode] = useState(false)
  const [emergencyOpen, setEmergencyOpen] = useState(false)
  const [emergencyNote, setEmergencyNote] = useState('')

  useEffect(() => {
    api.languages().then((r) => setLanguages(r.languages)).catch(() => {})
    api.health().then(setHealth).catch(() => setHealth({ status: 'unreachable' }))
  }, [])

  const tabs = [
    ['book', t(language, 'book')],
    ['records', t(language, 'records')],
    ['support', t(language, 'support')],
    ['staff', t(language, 'staff')],
  ]

  return (
    <div className={seniorMode ? 'senior-mode min-h-screen bg-slate-50 text-slate-900' : 'min-h-screen bg-slate-50 text-slate-900'}>
      <header className="sticky top-0 z-40 border-b bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-2 px-4 py-3">
          <button onClick={() => setTab('book')} className="text-xl font-black text-[#0A2540]">CareVoice <span className="text-[#015BBB]">🩺</span></button>
          <span className="hidden rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-800 sm:inline">{t(language, 'demo')}</span>
          <div className="ml-auto flex flex-wrap items-center gap-2">
            {tabs.map(([id, label]) => (
              <button key={id} onClick={() => setTab(id)} className={`rounded-full px-3 py-1.5 text-sm ${tab === id ? 'bg-[#0A2540] text-white' : 'border'}`}>{label}</button>
            ))}
            <button onClick={() => setSeniorMode(!seniorMode)} aria-pressed={seniorMode} className={`rounded-full px-3 py-1.5 text-sm ${seniorMode ? 'bg-amber-500 text-white' : 'border'}`}>
              👴 {t(language, 'senior')}
            </button>
            <button onClick={() => setEmergencyOpen(true)} className="rounded-full bg-red-600 px-4 py-1.5 text-sm font-bold text-white">🚨 {t(language, 'emergency')}</button>
          </div>
        </div>
        {health && health.status !== 'ok' && (
          <p className="bg-amber-50 px-4 py-1 text-center text-xs text-amber-800">Backend unreachable — start it with <code>uvicorn app.main:app --reload</code> in backend/.</p>
        )}
        {health?.status === 'ok' && !health.gnani_configured && (
          <p className="bg-amber-50 px-4 py-1 text-center text-xs text-amber-800">Voice transcription/speech needs a Gnani API key on the server (GNANI_API_KEY). Booking, records, support and staff tools work without it.</p>
        )}
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6">
        {seniorMode && (
          <div className="mb-4 rounded-2xl border-2 border-amber-400 bg-amber-50 p-4">
            <p className="font-bold">Senior / Easy mode is on</p>
            <p className="text-sm">Large text, big buttons, single column, slow voice (0.85×), confirmations repeated, no recording timeouts. You can book for a family member in the booking form.</p>
            <a href="tel:108" className="mt-2 inline-block rounded-full bg-red-600 px-5 py-3 font-bold text-white">📞 Call for help — 108</a>
          </div>
        )}
        {emergencyNote && <p className="mb-4 rounded-2xl bg-red-50 p-3 text-sm text-red-800">{emergencyNote}</p>}
        {tab === 'book' && <BookingFlow language={language} setLanguage={setLanguage} languages={languages} seniorMode={seniorMode}
          onEmergency={(res) => { setEmergencyOpen(true); setEmergencyNote(res?.speak_text || 'Emergency — call 108 or 112 now.') }} />}
        {tab === 'records' && <Records language={language} />}
        {tab === 'support' && <Support language={language} seniorMode={seniorMode} onEmergency={() => setEmergencyOpen(true)} />}
        {tab === 'staff' && <Ops language={language} />}
        {tab === 'book' && <div className="mt-4"><Dashboard onTab={setTab} /></div>}
      </main>
      <footer className="border-t bg-white px-4 py-4 text-center text-xs text-slate-400">
        CareVoice MVP · Demo — fictional hospital, doctors and slots · CareVoice does not diagnose, does not delay care, and does not dispatch ambulances.
      </footer>
      {emergencyOpen && <Emergency language={language} seniorMode={seniorMode} onClose={() => setEmergencyOpen(false)} />}
    </div>
  )
}
