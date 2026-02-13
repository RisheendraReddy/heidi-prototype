import { useState, useEffect, useRef } from 'react'
import { IntakeCheckResponse } from '../types'
import { continueCare, getNetworkStatusFromLevel } from '../api'
import { IconClipboard, IconLock, IconUnlock, IconTrendUp, IconTrendDown, IconTrendFlat, IconAlert, IconEmpty } from './Icons'
import ParticipationBadge from './ParticipationBadge'
import './HistoryPanel.css'

interface HistoryPanelProps {
  matchResult: IntakeCheckResponse | null
  intakeRequest?: { fullName: string; dob: string; phoneLast4: string } | null
  onContinueCareSuccess?: () => void
}

function HistoryPanel({ matchResult, intakeRequest, onContinueCareSuccess }: HistoryPanelProps) {
  const [animatedLevel, setAnimatedLevel] = useState(0)
  const [isAnimating, setIsAnimating] = useState(false)
  const [continueCareLoading, setContinueCareLoading] = useState(false)
  const [continueCareMessage, setContinueCareMessage] = useState<string | null>(null)
  const [continueCareRecorded, setContinueCareRecorded] = useState(false)
  const prevResultRef = useRef<IntakeCheckResponse | null>(null)

  // Animate level-by-level reveal when new results come in
  useEffect(() => {
    if (matchResult && matchResult !== prevResultRef.current) {
      const contextLevel = matchResult.requestingClinic.contextLevel
      
      if (matchResult.matchFound && matchResult.sharedSummary && contextLevel > 0) {
        setAnimatedLevel(0)
        setIsAnimating(true)
        
        // Staggered animation for each level
        const timers: ReturnType<typeof setTimeout>[] = []
        for (let i = 1; i <= contextLevel; i++) {
          timers.push(setTimeout(() => {
            setAnimatedLevel(i)
            if (i === contextLevel) {
              setTimeout(() => setIsAnimating(false), 300)
            }
          }, i * 500))
        }
        
        prevResultRef.current = matchResult
        return () => timers.forEach(clearTimeout)
      }
    }
    prevResultRef.current = matchResult
  }, [matchResult])

  useEffect(() => {
    setContinueCareMessage(null)
    setContinueCareRecorded(false)
  }, [matchResult, intakeRequest])

  const handleContinueCare = async () => {
    if (!matchResult || !intakeRequest || !matchResult.matchFound || !matchResult.sharedSummary || continueCareRecorded) return
    setContinueCareLoading(true)
    setContinueCareMessage(null)
    try {
      const res = await continueCare({
        clinicId: matchResult.requestingClinic.clinicId,
        fullName: intakeRequest.fullName,
        dob: intakeRequest.dob,
        phoneLast4: intakeRequest.phoneLast4,
      })
      setContinueCareRecorded(true)
      if (res.status === 'recorded') {
        setContinueCareMessage(res.message)
        onContinueCareSuccess?.()
      } else if (res.status === 'already_recorded') {
        setContinueCareMessage('Already recorded')
        onContinueCareSuccess?.()
      } else {
        setContinueCareMessage(res.message ?? '')
      }
    } catch (err) {
      setContinueCareRecorded(false)
      const msg = err instanceof Error ? err.message : 'Failed to record continue care'
      setContinueCareMessage(msg)
      if (import.meta.env.DEV) {
        console.error('[Continue Care]', err)
      }
    } finally {
      setContinueCareLoading(false)
    }
  }

  const canContinueCare = matchResult?.matchFound && matchResult?.sharedSummary && intakeRequest && matchResult.requestingClinic.contextLevel > 0
  const continueCareDisabled = continueCareLoading || continueCareRecorded

  if (!matchResult) {
    return (
      <div className="history-panel">
        <h2>Shared Patient History</h2>
        <div className="history-placeholder">
          <div className="placeholder-icon"><IconClipboard /></div>
          <p>Submit a patient intake form to check for shared history</p>
        </div>
      </div>
    )
  }

  const { matchFound, requestingClinic, sharedSummary, contributionGating, lockedPreview, whatIf } = matchResult
  const contextLevel = requestingClinic.contextLevel

  if (!matchFound) {
    return (
      <div className="history-panel">
        <h2>Shared Patient History</h2>
        <div className="no-match animate-fade-in">
          <div className="no-match-icon"><IconEmpty /></div>
          <p>No prior cross-clinic context found.</p>
        </div>
      </div>
    )
  }

  // Level 0: Show message and lockedPreview
  if (contextLevel === 0) {
    return (
      <div className="history-panel">
        <h2>Shared Patient History</h2>
        <div className="level-0-message animate-fade-in">
          <div className="level-0-icon"><IconLock /></div>
          <p className="message">
            External context is unavailable at your current participation level.
          </p>
          <div className="context-level-indicator level-0">
            <span className="level-badge-inline">Level 0</span>
            You're seeing Level 0 because your clinic shares {requestingClinic.contributionPct}%.
          </div>
          <div className="contribution-gating">
            <p>
              <strong>{contributionGating.contributingClinicsCount}</strong> contributing clinic(s);{' '}
              <strong>{contributionGating.detailCappedClinicsCount}</strong> capped by participation level.
            </p>
          </div>
          {lockedPreview.nextLevelUnlocks.length > 0 && (
            <div className="locked-preview">
              <strong><IconUnlock /> Share more to unlock:</strong>
              <ul>
                {lockedPreview.nextLevelUnlocks.map((unlock, idx) => (
                  <li key={idx}>{unlock}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    )
  }

  // matchFound is true but no details available (e.g., no opted-in contributors)
  if (!sharedSummary) {
    return (
      <div className="history-panel">
        <h2>Shared Patient History</h2>
        <div className="match-found animate-fade-in">
          <div className="context-level-indicator">
            <span className={`level-badge-inline level-${contextLevel}`}>Level {contextLevel}</span>
            You're seeing Level {contextLevel} because your clinic shares {requestingClinic.contributionPct}%.
          </div>
          <div className="contribution-gating">
            <p>
              <strong>{contributionGating.contributingClinicsCount}</strong> contributing clinic(s);{' '}
              <strong>{contributionGating.detailCappedClinicsCount}</strong> capped by participation level.
            </p>
          </div>
          <div className="no-match">
            <p>Match found, but no opted-in clinics contributed usable context.</p>
          </div>
          {lockedPreview.nextLevelUnlocks.length > 0 && (
            <div className="locked-fields">
              <strong><IconUnlock /> Share more to unlock:</strong>
              <ul>
                {lockedPreview.nextLevelUnlocks.map((unlock, idx) => (
                  <li key={idx}>{unlock}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    )
  }

  // Level 1, 2, or 3: Show available data with animation
  return (
    <div className="history-panel">
      <h2>Shared Patient History</h2>
      <div className="match-found">
        <div className="context-level-indicator animate-fade-in">
          <span className={`level-badge-inline level-${contextLevel}`}>Level {contextLevel}</span>
          You're seeing Level {contextLevel} because your clinic shares {requestingClinic.contributionPct}%.
        </div>
        
        {/* Contributing Clinics */}
        {contributionGating.contributingClinics && contributionGating.contributingClinics.length > 0 && (
          <div className="contributing-clinics animate-fade-in">
            <label>Data from:</label>
            <div className="clinic-list">
              {contributionGating.contributingClinics.map((clinic) => (
                <div key={clinic.clinicId} className={`clinic-chip ${clinic.isCapped ? 'capped' : ''}`}>
                  <span className="clinic-name">{clinic.clinicName}</span>
                  <ParticipationBadge
                    networkStatus={getNetworkStatusFromLevel(clinic.contributorLevel)}
                    level={clinic.contributorLevel}
                    size="small"
                  />
                  <span className={`clinic-level level-${clinic.visibleLevel}`}>L{clinic.visibleLevel}</span>
                  {clinic.isCapped && <span className="capped-indicator">capped</span>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Privacy / Reactive-Only Sharing Note */}
        <div className="privacy-note animate-fade-in">
          This history was retrieved because the patient presented at your clinic. Contributing clinics are not notified.
        </div>

        {/* Continue Care Button */}
        {canContinueCare && (
          <div className="continue-care-section animate-fade-in">
            <button
              className="continue-care-btn"
              onClick={handleContinueCare}
              disabled={continueCareDisabled}
            >
              {continueCareLoading ? 'Recording...' : continueCareRecorded ? '✓ Continued' : 'Continue Care'}
            </button>
            {continueCareMessage && (
              <span className="continue-care-message">{continueCareMessage}</span>
            )}
          </div>
        )}

        {/* Level 1 Data */}
        {contextLevel >= 1 && (
          <div className={`level-section level-1 ${animatedLevel >= 1 ? 'animate-slide-in visible' : 'hidden'}`}>
            <div className="level-header">
              <span className="level-tag">L1</span>
              <h3>Basic Context</h3>
            </div>
            {sharedSummary.conditions && sharedSummary.conditions.length > 0 && (
              <div className="data-field">
                <label>Conditions:</label>
                <ul>
                  {sharedSummary.conditions.map((cond, idx) => (
                    <li key={idx} style={{ animationDelay: `${idx * 50}ms` }}>{cond}</li>
                  ))}
                </ul>
              </div>
            )}
            {sharedSummary.dateRanges && sharedSummary.dateRanges.length > 0 && (
              <div className="data-field">
                <label>Date Ranges:</label>
                <ul>
                  {sharedSummary.dateRanges.map((range, idx) => (
                    <li key={idx} style={{ animationDelay: `${idx * 50}ms` }}>
                      {range.start} → {range.end}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Level 2 Data */}
        {contextLevel >= 2 && (
          <div className={`level-section level-2 ${animatedLevel >= 2 ? 'animate-slide-in visible' : 'hidden'}`}>
            <div className="level-header">
              <span className="level-tag">L2</span>
              <h3>Treatment Information</h3>
            </div>
            {sharedSummary.interventions && sharedSummary.interventions.length > 0 && (
              <div className="data-field">
                <label>Interventions:</label>
                <ul>
                  {sharedSummary.interventions.map((intervention, idx) => (
                    <li key={idx} style={{ animationDelay: `${idx * 50}ms` }}>{intervention}</li>
                  ))}
                </ul>
              </div>
            )}
            {sharedSummary.responseTrend && (
              <div className="data-field">
                <label>Response Trend:</label>
                <span className={`trend-badge ${sharedSummary.responseTrend}`}>
                  {sharedSummary.responseTrend === 'improving' && <IconTrendUp />}
                  {sharedSummary.responseTrend === 'plateau' && <IconTrendFlat />}
                  {sharedSummary.responseTrend === 'worse' && <IconTrendDown />}
                  {' '}{sharedSummary.responseTrend}
                </span>
              </div>
            )}
          </div>
        )}

        {/* Level 3 Data */}
        {contextLevel >= 3 && (
          <div className={`level-section level-3 ${animatedLevel >= 3 ? 'animate-slide-in visible' : 'hidden'}`}>
            <div className="level-header">
              <span className="level-tag">L3</span>
              <h3>Full Clinical Context</h3>
            </div>
            {sharedSummary.redFlags && sharedSummary.redFlags.length > 0 && (
              <div className="data-field">
                <label><IconAlert /> Red Flags:</label>
                <ul className="red-flags">
                  {sharedSummary.redFlags.map((flag, idx) => (
                    <li key={idx} style={{ animationDelay: `${idx * 50}ms` }}>{flag}</li>
                  ))}
                </ul>
              </div>
            )}
            {sharedSummary.timeline && sharedSummary.timeline.length > 0 && (
              <div className="data-field">
                <label>Timeline:</label>
                <ul className="timeline-list">
                  {sharedSummary.timeline.map((item, idx) => (
                    <li key={idx} style={{ animationDelay: `${idx * 50}ms` }}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
            {sharedSummary.lastSeenDate && (
              <div className="data-field">
                <label>Last Seen:</label>
                <span className="last-seen-date">{sharedSummary.lastSeenDate}</span>
              </div>
            )}
          </div>
        )}

        {/* What If Calculator */}
        {whatIf && whatIf.length > 0 && (
          <div className={`what-if-section ${!isAnimating ? 'animate-fade-in' : ''}`}>
            <label>What if you increased contribution?</label>
            <div className="what-if-scenarios">
              {whatIf.map((scenario, idx) => (
                <div key={idx} className="what-if-scenario">
                  <div className="scenario-header">
                    <span className="target-pct">+{scenario.increaseNeeded}%</span>
                    <span className="target-arrow">→</span>
                    <span className={`target-level level-${scenario.targetLevel}`}>Level {scenario.targetLevel}</span>
                  </div>
                  <div className="scenario-unlocks">
                    {scenario.unlocks.map((unlock, i) => (
                      <span key={i} className="unlock-item">{unlock}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default HistoryPanel
