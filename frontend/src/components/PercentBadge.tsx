import { formatPercent } from '../utils/format'

interface PercentBadgeProps {
  value: number | null
  className?: string
}

export function PercentBadge({ value, className = '' }: PercentBadgeProps) {
  if (value === null) return null

  const positive = value >= 0
  return (
    <span
      className={`inline-flex items-center gap-1 text-sm font-medium ${
        positive ? 'text-emerald-400' : 'text-rose-400'
      } ${className}`}
    >
      {positive ? '↑' : '↓'} {formatPercent(value)}
    </span>
  )
}
