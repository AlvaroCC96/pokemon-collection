import { useEffect, useState } from 'react'

/** Picks the Home layout (grid vs carousel) from a single source of truth
 * instead of rendering both trees and hiding one with CSS -- that would
 * make Embla measure a zero-width hidden container. */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() => window.matchMedia(query).matches)

  useEffect(() => {
    const mql = window.matchMedia(query)
    const onChange = () => setMatches(mql.matches)
    onChange()
    mql.addEventListener('change', onChange)
    return () => mql.removeEventListener('change', onChange)
  }, [query])

  return matches
}
