// Mirrors the FastAPI Pydantic schemas in backend/app/schemas/*.py.
// Keep these in sync manually -- there is no shared codegen yet.

export interface Card {
  id: number
  name: string
  collector_number: string
  set_name: string | null
  language: string | null
  rarity: string | null
  image_url: string | null
  quantity: number
  external_card_id: string | null
  identified: boolean
  created_at: string
  updated_at: string
}

export interface CardCreate {
  name: string
  collector_number: string
  quantity?: number
  set_name?: string | null
  language?: string | null
  rarity?: string | null
  image_url?: string | null
}

export interface CardUpdate {
  name?: string
  collector_number?: string
  set_name?: string | null
  language?: string | null
  rarity?: string | null
  image_url?: string | null
  quantity?: number
}

export type IdentifyStatus = 'not_found' | 'single_match' | 'multiple_matches'

export interface IdentificationCandidate {
  external_id: string
  name: string
  // Nullable: some official regional catalogs (e.g. Japan's) don't expose a
  // collector number at all -- never guessed, see backend ARCHITECTURE.md.
  collector_number: string | null
  set_name: string | null
  rarity: string | null
  image_url: string | null
  language: string | null
  source: string | null
}

export interface IdentifyRequest {
  name: string
  collector_number: string
  set_name?: string | null
  language?: string | null
  page?: number
}

export interface IdentifyResponse {
  status: IdentifyStatus
  candidates: IdentificationCandidate[]
  // True if calling identify() again with page+1 (same name/number/language)
  // would likely surface more candidates -- only ever true for sources that
  // paginate without an exact server-side filter (e.g. Japan's official
  // search on a common name). See CandidateCard/AddCardPage "Cargar más".
  has_more: boolean
}

export type MarketScope = 'CHILE' | 'INTERNATIONAL'
export type ConfidenceLabel = 'HIGH' | 'MEDIUM' | 'LOW'

export interface SourceObservation {
  source_name: string
  source_url: string | null
  observed_price: number
  currency: string
  market_region: string
  language: string | null
  observed_at: string | null
  is_outlier: boolean
  included_in_estimate: boolean
}

export interface Valuation {
  estimated: number
  low: number | null
  high: number | null
  currency: string
  market_scope: MarketScope
  confidence_score: number
  confidence_label: ConfidenceLabel
}

export interface UpdatePriceResponse {
  card: Card
  valuation: Valuation
  sources: SourceObservation[]
}

export interface PriceSnapshot {
  id: number
  estimated_price: number
  low_price: number | null
  high_price: number | null
  currency: string
  market_scope: MarketScope
  confidence_score: number
  confidence_label: ConfidenceLabel
  source_count: number
  provider: string
  checked_at: string
  previous_price: number | null
  price_change: number | null
  price_change_percent: number | null
  observations: SourceObservation[]
}

export interface CardPriceHistory {
  card_id: number
  snapshots: PriceSnapshot[]
}

export interface UpdateAllCardResult {
  card_id: number
  status: 'updated' | 'failed'
  error: string | null
}

export interface UpdateAllResponse {
  total: number
  updated: number
  failed: number
  details: UpdateAllCardResult[]
}

export interface CardValueSummary {
  card_id: number
  name: string
  collector_number: string
  estimated_price: number
  currency: string
  quantity: number
  total_value: number
  market_scope: string
  checked_at: string
  price_change_percent: number | null
}

export interface CurrencyTotal {
  currency: string
  total_value: number
  card_count: number
}

export interface CollectionStats {
  distinct_card_count: number
  total_card_count: number
  cards_with_valuation: number
  cards_without_valuation: number
  total_estimated_value: number
  currency: string
  other_currency_totals: CurrencyTotal[]
  most_valuable_card: CardValueSummary | null
  top_valuable_cards: CardValueSummary[]
  last_price_update: string | null
}

export interface ApiErrorBody {
  error: string
  message: string
}
