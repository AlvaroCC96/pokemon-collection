import type { PriceSnapshot } from '../api'
import { formatDate, formatMoney } from '../utils/format'

interface PriceChartProps {
  snapshots: PriceSnapshot[]
}

const WIDTH = 600
const HEIGHT = 200
const PADDING_X = 12
const PADDING_Y = 16

/** Small hand-rolled SVG line chart -- a full charting library is overkill
 * for "estimated price over N snapshots" on a personal collection. */
export function PriceChart({ snapshots }: PriceChartProps) {
  if (snapshots.length === 0) return null

  const prices = snapshots.map((s) => s.estimated_price)
  const min = Math.min(...prices)
  const max = Math.max(...prices)
  const range = max - min || 1
  const currency = snapshots[0].currency

  const points = snapshots.map((snapshot, index) => {
    const x =
      snapshots.length === 1
        ? WIDTH / 2
        : PADDING_X + (index / (snapshots.length - 1)) * (WIDTH - PADDING_X * 2)
    const y = HEIGHT - PADDING_Y - ((snapshot.estimated_price - min) / range) * (HEIGHT - PADDING_Y * 2)
    return { x, y, snapshot }
  })

  const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ')
  const areaPath = `${linePath} L ${points[points.length - 1].x} ${HEIGHT} L ${points[0].x} ${HEIGHT} Z`

  return (
    <div className="w-full">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="w-full" role="img" aria-label="Evolución del precio estimado">
        <defs>
          <linearGradient id="priceFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--color-price-gold)" stopOpacity="0.35" />
            <stop offset="100%" stopColor="var(--color-price-gold)" stopOpacity="0" />
          </linearGradient>
        </defs>

        {points.length > 1 && <path d={areaPath} fill="url(#priceFill)" />}
        {points.length > 1 && (
          <path d={linePath} fill="none" stroke="var(--color-price-gold)" strokeWidth="2" strokeLinejoin="round" />
        )}

        {points.map((p, i) => (
          <circle key={p.snapshot.id} cx={p.x} cy={p.y} r={i === points.length - 1 ? 4 : 3} fill="var(--color-price-gold)">
            <title>
              {formatDate(p.snapshot.checked_at)} · {formatMoney(p.snapshot.estimated_price, p.snapshot.currency)}
            </title>
          </circle>
        ))}
      </svg>

      <div className="mt-1 flex justify-between text-xs text-pokedex-muted">
        <span>{formatDate(snapshots[0].checked_at)}</span>
        <span>{formatDate(snapshots[snapshots.length - 1].checked_at)}</span>
      </div>
      <div className="mt-1 flex justify-between text-xs text-pokedex-muted">
        <span>Mín: {formatMoney(min, currency)}</span>
        <span>Máx: {formatMoney(max, currency)}</span>
      </div>
    </div>
  )
}
