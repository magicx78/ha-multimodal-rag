import apiClient from './client'

export const uploadAPI = {
  upload: async (file: File, collectionName: string) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('collection_name', collectionName)
    
    const response = await apiClient.post('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return response.data
  }
}
