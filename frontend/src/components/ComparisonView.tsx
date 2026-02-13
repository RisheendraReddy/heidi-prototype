import { useState, useEffect } from 'react'
import { fetchClinics, checkIntake, Clinic, IntakeCheckResponse, getNetworkStatusFromLevel } from '../api'
import { IconLock, IconEmpty } from './Icons'
import ParticipationBadge from './ParticipationBadge'
import './ComparisonView.css'

interface ComparisonViewProps {
  onClose: () => void
}

function ComparisonView({ onClose }: ComparisonViewProps) {
  const [clinics, setClinics] = useState<Clinic[]>([])
  const [leftClinicId, setLeftClinicId] = useState<string>('')
  const [rightClinicId, setRightClinicId] = useState<string>('')
  const [leftResult, setLeftResult] = useState<IntakeCheckResponse | null>(null)
  const [rightResult, setRightResult] = useState<IntakeCheckResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [patientData, setPatientData] = useState({
    fullName: 'John Doe',
    dob: '1990-01-15',
    phoneLast4: '1234',
  })

  useEffect(() => {
    loadClinics()
  }, [])

  const loadClinics = async () => {
    try {
      const data = await fetchClinics()
      setClinics(data)
      if (data.length >= 2) {
        setLeftClinicId(data[0].clinicId)
        setRightClinicId(data[2]?.clinicId || data[1].clinicId)
      }
    } catch (err) {
      console.error('Failed to load clinics', err)
    }
  }

  const runComparison = async () => {
    if (!leftClinicId || !rightClinicId) return
    
    setLoading(true)
    setLeftResult(null)
    setRightResult(null)

    try {
      const [left, right] = await Promise.all([
        checkIntake({ clinicId: leftClinicId, ...patientData }),
        checkIntake({ clinicId: rightClinicId, ...patientData }),
      ])
      
      // Staggered reveal for dramatic effect
      setTimeout(() => setLeftResult(left), 300)
      setTimeout(() => setRightResult(right), 600)
    } catch (err) {
      console.error('Comparison failed', err)
    } finally {
      setLoading(false)
    }
  }

  const loadDemoPatient = (num: 1 | 2) => {
    if (num === 1) {
      setPatientData({ fullName: 'John Doe', dob: '1990-01-15', phoneLast4: '1234' })
    } else {
      setPatientData({ fullName: 'Jane Smith', dob: '1985-03-22', phoneLast4: '5678' })
    }
    setLeftResult(null)
    setRightResult(null)
  }

  const getClinic = (id: string) => clinics.find(c => c.clinicId === id)
  const leftClinic = getClinic(leftClinicId)
  const rightClinic = getClinic(rightClinicId)

  return (
    <div className="comparison-overlay">
      <div className="comparison-container">
        <div className="comparison-header">
          <h2>Side-by-Side Clinic Comparison</h2>
          <p className="comparison-subtitle">See how the same patient looks from different clinic perspectives</p>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div className="comparison-controls">
          <div className="clinic-selectors">
            <div className="selector-group">
              <label>Left Clinic:</label>
              <select value={leftClinicId} onChange={(e) => { setLeftClinicId(e.target.value); setLeftResult(null); }}>
                {clinics.map(c => (
                  <option key={c.clinicId} value={c.clinicId}>
                    {c.name} (Level {c.contextLevel})
                  </option>
                ))}
              </select>
            </div>
            <div className="vs-badge">VS</div>
            <div className="selector-group">
              <label>Right Clinic:</label>
              <select value={rightClinicId} onChange={(e) => { setRightClinicId(e.target.value); setRightResult(null); }}>
                {clinics.map(c => (
                  <option key={c.clinicId} value={c.clinicId}>
                    {c.name} (Level {c.contextLevel})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="patient-controls">
            <div className="patient-info">
              <span className="patient-label">Patient:</span>
              <span className="patient-name">{patientData.fullName}</span>
              <span className="patient-details">DOB: {patientData.dob} | Phone: ***{patientData.phoneLast4}</span>
            </div>
            <div className="patient-buttons">
              <button onClick={() => loadDemoPatient(1)} className={patientData.phoneLast4 === '1234' ? 'active' : ''}>
                Patient 1 (Cross-clinic)
              </button>
              <button onClick={() => loadDemoPatient(2)} className={patientData.phoneLast4 === '5678' ? 'active' : ''}>
                Patient 2 (Single clinic)
              </button>
            </div>
          </div>

          <button className="compare-btn" onClick={runComparison} disabled={loading}>
            {loading ? 'Comparing...' : 'Run Comparison'}
          </button>
        </div>

        {/* Asymmetry Insight Banner */}
        {leftClinic && rightClinic && leftClinic.contextLevel !== rightClinic.contextLevel && (leftResult || rightResult) && (
          <div className="asymmetry-banner">
            {leftClinic.contextLevel > rightClinic.contextLevel
              ? `${leftClinic.name} (Level ${leftClinic.contextLevel}) sees more detail than ${rightClinic.name} (Level ${rightClinic.contextLevel}) for the same patient. Contribute more, see more.`
              : `${rightClinic.name} (Level ${rightClinic.contextLevel}) sees more detail than ${leftClinic.name} (Level ${leftClinic.contextLevel}) for the same patient. Contribute more, see more.`
            }
          </div>
        )}

        <div className="comparison-panels">
          <ComparisonPanel 
            clinic={leftClinic} 
            result={leftResult} 
            side="left"
          />
          <div className="divider" />
          <ComparisonPanel 
            clinic={rightClinic} 
            result={rightResult} 
            side="right"
          />
        </div>
      </div>
    </div>
  )
}

interface ComparisonPanelProps {
  clinic: Clinic | undefined
  result: IntakeCheckResponse | null
  side: 'left' | 'right'
}

function ComparisonPanel({ clinic, result, side }: ComparisonPanelProps) {
  const [animateLevel, setAnimateLevel] = useState(0)

  useEffect(() => {
    if (result && result.matchFound && result.sharedSummary) {
      // Animate levels appearing one by one
      setAnimateLevel(0)
      const contextLevel = result.requestingClinic.contextLevel
      
      const timers: ReturnType<typeof setTimeout>[] = []
      for (let i = 1; i <= contextLevel; i++) {
        timers.push(setTimeout(() => setAnimateLevel(i), i * 400))
      }
      
      return () => timers.forEach(clearTimeout)
    } else {
      setAnimateLevel(0)
    }
  }, [result])

  if (!clinic) {
    return <div className={`comparison-panel ${side}`}>Select a clinic</div>
  }

  const contextLevel = clinic.contextLevel

  return (
    <div className={`comparison-panel ${side} ${result ? 'has-result' : ''}`}>
      <div className="panel-header">
        <h3>{clinic.name}</h3>
        <div className="panel-badges">
          <div className={`level-badge level-${contextLevel}`}>
            Level {contextLevel}
          </div>
          <ParticipationBadge
            networkStatus={getNetworkStatusFromLevel(contextLevel)}
            level={contextLevel}
            size="small"
          />
        </div>
      </div>
      
      <div className="panel-stats">
        <div className="stat">
          <span className="stat-label">Contribution</span>
          <span className="stat-value">{clinic.contributionPct}%</span>
        </div>
        <div className="stat">
          <span className="stat-label">Opted In</span>
          <span className={`stat-value ${clinic.optedIn ? 'yes' : 'no'}`}>
            {clinic.optedIn ? 'Yes' : 'No'}
          </span>
        </div>
      </div>

      {!result && (
        <div className="panel-placeholder">
          <p>Click "Run Comparison" to see results</p>
        </div>
      )}

      {result && !result.matchFound && (
        <div className="panel-no-match fade-in">
          <div className="no-match-icon"><IconEmpty /></div>
          <p>No cross-clinic history found</p>
        </div>
      )}

      {result && result.matchFound && contextLevel === 0 && (
        <div className="panel-level-0 fade-in">
          <div className="locked-icon"><IconLock /></div>
          <p>External context unavailable at Level 0</p>
          <p className="hint">Increase contribution to unlock</p>
        </div>
      )}

      {result && result.matchFound && result.sharedSummary && contextLevel > 0 && (
        <div className="panel-data">
          {/* Level 1 Data */}
          <div className={`data-level level-1 ${animateLevel >= 1 ? 'visible' : ''}`}>
            <div className="level-header">
              <span className="level-tag">L1</span>
              <span>Basic Context</span>
            </div>
            {result.sharedSummary.conditions && result.sharedSummary.conditions.length > 0 && (
              <div className="data-item">
                <label>Conditions</label>
                <ul>
                  {result.sharedSummary.conditions.map((c: string, i: number) => (
                    <li key={i}>{c}</li>
                  ))}
                </ul>
              </div>
            )}
            {result.sharedSummary.dateRanges && result.sharedSummary.dateRanges.length > 0 && (
              <div className="data-item">
                <label>Date Ranges</label>
                <ul>
                  {result.sharedSummary.dateRanges.map((r: { start: string; end: string }, i: number) => (
                    <li key={i}>{r.start} → {r.end}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Level 2 Data */}
          {contextLevel >= 2 && (
            <div className={`data-level level-2 ${animateLevel >= 2 ? 'visible' : ''}`}>
              <div className="level-header">
                <span className="level-tag">L2</span>
                <span>Treatment Info</span>
              </div>
              {result.sharedSummary.interventions && result.sharedSummary.interventions.length > 0 && (
                <div className="data-item">
                  <label>Interventions</label>
                  <ul>
                    {result.sharedSummary.interventions.map((int: string, i: number) => (
                      <li key={i}>{int}</li>
                    ))}
                  </ul>
                </div>
              )}
              {result.sharedSummary.responseTrend && (
                <div className="data-item">
                  <label>Response Trend</label>
                  <span className={`trend ${result.sharedSummary.responseTrend}`}>
                    {result.sharedSummary.responseTrend}
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Level 3 Data */}
          {contextLevel >= 3 && (
            <div className={`data-level level-3 ${animateLevel >= 3 ? 'visible' : ''}`}>
              <div className="level-header">
                <span className="level-tag">L3</span>
                <span>Full Context</span>
              </div>
              {result.sharedSummary.redFlags && result.sharedSummary.redFlags.length > 0 && (
                <div className="data-item red-flags">
                  <label>Red Flags</label>
                  <ul>
                    {result.sharedSummary.redFlags.map((flag: string, i: number) => (
                      <li key={i}>{flag}</li>
                    ))}
                  </ul>
                </div>
              )}
              {result.sharedSummary.timeline && result.sharedSummary.timeline.length > 0 && (
                <div className="data-item">
                  <label>Timeline</label>
                  <ul className="timeline-list">
                    {result.sharedSummary.timeline.map((item: string, i: number) => (
                      <li key={i}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}
              {result.sharedSummary.lastSeenDate && (
                <div className="data-item">
                  <label>Last Seen</label>
                  <span>{result.sharedSummary.lastSeenDate}</span>
                </div>
              )}
            </div>
          )}

          {/* Gating info */}
          <div className="gating-info fade-in">
            <span>
              {result.contributionGating.contributingClinicsCount} contributing clinic(s)
              {result.contributionGating.detailCappedClinicsCount > 0 && (
                <>, {result.contributionGating.detailCappedClinicsCount} capped</>
              )}
            </span>
          </div>
        </div>
      )}

      {/* Locked preview for levels below 3 */}
      {result && result.matchFound && result.lockedPreview.nextLevelUnlocks.length > 0 && (
        <div className="locked-preview fade-in">
          <strong>Unlock at next level:</strong>
          <ul>
            {result.lockedPreview.nextLevelUnlocks.map((u, i) => (
              <li key={i}>{u}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

export default ComparisonView
