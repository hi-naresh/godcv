<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useEditorStore } from '../stores/editor'
import { useProfile } from '../composables/useProfile'
import PageModeToggle from '../components/PageModeToggle.vue'

const store = useEditorStore()
const { fetchProfile, updateProfile } = useProfile()

const apiKey = ref('')
const saving = ref(false)
const msg = ref('')

onMounted(async () => {
  const p = await fetchProfile()
  if (p) {
    store.profile = p
    if (p.page_mode) store.pageMode = p.page_mode
    apiKey.value = p.gemini_api_key || ''
  }
})

watch(() => store.pageMode, (val) => {
  if (store.profile) {
    updateProfile({ page_mode: val })
  }
})

async function saveApiKey() {
  saving.value = true
  try {
    const p = await updateProfile({ gemini_api_key: apiKey.value })
    store.profile = p
    msg.value = 'Saved!'
    setTimeout(() => msg.value = '', 2000)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="preferences-page">
    <h2>Preferences</h2>

    <div class="pref-card">
      <h3>Page Layout</h3>
      <p class="pref-desc">Choose whether the resume preview fits to a single page or flows across multiple pages.</p>
      <PageModeToggle v-model="store.pageMode" />
    </div>

    <div class="pref-card">
      <h3>Gemini API Key</h3>
      <p class="pref-desc">Used for AI-powered resume tailoring.</p>
      <div class="api-key-row">
        <input
          v-model="apiKey"
          type="password"
          placeholder="Paste your Gemini API key"
          class="pref-input"
        />
        <button class="save-btn" :disabled="saving" @click="saveApiKey">
          {{ saving ? 'Saving...' : 'Save' }}
        </button>
      </div>
      <span v-if="msg" class="msg">{{ msg }}</span>
    </div>
  </div>
</template>

<style scoped>
.preferences-page { max-width: 600px; margin: 0 auto; }
h2 { margin-bottom: 16px; }
.pref-card {
  background: #fff; border: 1px solid #e0e0e0; border-radius: 12px;
  padding: 18px; margin-bottom: 12px;
}
.pref-card h3 { margin: 0 0 4px; font-size: 0.95rem; }
.pref-desc { color: #666; font-size: 0.82rem; margin: 0 0 12px; }
.api-key-row { display: flex; gap: 8px; }
.pref-input {
  flex: 1; padding: 8px 10px; border: 1px solid #d0d0d0; border-radius: 8px;
  font-size: 0.85rem;
}
.save-btn {
  padding: 8px 18px; border: none; background: #111; color: #fff;
  border-radius: 8px; font-weight: 600; font-size: 0.82rem; cursor: pointer;
}
.save-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.msg { color: #28a745; font-size: 0.82rem; margin-top: 4px; display: block; }
</style>
