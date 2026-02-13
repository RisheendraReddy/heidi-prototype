import { useState, useEffect } from 'react'
import ClinicConsole from './components/ClinicConsole'
import IntakeForm from './components/IntakeForm'
import HistoryPanel from './components/HistoryPanel'
import Walkthrough from './components/Walkthrough'
import ComparisonView from './components/ComparisonView'
import CreditsDashboard from './components/CreditsDashboard'
import BenchmarkingSection from './components/BenchmarkingSection'
import GuidedDemo from './components/GuidedDemo'
import { IconCompare } from './components/Icons'
import { Clinic, IntakeCheckResponse } from './types'
import { fetchDemoStatus, demoReset, demoScenarioAllLevel0 } from './api'
import './App.css'

function App() {
  const [activeClinicId, setActiveClinicId] = useState<string>('A')
  const [matchResult, setMatchResult] = useState<IntakeCheckResponse | null>(null)
  const [intakeRequest, setIntakeRequest] = useState<{ fullName: string; dob: string; phoneLast4: string } | null>(null)
  const [showWalkthrough, setShowWalkthrough] = useState(false)
  const [showComparison, setShowComparison] = useState(false)
  const [showDashboard, setShowDashboard] = useState(false)
  const [creditsRefreshKey, setCreditsRefreshKey] = useState(0)
  const [clinicRefreshKey, setClinicRefreshKey] = useState(0)
  const [demoMode, setDemoMode] = useState(false)
  const [toastMessage, setToastMessage] = useState<string | null>(null)
  const [resetLoading, setResetLoading] = useState(false)
  const [resetError, setResetError] = useState<string | null>(null)
  const [scenarioLoading, setScenarioLoading] = useState(false)
  const [showGuidedDemo, setShowGuidedDemo] = useState(false)

  useEffect(() => {
    // Show Reviewer Tools when backend reports demo mode OR when VITE_DEMO_MODE is set
    const fromEnv = import.meta.env.VITE_DEMO_MODE === 'true'
    if (fromEnv) {
      setDemoMode(true)
    } else {
      fetchDemoStatus().then(({ demoMode: dm }) => setDemoMode(dm))
    }
  }, [])

  useEffect(() => {
    if (!toastMessage) return
    const t = setTimeout(() => setToastMessage(null), 3000)
    return () => clearTimeout(t)
  }, [toastMessage])

  const handleDemoReset = async () => {
    setResetLoading(true)
    setResetError(null)
    try {
      await demoReset()
      setMatchResult(null)
      setIntakeRequest(null)
      setCreditsRefreshKey((k) => k + 1)
      setClinicRefreshKey((k) => k + 1)
      setToastMessage('Demo reset complete')
    } catch (err) {
      setResetError(err instanceof Error ? err.message : 'Reset failed')
    } finally {
      setResetLoading(false)
    }
  }

  const handleScenarioAllLevel0 = async () => {
    setScenarioLoading(true)
    setResetError(null)
    try {
      await demoScenarioAllLevel0()
      setMatchResult(null)
      setIntakeRequest(null)
      setCreditsRefreshKey((k) => k + 1)
      setClinicRefreshKey((k) => k + 1)
      setToastMessage('All clinics set to Level 0')
    } catch (err) {
      setResetError(err instanceof Error ? err.message : 'Scenario failed')
    } finally {
      setScenarioLoading(false)
    }
  }

  const handleClinicChange = (clinicId: string) => {
    setActiveClinicId(clinicId)
    setMatchResult(null)
  }

  const handleSettingsUpdate = (_clinic: Clinic) => {
    setMatchResult(null)
    setCreditsRefreshKey((k) => k + 1)  // Refetch dashboard + benchmarking
  }

  const handleMatchFound = (result: IntakeCheckResponse, request?: { fullName: string; dob: string; phoneLast4: string }) => {
    setMatchResult(result)
    setIntakeRequest(request ?? null)
  }

  return (
    <div className="app">
      {showGuidedDemo && (
        <GuidedDemo
          onClose={() => setShowGuidedDemo(false)}
          onStateChange={() => {
            setCreditsRefreshKey((k) => k + 1)
            setClinicRefreshKey((k) => k + 1)
            setMatchResult(null)
            setIntakeRequest(null)
          }}
          onShowDashboard={() => setShowDashboard(true)}
        />
      )}
      {showWalkthrough && <Walkthrough onClose={() => setShowWalkthrough(false)} />}
      {showComparison && <ComparisonView onClose={() => setShowComparison(false)} />}
      {showDashboard && (
        <div className="dashboard-overlay" onClick={() => setShowDashboard(false)}>
          <div className="dashboard-modal" onClick={(e) => e.stopPropagation()}>
            <button className="dashboard-close" onClick={() => setShowDashboard(false)}>×</button>
            <h2>Dashboard</h2>
            <div className="dashboard-grid">
              <CreditsDashboard key={creditsRefreshKey} compact />
              <BenchmarkingSection key={creditsRefreshKey} activeClinicId={activeClinicId} />
            </div>
          </div>
        </div>
      )}
      {toastMessage && (
        <div className="toast" role="status">
          {toastMessage}
        </div>
      )}
      <header className="app-header">
        <h1>Incentive Design Under Adversarial Conditions</h1>
        <div className="header-buttons">
          {demoMode && (
            <div className="reviewer-tools">
              <span className="reviewer-tools-label">Reviewer Tools</span>
              <button
                onClick={handleDemoReset}
                disabled={resetLoading || scenarioLoading}
                className="demo-reset-button"
                title="Reset demo data to baseline"
              >
                {resetLoading ? 'Resetting…' : 'Reset demo data'}
              </button>
              <button
                onClick={handleScenarioAllLevel0}
                disabled={resetLoading || scenarioLoading}
                className="demo-reset-button"
                title="Set all clinics to Level 0"
              >
                {scenarioLoading ? 'Applying…' : 'All Level 0'}
              </button>
              {resetError && <span className="reset-error">{resetError}</span>}
            </div>
          )}
          <button onClick={() => setShowGuidedDemo(true)} className="guided-demo-button">
            Start Guided Demo
          </button>
          <button onClick={() => setShowDashboard(true)} className="dashboard-button">
            Dashboard
          </button>
          <button onClick={() => setShowComparison(true)} className="comparison-button">
            <IconCompare /> Compare Clinics
          </button>
          <button onClick={() => setShowWalkthrough(true)} className="help-button">
            Learn More
          </button>
        </div>
      </header>
      <main className="app-main">
        <div className="left-panel">
          <ClinicConsole
            activeClinicId={activeClinicId}
            onClinicChange={handleClinicChange}
            onSettingsUpdate={handleSettingsUpdate}
            refreshKey={clinicRefreshKey}
          />
          <IntakeForm
            activeClinicId={activeClinicId}
            onMatchFound={handleMatchFound}
          />
        </div>
        <div className="right-panel">
          <HistoryPanel
            matchResult={matchResult}
            intakeRequest={intakeRequest}
            onContinueCareSuccess={() => setCreditsRefreshKey((k) => k + 1)}
          />
        </div>
      </main>
    </div>
  )
}

export default App
