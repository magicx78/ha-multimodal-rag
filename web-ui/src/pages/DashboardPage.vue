<template>
  <div class="p-8">
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <!-- Upload Module -->
      <div class="card">
        <h2 class="text-xl font-bold mb-4">📤 Upload Documents</h2>
        <UploadModule />
      </div>

      <!-- Search Module -->
      <div class="card">
        <h2 class="text-xl font-bold mb-4">🔍 Search</h2>
        <SearchModule />
      </div>

      <!-- Reasoning Module -->
      <div class="card">
        <h2 class="text-xl font-bold mb-4">💭 Reasoning</h2>
        <ReasoningModule />
      </div>

      <!-- Collections Module -->
      <div class="card">
        <h2 class="text-xl font-bold mb-4">📚 Collections</h2>
        <CollectionsModule />
      </div>

      <!-- Info -->
      <div class="card md:col-span-2 lg:col-span-1">
        <h2 class="text-xl font-bold mb-4">ℹ️ About</h2>
        <p class="text-gray-600">Multimodal RAG v1.1.0</p>
        <p class="text-sm text-gray-500 mt-2">Web-UI for semantic search and AI reasoning</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import UploadModule from '../components/modules/UploadModule.vue'
import SearchModule from '../components/modules/SearchModule.vue'
import ReasoningModule from '../components/modules/ReasoningModule.vue'
import CollectionsModule from '../components/modules/CollectionsModule.vue'
</script>
