<template>
  <div class="p-8">
    <h1 class="text-3xl font-bold mb-8">Admin Panel</h1>

    <div class="space-y-6">
      <!-- Settings Card -->
      <div class="card">
        <h2 class="text-xl font-bold mb-4">⚙️ Settings</h2>
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium mb-2">API Endpoint</label>
            <input
              v-model="apiEndpoint"
              type="text"
              class="input-field"
              placeholder="http://localhost:8000"
            />
          </div>
          <div>
            <label class="flex items-center">
              <input type="checkbox" v-model="darkMode" class="mr-2" />
              <span>Dark Mode</span>
            </label>
          </div>
          <button class="btn-primary">Save Settings</button>
        </div>
      </div>

      <!-- Users Card -->
      <div class="card">
        <h2 class="text-xl font-bold mb-4">👥 Users</h2>
        <p class="text-gray-600">User management coming soon...</p>
      </div>

      <!-- System Info Card -->
      <div class="card">
        <h2 class="text-xl font-bold mb-4">📊 System Info</h2>
        <div class="space-y-2 text-sm">
          <p><span class="font-semibold">Version:</span> 1.1.0</p>
          <p><span class="font-semibold">API Status:</span> <span class="text-green-600">Connected</span></p>
          <p><span class="font-semibold">Uptime:</span> Online</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const apiEndpoint = ref(import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000')
const darkMode = ref(false)
</script>
