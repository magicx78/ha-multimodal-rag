<template>
  <div class="space-y-4">
    <button
      @click="loadCollections"
      :disabled="loading"
      class="w-full btn-primary disabled:opacity-50"
    >
      {{ loading ? 'Loading...' : 'Refresh' }}
    </button>

    <div v-if="collections.length > 0" class="space-y-2">
      <div v-for="collection in collections" :key="collection.name" class="p-3 bg-gray-50 rounded">
        <p class="font-semibold">{{ collection.name }}</p>
        <p class="text-xs text-gray-600">Documents: {{ collection.document_count }}</p>
        <p class="text-xs text-gray-600">Size: {{ formatBytes(collection.size) }}</p>
      </div>
    </div>

    <p v-if="collections.length === 0 && !loading" class="text-gray-500 text-sm">
      No collections yet
    </p>

    <div v-if="error" class="p-3 bg-red-100 text-red-700 rounded text-sm">{{ error }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { collectionsAPI } from '../../api/collections'

const collections = ref<any[]>([])
const loading = ref(false)
const error = ref('')

const formatBytes = (bytes: number) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

const loadCollections = async () => {
  loading.value = true
  error.value = ''

  try {
    const response = await collectionsAPI.list()
    collections.value = response.collections
  } catch (err) {
    error.value = 'Failed to load collections'
  } finally {
    loading.value = false
  }
}

onMounted(() => loadCollections())
</script>
