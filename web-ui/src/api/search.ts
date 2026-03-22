import apiClient from './client'

export interface SearchRequest {
  query: string
  collection_name: string
  top_k?: number
}

export interface SearchResult {
  score: number
  text: string
  source: string
}

export const searchAPI = {
  search: async (request: SearchRequest): Promise<{ results: SearchResult[] }> => {
    const response = await apiClient.post('/documents/search', request)
    return response.data
  }
}
