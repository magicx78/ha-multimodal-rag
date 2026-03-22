import apiClient from './client'

export interface ReasoningRequest {
  question: string
  collection_name: string
  temperature?: number
}

export interface ReasoningResponse {
  answer: string
  sources: string[]
  metadata: Record<string, any>
}

export const reasoningAPI = {
  reason: async (request: ReasoningRequest): Promise<ReasoningResponse> => {
    const response = await apiClient.post('/documents/reason', request)
    return response.data
  }
}
