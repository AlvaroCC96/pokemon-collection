// Fixed list instead of free text: a typo or "Ingles" vs "Inglés" vs "EN" used
// to silently break the backend's language filter (it now normalizes common
// variants too, but a select avoids the problem at the source).
export const LANGUAGE_OPTIONS = [
  { value: '', label: 'Sin especificar' },
  { value: 'Español', label: 'Español' },
  { value: 'Inglés', label: 'Inglés' },
  { value: 'Japonés', label: 'Japonés' },
  { value: 'Francés', label: 'Francés' },
  { value: 'Alemán', label: 'Alemán' },
  { value: 'Italiano', label: 'Italiano' },
  { value: 'Portugués', label: 'Portugués' },
  { value: 'Coreano', label: 'Coreano' },
  { value: 'ZH-TW', label: 'Chino tradicional (Taiwán/HK)' },
  { value: 'ZH-CN', label: 'Chino simplificado (China)' },
] as const
