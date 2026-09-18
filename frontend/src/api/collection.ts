import { apiClient } from './client'
import type { CollectionStats, UpdateAllResponse } from './types'

export const collectionApi = {
  stats: () => apiClient.get<CollectionStats>('/api/collection/stats'),
  updateAll: () => apiClient.post<UpdateAllResponse>('/api/prices/update-all'),
}
