import './ParticipationBadge.css'

interface ParticipationBadgeProps {
  networkStatus: string
  level?: number
  size?: 'small' | 'medium'
}

const STATUS_LABELS: Record<string, string> = {
  'Isolated': 'Isolated',
  'Basic': 'Basic',
  'Collaborative': 'Collaborative',
  'Trusted Contributor': 'Trusted Contributor',
}

function ParticipationBadge({ networkStatus, level = 0, size = 'medium' }: ParticipationBadgeProps) {
  const label = STATUS_LABELS[networkStatus] || networkStatus || 'Isolated'
  return (
    <span className={`participation-badge participation-badge--${size} status-${level}`}>
      {label}
    </span>
  )
}

export default ParticipationBadge
