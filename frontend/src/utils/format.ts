const clpFormatter = new Intl.NumberFormat('es-CL', {
  style: 'currency',
  currency: 'CLP',
  maximumFractionDigits: 0,
})

const genericMoneyFormatter = new Intl.NumberFormat('es-CL', {
  maximumFractionDigits: 2,
})

const percentFormatter = new Intl.NumberFormat('es-CL', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 2,
})

const dateFormatter = new Intl.DateTimeFormat('es-CL', {
  dateStyle: 'short',
  timeStyle: 'short',
})

/** Formats a price using the right convention for its currency: "$235.000" for
 * CLP (no decimals, Chilean thousands separator), "1.234,56" + code otherwise. */
export function formatMoney(value: number, currency: string): string {
  if (currency.toUpperCase() === 'CLP') {
    return clpFormatter.format(value)
  }
  return `${genericMoneyFormatter.format(value)} ${currency.toUpperCase()}`
}

/** "6,82%" -- caller adds the sign/arrow (see <PercentBadge />). */
export function formatPercent(value: number): string {
  return `${percentFormatter.format(Math.abs(value))}%`
}

export function formatDate(value: string): string {
  return dateFormatter.format(new Date(value))
}
