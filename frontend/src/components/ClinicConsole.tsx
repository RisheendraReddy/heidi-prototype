import { useState, useEffect, useCallback, useRef } from 'react'
import { fetchClinics, updateClinicSettings, Clinic, getContextLevelFromClinic, getNetworkStatusFromLevel } from '../api'
import ParticipationBadge from './ParticipationBadge'
import './ClinicConsole.css'

interface ClinicConsoleProps {
  activeClinicId: string
  onClinicChange: (clinicId: string) => void
  onSettingsUpdate: (clinic: Clinic) => void
  /** Increment to force refetch clinics (e.g. after demo reset). */
  refreshKey?: number
}

function ClinicConsole({ activeClinicId, onClinicChange, onSettingsUpdate, refreshKey }: ClinicConsoleProps) {
  const [clinics, setClinics] = useState<Clinic[]>([])
  const [activeClinic, setActiveClinic] = useState<Clinic | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadClinics()
  }, [refreshKey ?? 0])

  useEffect(() => {
    if (clinics.length > 0) {
      const clinic = clinics.find(c => c.clinicId === activeClinicId) || clinics[0]
      setActiveClinic(clinic)
      if (clinic.clinicId !== activeClinicId) {
        onClinicChange(clinic.clinicId)
      }
    }
  }, [clinics, activeClinicId])

  const loadClinics = async () => {
    try {
      setLoading(true)
      const data = await fetchClinics()
      setClinics(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load clinics')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleClinicSelect = (clinicId: string) => {
    const clinic = clinics.find(c => c.clinicId === clinicId)
    if (clinic) {
      setActiveClinic(clinic)
      onClinicChange(clinicId)
    }
  }

  const handleOptInToggle = async (optedIn: boolean) => {
    if (!activeClinic) return
    // When unchecking opt-in, contribution must be 0 (Level 0 = Isolated)
    const contributionPct = optedIn ? activeClinic.contributionPct : 0
    const optimistic = {
      ...activeClinic,
      optedIn,
      contributionPct,
      contextLevel: optedIn ? getContextLevelFromClinic({ ...activeClinic, optedIn, contributionPct }) : 0,
      networkStatus: optedIn ? getNetworkStatusFromLevel(getContextLevelFromClinic({ ...activeClinic, optedIn, contributionPct })) : 'Isolated',
    }
    setActiveClinic(optimistic)
    setClinics((prev) => prev.map(c => c.clinicId === activeClinic.clinicId ? optimistic : c))
    onSettingsUpdate(optimistic)
    try {
      setError(null)
      const updated = await updateClinicSettings(
        activeClinic.clinicId,
        optedIn,
        contributionPct
      )
      setActiveClinic(updated)
      setClinics((prev) => prev.map(c => c.clinicId === updated.clinicId ? updated : c))
      onSettingsUpdate(updated)
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update opt-in status'
      setError(`Failed to update opt-in status: ${errorMessage}`)
      console.error('Opt-in toggle error:', err)
      setActiveClinic(activeClinic)
      setClinics((prev) => prev.map(c => c.clinicId === activeClinic.clinicId ? activeClinic : c))
      onSettingsUpdate(activeClinic)
    }
  }

  const contributionDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const handleContributionChange = useCallback(async (contributionPct: number) => {
    if (!activeClinic) return
    try {
      setError(null)
      const updated = await updateClinicSettings(
        activeClinic.clinicId,
        activeClinic.optedIn,
        contributionPct
      )
      setActiveClinic(updated)
      setClinics((prev) => prev.map(c => c.clinicId === updated.clinicId ? updated : c))
      onSettingsUpdate(updated)
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update contribution'
      setError(`Failed to update contribution: ${errorMessage}`)
      console.error('Contribution change error:', err)
    }
  }, [activeClinic, onSettingsUpdate])

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!activeClinic || !activeClinic.optedIn) return
    const value = parseInt(e.target.value)
    const updated = { ...activeClinic, contributionPct: value }
    const level = getContextLevelFromClinic(updated)
    const withLevel = { ...updated, contextLevel: level, networkStatus: getNetworkStatusFromLevel(level) }
    setActiveClinic(withLevel)
    setClinics((prev) => prev.map(c => c.clinicId === activeClinic.clinicId ? withLevel : c))
    if (contributionDebounceRef.current) clearTimeout(contributionDebounceRef.current)
    contributionDebounceRef.current = setTimeout(() => {
      handleContributionChange(value)
      contributionDebounceRef.current = null
    }, 300)
  }

  useEffect(() => () => {
    if (contributionDebounceRef.current) clearTimeout(contributionDebounceRef.current)
  }, [])

  const PRESET_SETTINGS = {
    level0: { optedIn: false, contributionPct: 0 },
    level1: { optedIn: true, contributionPct: 20 },
    level2: { optedIn: true, contributionPct: 60 },
    level3: { optedIn: true, contributionPct: 85 },
  } as const

  const applyPreset = async (preset: keyof typeof PRESET_SETTINGS) => {
    if (!activeClinic) return
    const { optedIn, contributionPct } = PRESET_SETTINGS[preset]
    const level = preset === 'level0' ? 0 : parseInt(preset.replace('level', ''), 10)
    const withLevel = {
      ...activeClinic,
      optedIn,
      contributionPct,
      contextLevel: level,
      networkStatus: getNetworkStatusFromLevel(level),
    }
    setActiveClinic(withLevel)
    setClinics((prev) => prev.map(c => c.clinicId === activeClinic.clinicId ? withLevel : c))
    try {
      setError(null)
      const updated = await updateClinicSettings(
        activeClinic.clinicId,
        optedIn,
        contributionPct
      )
      setActiveClinic(updated)
      setClinics((prev) => prev.map(c => c.clinicId === updated.clinicId ? updated : c))
      onSettingsUpdate(updated)
    } catch (err: unknown) {
      setError('Failed to apply preset')
      console.error(err)
    }
  }

  const getContextLevelDescription = (level: number) => {
    const descriptions = [
      'Level 0: No external context',
      'Level 1: Conditions + Date ranges',
      'Level 2: + Interventions + Response trends',
      'Level 3: + Red flags + Timeline + Last seen date'
    ]
    return descriptions[level] || 'Unknown level'
  }

  const getNextLevelUnlocks = (level: number): string[] => {
    if (level === 0) {
      return ['Conditions and date ranges', 'Contributing clinics count']
    } else if (level === 1) {
      return ['Intervention categories', 'Response trend (improving/plateau/worse)']
    } else if (level === 2) {
      return ['Red flags', 'Timeline (short bullets)', 'Last seen date']
    }
    return []
  }

  if (loading) return <div className="clinic-console">Loading clinics...</div>
  if (error) return <div className="clinic-console error">{error}</div>
  if (!activeClinic) return <div className="clinic-console">No clinic selected</div>

  const effectiveContribution = activeClinic.optedIn ? activeClinic.contributionPct : 0
  const displayLevel = getContextLevelFromClinic({ ...activeClinic, contributionPct: effectiveContribution })
  const displayNetworkStatus = getNetworkStatusFromLevel(displayLevel)
  const nextLevelUnlocks = getNextLevelUnlocks(displayLevel)

  return (
    <div className="clinic-console">
      <h2>Clinic Settings</h2>
      
      <div className="clinic-selector">
        <label>Active Clinic:</label>
        <select
          value={activeClinicId}
          onChange={(e) => handleClinicSelect(e.target.value)}
        >
          {clinics.map(clinic => (
            <option key={clinic.clinicId} value={clinic.clinicId}>
              {clinic.name} ({getNetworkStatusFromLevel(getContextLevelFromClinic(clinic))})
            </option>
          ))}
        </select>
      </div>

      <div className="settings-section">
        <div className="setting-item">
          <label>
            <input
              type="checkbox"
              checked={activeClinic.optedIn}
              onChange={(e) => handleOptInToggle(e.target.checked)}
            />
            Opt-in to sharing
          </label>
        </div>

        <div className={`setting-item ${!activeClinic.optedIn ? 'slider-disabled' : ''}`}>
          <label>
            Contribution: {effectiveContribution}%
            <input
              type="range"
              min="0"
              max="100"
              value={effectiveContribution}
              onChange={handleSliderChange}
              disabled={!activeClinic.optedIn}
              className="slider"
            />
          </label>
        </div>

        <div className="preset-buttons">
          <button onClick={() => applyPreset('level0')} className="preset-btn">
            Free Rider (Level 0)
          </button>
          <button onClick={() => applyPreset('level1')} className="preset-btn">
            Basic Contributor (Level 1)
          </button>
          <button onClick={() => applyPreset('level2')} className="preset-btn">
            Collaborative Contributor (Level 2)
          </button>
          <button onClick={() => applyPreset('level3')} className="preset-btn">
            Trusted Contributor (Level 3)
          </button>
        </div>

        <div className="context-level-display">
          <div className="context-level-row">
            <div className={`level-badge level-${displayLevel}`}>
              Context Level {displayLevel}
            </div>
            <ParticipationBadge
              networkStatus={displayNetworkStatus}
              level={displayLevel}
              size="medium"
            />
          </div>
          <p className="level-description">
            {getContextLevelDescription(displayLevel)}
          </p>
          
          {nextLevelUnlocks.length > 0 && (
            <div className="tier-preview">
              <strong>At the next level you'd also see:</strong>
              <ul>
                {nextLevelUnlocks.map((unlock, idx) => (
                  <li key={idx}>{unlock}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default ClinicConsole
