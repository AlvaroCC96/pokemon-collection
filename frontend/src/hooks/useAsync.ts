import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from '../api'

interface AsyncState<T> {
  data: T | null
  loading: boolean
  error: string | null
}

/** Minimal fetch-on-mount + refetch hook. No external data-fetching library --
 * the app's needs (a handful of GET endpoints, no caching/pagination) don't
 * justify one. */
export function useAsync<T>(fetcher: () => Promise<T>, deps: unknown[] = []) {
  const [state, setState] = useState<AsyncState<T>>({ data: null, loading: true, error: null })
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  const run = useCallback(() => {
    let cancelled = false
    setState((prev) => ({ ...prev, loading: true, error: null }))

    fetcherRef
      .current()
      .then((data) => {
        if (!cancelled) setState({ data, loading: false, error: null })
      })
      .catch((err: unknown) => {
        if (cancelled) return
        const message = err instanceof ApiError ? err.message : 'No se pudo conectar con el servidor.'
        setState({ data: null, loading: false, error: message })
      })

    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  useEffect(() => run(), [run])

  return { ...state, refetch: run }
}
