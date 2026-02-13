import { useState } from 'react'
import { checkIntake, IntakeCheckRequest } from '../api'
import { IntakeCheckResponse } from '../types'
import './IntakeForm.css'

interface IntakeFormProps {
  activeClinicId: string
  onMatchFound: (result: IntakeCheckResponse, request?: { fullName: string; dob: string; phoneLast4: string }) => void
}

function IntakeForm({ activeClinicId, onMatchFound }: IntakeFormProps) {
  const [formData, setFormData] = useState({
    fullName: '',
    dob: '',
    phoneLast4: '',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    // Validate phone last4 is exactly 4 digits
    if (!/^\d{4}$/.test(formData.phoneLast4)) {
      setError('Phone last 4 digits must be exactly 4 numbers')
      setLoading(false)
      return
    }

    try {
      const request: IntakeCheckRequest = {
        clinicId: activeClinicId,
        fullName: formData.fullName,
        dob: formData.dob,
        phoneLast4: formData.phoneLast4,
      }
      const result = await checkIntake(request)
      onMatchFound(result, { fullName: formData.fullName, dob: formData.dob, phoneLast4: formData.phoneLast4 })
    } catch (err) {
      setError('Failed to check patient')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const loadDemoPatient = (patientNum: 1 | 2) => {
    if (patientNum === 1) {
      // Patient 1: John Doe, DOB: 1990-01-15, Phone: 1234
      setFormData({
        fullName: 'John Doe',
        dob: '1990-01-15',
        phoneLast4: '1234',
      })
    } else {
      // Patient 2: Jane Smith, DOB: 1985-03-22, Phone: 5678
      setFormData({
        fullName: 'Jane Smith',
        dob: '1985-03-22',
        phoneLast4: '5678',
      })
    }
  }

  return (
    <div className="intake-form">
      <h2>Patient Intake</h2>
      
      <div className="demo-presets">
        <button 
          type="button" 
          onClick={() => loadDemoPatient(1)}
          className="demo-btn"
        >
          Demo Preset Patient 1
        </button>
        <button 
          type="button" 
          onClick={() => loadDemoPatient(2)}
          className="demo-btn"
        >
          Demo Preset Patient 2
        </button>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="fullName">Full Name:</label>
          <input
            type="text"
            id="fullName"
            name="fullName"
            value={formData.fullName}
            onChange={handleChange}
            required
            placeholder="John Doe"
          />
        </div>
        <div className="form-group">
          <label htmlFor="dob">Date of Birth (YYYY-MM-DD):</label>
          <input
            type="date"
            id="dob"
            name="dob"
            value={formData.dob}
            onChange={handleChange}
            required
          />
        </div>
        <div className="form-group">
          <label htmlFor="phoneLast4">Phone Last 4 Digits:</label>
          <input
            type="text"
            id="phoneLast4"
            name="phoneLast4"
            value={formData.phoneLast4}
            onChange={handleChange}
            required
            pattern="\d{4}"
            maxLength={4}
            placeholder="1234"
          />
        </div>
        <button type="submit" disabled={loading}>
          {loading ? 'Checking...' : 'Check shared history'}
        </button>
      </form>
      {error && <p className="error">{error}</p>}
    </div>
  )
}

export default IntakeForm
