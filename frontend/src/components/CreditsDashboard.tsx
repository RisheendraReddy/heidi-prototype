import { useState, useEffect } from 'react'
import { fetchCreditsDashboard, fetchClinics } from '../api'
import './CreditsDashboard.css'

interface CreditsDashboardProps {
  onClose?: () => void
  compact?: boolean
}

function CreditsDashboard({ onClose, compact = false }: CreditsDashboardProps) {
  const [clinics, setClinics] = useState<Record<string, string>>({})
  const [credits, setCredits] = useState<Record<string, number>>({})
  const [events, setEvents] = useState<Array<{ patientId: string; fromClinic: string; toClinic: string; timestamp: string }>>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [clinicList, dashboard] = await Promise.all([
        fetchClinics(),
        fetchCreditsDashboard(),
      ])
      const names: Record<string, string> = {}
      clinicList.forEach((c) => { names[c.clinicId] = c.name })
      setClinics(names)
      setCredits(dashboard.clinicCredits)
      setEvents(dashboard.recentEvents)
    } catch (err) {
      console.error('Failed to load credits dashboard', err)
    } finally {
      setLoading(false)
    }
  }

  const formatTimestamp = (ts: string) => {
    try {
      const d = new Date(ts)
      return d.toLocaleString()
    } catch {
      return ts
    }
  }

  if (loading) return <div className="credits-dashboard">Loading...</div>

  return (
    <div className={`credits-dashboard ${compact ? 'compact' : ''}`}>
      {onClose && (
        <div className="credits-dashboard-header">
          <h3>Continuity Credits</h3>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
      )}
      <div className="credits-totals">
        <h4>Credits by Clinic</h4>
        <p className="credits-explainer">
          Earned when another clinic uses your shared history to continue care. Higher counts signal network value.
        </p>
        <div className="credits-grid">
          {Object.entries(credits).map(([clinicId, total]) => (
            <div key={clinicId} className="credit-card">
              <span className="clinic-name">{clinics[clinicId] || clinicId}</span>
              <span className="credit-count">{total}</span>
            </div>
          ))}
          {Object.keys(credits).length === 0 && (
            <p className="no-credits">No credits yet. Use &quot;Continue Care&quot; on a patient history to award credits.</p>
          )}
        </div>
      </div>
      <div className="credits-events">
        <h4>Last 5 Credit Events</h4>
        <div className="events-list">
          {events.length === 0 && <p className="no-events">No events yet</p>}
          {events.map((e, i) => (
            <div key={i} className="event-row">
              <span className="event-patient">{e.patientId.split('|')[0]}</span>
              <span className="event-flow">{clinics[e.fromClinic] || e.fromClinic} → {clinics[e.toClinic] || e.toClinic}</span>
              <span className="event-time">{formatTimestamp(e.timestamp)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default CreditsDashboard
