<template>
  <div class="space-y-4">
    <div class="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center cursor-pointer hover:border-blue-500 transition"
         @click="$refs.fileInput.click()"
         @drop="handleDrop"
         @dragover.prevent
         @dragenter.prevent>
      <input
        ref="fileInput"
        type="file"
        class="hidden"
        @change="handleFileSelect"
      />
      <p class="text-gray-600">Drop file here or click to select</p>
    </div>

    <select v-model="selectedCollection" class="input-field">
      <option value="">Select Collection</option>
      <option value="default">Default</option>
    </select>

    <button
      @click="handleUpload"
      :disabled="!selectedFile || !selectedCollection || uploading"
      class="w-full btn-primary disabled:opacity-50"
    >
      {{ uploading ? 'Uploading...' : 'Upload' }}
    </button>

    <div v-if="progress" class="w-full bg-gray-200 rounded-full h-2">
      <div class="bg-blue-600 h-2 rounded-full" :style="{ width: progress + '%' }"></div>
    </div>

    <div v-if="message" :class="['p-3 rounded text-sm', messageType === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700']">
      {{ message }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { uploadAPI } from '../../api/upload'

const fileInput = ref<HTMLInputElement>()
const selectedFile = ref<File | null>(null)
const selectedCollection = ref('')
const uploading = ref(false)
const progress = ref(0)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')

const handleFileSelect = (e: Event) => {
  const target = e.target as HTMLInputElement
  selectedFile.value = target.files?.[0] || null
}

const handleDrop = (e: DragEvent) => {
  e.preventDefault()
  selectedFile.value = e.dataTransfer?.files?.[0] || null
}

const handleUpload = async () => {
  if (!selectedFile.value || !selectedCollection.value) return

  uploading.value = true
  progress.value = 0

  try {
    await uploadAPI.upload(selectedFile.value, selectedCollection.value)
    message.value = 'File uploaded successfully!'
    messageType.value = 'success'
    selectedFile.value = null
    progress.value = 100
    setTimeout(() => { progress.value = 0; message.value = '' }, 3000)
  } catch (error) {
    message.value = 'Upload failed. Please try again.'
    messageType.value = 'error'
  } finally {
    uploading.value = false
  }
}
</script>
