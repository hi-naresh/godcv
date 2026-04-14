<script setup lang="ts">
import { ref } from 'vue'
import { useEditorStore } from '../stores/editor'
import { useTailor } from '../composables/useTailor'

const store = useEditorStore()
const { startTailoring } = useTailor()
const jobDescription = ref('')
const apiKey = ref('')

function tailor() {
  if (!jobDescription.value.trim()) return alert('Paste a job description first.')
  if (!store.markdown.trim()) return alert('Load a resume first.')
  const key = apiKey.value.trim() || store.profile?.gemini_api_key || ''
  if (!key) return alert('Enter a Gemini API key.')
  startTailoring(jobDescription.value, key, store.markdown)
}
</script>

<template>
  <div class="job-input">
    <h3>AI Resume Tailoring</h3>
    <input v-model="apiKey" type="password" placeholder="Gemini API Key (or set in Profile)" class="api-key-input" />
    <textarea v-model="jobDescription" placeholder="Paste job description here..." class="jd-input" />
    <button @click="tailor" :disabled="store.tailoringStatus === 'running'" class="tailor-btn">
      {{ store.tailoringStatus === 'running' ? 'Tailoring...' : 'Tailor Resume to Job' }}
    </button>
  </div>
</template>

<style scoped>
.job-input { display: flex; flex-direction: column; gap: 8px; }
h3 { margin: 0; font-size: 0.95rem; }
.api-key-input {
  width: 100%; padding: 8px; border: 1px solid #d0d0d0;
  border-radius: 8px; font-size: 0.85rem;
}
.jd-input {
  width: 100%; min-height: 80px; resize: vertical; padding: 8px;
  border: 1px dashed #b9b9b9; border-radius: 8px; font-size: 0.85rem;
}
.tailor-btn {
  width: 100%; padding: 10px; font-weight: 600; border-radius: 8px;
  border: none; color: white; cursor: pointer;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.tailor-btn:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
