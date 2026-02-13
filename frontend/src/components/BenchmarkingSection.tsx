import { useState, useEffect } from 'react'
import { fetchClinicBenchmark, ClinicBenchmark } from '../api'
import './BenchmarkingSection.css'

interface BenchmarkingSectionProps {
  activeClinicId: string
  onClose?: () => void
}

function BenchmarkingSection({ activeClinicId, onClose }: BenchmarkingSectionProps) {
  const [benchmark, setBenchmark] = useState<ClinicBenchmark | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadBenchmark()
  }, [activeClinicId])

  const loadBenchmark = async () => {
    try {
      setLoading(true)
      const data = await fetchClinicBenchmark(activeClinicId)
      setBenchmark(data)
    } catch (err) {
      console.error('Failed to load benchmark', err)
    } finally {
      setLoading(false)
    }
  }

  const trends = ['improving', 'plateau', 'worse'] as const

  if (loading) return <div className="benchmarking-section">Loading...</div>;
  if (!benchmark) return <div className="benchmarking-section">Failed to load benchmark.</div>;

  const ineligibleMessage =
    benchmark?.reason === 'locked_level_0'
      ? 'Benchmarking locked — contribute at least Level 1 to unlock.'
      : benchmark?.reason === 'not_opted_in'
        ? 'Opt in to enable benchmarking'
        : benchmark?.reason === 'no_participants'
          ? 'No network benchmark yet — clinics must opt in at Level 1+.'
          : 'Benchmarking unavailable.'

  const showBars = benchmark && benchmark.eligible

  return (
    <div className="benchmarking-section">
      {onClose && (
        <div className="benchmarking-header">
          <h3>Outcome Benchmarking</h3>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
      )}
      <p className="benchmarking-note">You vs Network Average (response trends only). No clinic names or Level 3 data.</p>
      <div className="benchmark-legend">
        <span className="legend-item improving">Improving — positive patient trajectory</span>
        <span className="legend-item plateau">Plateau — stable, no significant change</span>
        <span className="legend-item worse">Worse — outcomes declining</span>
      </div>
      {benchmark && !benchmark.eligible ? (
        <div className="benchmark-ineligible">
          <p>{ineligibleMessage}</p>
        </div>
      ) : showBars ? (
        <div className="benchmark-table">
          <div className="benchmark-row header">
            <span className="col-trend">Trend</span>
            <span className="col-you">You</span>
            <span className="col-network">Network Avg</span>
          </div>
          {benchmark && trends.map((trend) => (
            <div key={trend} className="benchmark-row">
              <span className="col-trend">{trend}</span>
              <span className="col-you">
                <span className="bar-container">
                  <span className="bar you" style={{ width: `${(benchmark.clinicDistribution[trend] ?? 0) * 100}%` }} />
                </span>
                {((benchmark.clinicDistribution[trend] ?? 0) * 100).toFixed(0)}%
              </span>
              <span className="col-network">
                <span className="bar-container">
                  <span className="bar network" style={{ width: `${(benchmark.networkAverage[trend] ?? 0) * 100}%` }} />
                </span>
                {((benchmark.networkAverage[trend] ?? 0) * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  )
}

export default BenchmarkingSection
