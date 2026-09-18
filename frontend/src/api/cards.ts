import { apiClient } from './client'
import type {
  Card,
  CardCreate,
  CardPriceHistory,
  CardUpdate,
  IdentifyRequest,
  IdentifyResponse,
  UpdatePriceResponse,
} from './types'

export const cardsApi = {
  list: () => apiClient.get<Card[]>('/api/cards'),
  get: (id: number) => apiClient.get<Card>(`/api/cards/${id}`),
  create: (data: CardCreate) => apiClient.post<Card>('/api/cards', data),
  update: (id: number, data: CardUpdate) => apiClient.put<Card>(`/api/cards/${id}`, data),
  remove: (id: number) => apiClient.delete<void>(`/api/cards/${id}`),

  identify: (data: IdentifyRequest) => apiClient.post<IdentifyResponse>('/api/cards/identify', data),
  reidentify: (id: number, overrides?: Partial<IdentifyRequest>) =>
    apiClient.post<IdentifyResponse>(`/api/cards/${id}/identify`, overrides ?? {}),

  updatePrice: (id: number) => apiClient.post<UpdatePriceResponse>(`/api/cards/${id}/update-price`),
  priceHistory: (id: number) => apiClient.get<CardPriceHistory>(`/api/cards/${id}/prices`),
}
