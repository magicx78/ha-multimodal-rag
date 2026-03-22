<template>
  <div class="space-y-4">
    <input
      v-model="query"
      type="text"
      class="input-field"
      placeholder="Enter search query..."
      @keyup.enter="handleSearch"
    />

    <button
      @click="handleSearch"
      :disabled="!query || searching"
      class="w-full btn-primary disabled:opacity-50"
    >
      {{ searching ? 'Searching...' : 'Search' }}
    </button>

    <div v-if="results.length > 0" class="space-y-2">
      <div v-for="result in results" :key="result.source" class="p-3 bg-gray-50 rounded">
        <p class="text-sm"><strong>Score:</strong> {{ result.score.toFixed(2) }}</p>
        <p class="text-sm mt-1">{{ result.text.substring(0, 100) }}...</p>
        <p class="text-xs text-gray-500 mt-1">Source: {{ result.source }}</p>
      </div>
    </div>

    <div v-if="error" class="p-3 bg-red-100 text-red-700 rounded text-sm">{{ error }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { searchAPI } from '../../api/search'

const query = ref('')
const searching = ref(false)
const results = ref<any[]>([])
const error = ref('')

const handleSearch = async () => {
  if (!query.value) return

  searching.value = true
  error.value = ''

  try {
    const response = await searchAPI.search({
      query: query.value,
      collection_name: 'default'
    })
    results.value = response.results
  } catch (err) {
    error.value = 'Search failed'
  } finally {
    searching.value = false
  }
}
</script>
