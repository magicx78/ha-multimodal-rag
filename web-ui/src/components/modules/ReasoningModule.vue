<template>
  <div class="space-y-4">
    <textarea
      v-model="question"
      class="input-field h-24 resize-none"
      placeholder="Ask a question..."
    ></textarea>

    <button
      @click="handleReason"
      :disabled="!question || reasoning"
      class="w-full btn-primary disabled:opacity-50"
    >
      {{ reasoning ? 'Thinking...' : 'Ask' }}
    </button>

    <div v-if="answer" class="p-4 bg-blue-50 rounded">
      <p class="font-semibold mb-2">Answer:</p>
      <p class="text-sm">{{ answer }}</p>
      <div v-if="sources.length > 0" class="mt-3 pt-3 border-t">
        <p class="text-xs font-semibold text-gray-600">Sources:</p>
        <ul class="text-xs text-gray-600 mt-1">
          <li v-for="source in sources" :key="source">• {{ source }}</li>
        </ul>
      </div>
    </div>

    <div v-if="error" class="p-3 bg-red-100 text-red-700 rounded text-sm">{{ error }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { reasoningAPI } from '../../api/reasoning'

const question = ref('')
const reasoning = ref(false)
const answer = ref('')
const sources = ref<string[]>([])
const error = ref('')

const handleReason = async () => {
  if (!question.value) return

  reasoning.value = true
  error.value = ''

  try {
    const response = await reasoningAPI.reason({
      question: question.value,
      collection_name: 'default'
    })
    answer.value = response.answer
    sources.value = response.sources
  } catch (err) {
    error.value = 'Reasoning failed'
  } finally {
    reasoning.value = false
  }
}
</script>
