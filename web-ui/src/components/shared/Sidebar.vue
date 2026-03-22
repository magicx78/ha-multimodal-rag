<template>
  <aside class="w-64 bg-gray-900 text-white p-6">
    <div class="mb-8">
      <h2 class="text-xl font-bold">RAG</h2>
    </div>

    <nav class="space-y-2">
      <RouterLink
        to="/"
        class="block px-4 py-2 rounded hover:bg-gray-800 transition"
      >
        📊 Dashboard
      </RouterLink>
      <RouterLink
        to="/admin"
        class="block px-4 py-2 rounded hover:bg-gray-800 transition"
      >
        ⚙️ Admin
      </RouterLink>
    </nav>

    <button
      @click="handleLogout"
      class="mt-8 w-full px-4 py-2 bg-red-600 hover:bg-red-700 rounded transition"
    >
      Logout
    </button>
  </aside>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const handleLogout = async () => {
  await authStore.logout()
  router.push('/login')
}
</script>
