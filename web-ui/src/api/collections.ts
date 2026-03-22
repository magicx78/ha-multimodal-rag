import apiClient from './client'

export interface Collection {
  name: string
  document_count: number
  size: number
}

export const collectionsAPI = {
  list: async (): Promise<{ collections: Collection[] }> => {
    const response = await apiClient.get('/collections')
    return response.data
  },

  delete: async (documentId: string): Promise<{ success: boolean }> => {
    const response = await apiClient.delete(`/documents/${documentId}`)
    return response.data
  }
}
