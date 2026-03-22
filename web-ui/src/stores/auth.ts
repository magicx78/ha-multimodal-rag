import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authAPI } from '../api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('auth_token'))
  const userId = ref<string | null>(localStorage.getItem('user_id'))

  const isAuthenticated = computed(() => !!token.value)

  const login = async (username: string, password: string) => {
    try {
      const response = await authAPI.login({ username, password })
      token.value = response.token
      userId.value = response.user_id
      localStorage.setItem('auth_token', response.token)
      localStorage.setItem('user_id', response.user_id)
      return true
    } catch (error) {
      console.error('Login failed:', error)
      return false
    }
  }

  const logout = async () => {
    try {
      await authAPI.logout()
      token.value = null
      userId.value = null
      localStorage.removeItem('auth_token')
      localStorage.removeItem('user_id')
    } catch (error) {
      console.error('Logout failed:', error)
    }
  }

  return { token, userId, isAuthenticated, login, logout }
})
