import { useState } from 'react'

interface CardImageProps {
  src: string | null
  alt: string
  className?: string
}

function Placeholder({ className }: { className: string }) {
  return (
    <div
      className={`flex items-center justify-center bg-gradient-to-br from-pokedex-surface-2 to-pokedex-bg text-pokedex-muted/50 ${className}`}
    >
      <svg viewBox="0 0 24 24" fill="none" className="h-10 w-10" aria-hidden="true">
        <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.5" />
        <path d="M3 12h18" stroke="currentColor" strokeWidth="1.5" />
        <circle cx="12" cy="12" r="2.5" stroke="currentColor" strokeWidth="1.5" />
      </svg>
    </div>
  )
}

export function CardImage({ src, alt, className = '' }: CardImageProps) {
  const [failed, setFailed] = useState(false)

  if (!src || failed) {
    return <Placeholder className={className} />
  }

  return (
    <img
      src={src}
      alt={alt}
      loading="lazy"
      className={`object-contain ${className}`}
      onError={() => setFailed(true)}
    />
  )
}
