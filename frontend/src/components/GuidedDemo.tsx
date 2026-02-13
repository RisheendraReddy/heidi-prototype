import { useState } from 'react'
import {
  demoReset,
  demoScenarioAllLevel0,
  updateClinicSettings,
  checkIntake,
  continueCare,
} from '../api'
import './GuidedDemo.css'

interface GuidedDemoProps {
  onClose: () => void
  onStateChange: () => void
  onShowDashboard: () => void
}

interface Step {
  title: string
  narration: string
  buttonLabel: string
  action: () => Promise<void>
}

function GuidedDemo({ onClose, onStateChange, onShowDashboard }: GuidedDemoProps) {
  const [currentStep, setCurrentStep] = useState(0)
  const [running, setRunning] = useState(false)
  const [stepDone, setStepDone] = useState(false)

  const steps: Step[] = [
    {
      title: 'Step 1: Everyone is blind',
      narration:
        'All clinics start at Level 0. Nobody shares, nobody sees patient history. ' +
        'This is the 19% world -- clinics want to receive history but refuse to share their own.',
      buttonLabel: 'Set all clinics to Level 0',
      action: async () => {
        await demoReset()
        await demoScenarioAllLevel0()
        onStateChange()
      },
    },
    {
      title: 'Step 2: One clinic opts in',
      narration:
        'Clinic A decides to contribute at 10% (Level 1). They now see basic info -- conditions and date ranges -- ' +
        'from other clinics that also contribute. But Level 0 clinics still see nothing. ' +
        'The incentive: even minimal sharing unlocks useful context.',
      buttonLabel: 'Set Clinic A to Level 1',
      action: async () => {
        await updateClinicSettings('A', true, 20)
        await updateClinicSettings('C', true, 30)
        onStateChange()
      },
    },
    {
      title: 'Step 3: Higher contribution unlocks more',
      narration:
        'Clinic A increases to 85% (Level 3 -- Trusted Contributor). Now they see everything: ' +
        'red flags, timeline, last seen date. But they only see Level 1 data from Clinic C (which contributes at 30%). ' +
        'This is reciprocity: you get data at the level you contribute, capped by what others share.',
      buttonLabel: 'Set Clinic A to Level 3',
      action: async () => {
        await updateClinicSettings('A', true, 85)
        onStateChange()
      },
    },
    {
      title: 'Step 4: Credits reward sharing',
      narration:
        'When Clinic B uses shared history to continue a patient\'s care, contributing clinics (A and C) earn continuity credits. ' +
        'This is the reward: your data helped another clinic treat the patient better, and you get credit for it. ' +
        'Credits are idempotent -- clicking twice does not inflate them.',
      buttonLabel: 'Run Continue Care (as Clinic B)',
      action: async () => {
        await updateClinicSettings('B', true, 45)
        await checkIntake({ clinicId: 'B', fullName: 'John Doe', dob: '1990-01-15', phoneLast4: '1234' })
        await continueCare({ clinicId: 'B', fullName: 'John Doe', dob: '1990-01-15', phoneLast4: '1234' })
        onStateChange()
      },
    },
    {
      title: 'Step 5: Benchmarking unlocks',
      narration:
        'Open the Dashboard to see credits earned and outcome benchmarking (You vs Network Average). ' +
        'Benchmarking is only available at Level 1+ -- another incentive to opt in. ' +
        'This is how 19% becomes 80%: blindness is costly, sharing is rewarded, and free-riders get nothing.',
      buttonLabel: 'Open Dashboard',
      action: async () => {
        onShowDashboard()
      },
    },
  ]

  const step = steps[currentStep]

  const handleRun = async () => {
    setRunning(true)
    try {
      await step.action()
      setStepDone(true)
    } catch (err) {
      console.error('Guided demo step failed:', err)
    } finally {
      setRunning(false)
    }
  }

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep((s) => s + 1)
      setStepDone(false)
    } else {
      onClose()
    }
  }

  return (
    <div className="guided-demo-overlay">
      <div className="guided-demo-panel" onClick={(e) => e.stopPropagation()}>
        <div className="guided-demo-header">
          <h3>Guided Demo: 19% to 80%</h3>
          <span className="guided-demo-step-indicator">
            {currentStep + 1} / {steps.length}
          </span>
          <button className="guided-demo-close" onClick={onClose}>
            ×
          </button>
        </div>
        <p className="guided-demo-title">{step.title}</p>
        <p className="guided-demo-narration">{step.narration}</p>
        <div className="guided-demo-actions">
          <button
            className="guided-demo-run"
            onClick={handleRun}
            disabled={running || stepDone}
          >
            {running ? 'Running...' : stepDone ? 'Done' : step.buttonLabel}
          </button>
          {stepDone && (
            <button className="guided-demo-next" onClick={handleNext}>
              {currentStep < steps.length - 1 ? 'Next step' : 'Finish'}
            </button>
          )}
        </div>
        <div className="guided-demo-progress">
          {steps.map((_, i) => (
            <div
              key={i}
              className={`progress-dot ${
                i < currentStep ? 'completed' : i === currentStep ? 'active' : ''
              }`}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

export default GuidedDemo
