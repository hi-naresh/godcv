<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useEditorStore } from '../stores/editor'
import { useProfile } from '../composables/useProfile'
import PageModeToggle from '../components/PageModeToggle.vue'

const store = useEditorStore()
const { fetchProfile, updateProfile } = useProfile()

const apiKey = ref('')
const saving = ref(false)
const msg = ref('')

interface Usage {
  total_requests: number
  total_prompt_tokens: number
  total_completion_tokens: number
  total_tokens: number
  errors: number
  model: string
  rpm: number
  tpm: number
  rpd: number
  rate_limits: Record<string, string>
}
const usage = ref<Usage | null>(null)

interface ModelInfo {
  id: string
  displayName: string
  inputTokenLimit: number
  outputTokenLimit: number
}
const models = ref<ModelInfo[]>([])
const currentModel = ref('')
const modelsLoading = ref(false)

// Gemini free tier limits
const LIMITS = { rpm: 15, tpm: 1_000_000, rpd: 1500 }

onMounted(async () => {
  const p = await fetchProfile()
  if (p) {
    store.profile = p
    if (p.page_mode) store.pageMode = p.page_mode
    apiKey.value = p.gemini_api_key || ''
  }
  await Promise.all([loadUsage(), loadModels()])
})

async function loadUsage() {
  try {
    const res = await fetch('/api/usage')
    if (res.ok) usage.value = await res.json()
  } catch { /* ignore */ }
}

async function loadModels() {
  modelsLoading.value = true
  try {
    const res = await fetch('/api/models')
    if (res.ok) {
      const data = await res.json()
      models.value = data.models || []
      currentModel.value = data.current || ''
    }
  } catch { /* ignore */ }
  modelsLoading.value = false
}

async function selectModel(modelId: string) {
  await fetch('/api/models/select', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model: modelId }),
  })
  currentModel.value = modelId
  await loadUsage()
}

watch(() => store.pageMode, (val) => {
  if (store.profile) updateProfile({ page_mode: val })
})

async function saveApiKey() {
  saving.value = true
  try {
    const p = await updateProfile({ gemini_api_key: apiKey.value })
    store.profile = p
    msg.value = 'Saved!'
    setTimeout(() => msg.value = '', 2000)
    await loadModels()
  } finally {
    saving.value = false
  }
}

function fmt(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
  return String(n)
}

const activeModel = computed(() => models.value.find(m => m.id === currentModel.value))

function pct(used: number, limit: number): number {
  return limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 0
}

function barColor(p: number): string {
  if (p >= 90) return '#dc3545'
  if (p >= 70) return '#f0ad4e'
  return '#28a745'
}
</script>

<template>
  <div class="preferences-page">
    <h2>Preferences</h2>

    <div class="pref-card">
      <h3>Page Layout</h3>
      <p class="pref-desc">Single page auto-fits content. Multi-page allows unlimited content.</p>
      <PageModeToggle v-model="store.pageMode" />
    </div>

    <div class="pref-card">
      <h3>Gemini API Key</h3>
      <p class="pref-desc">Required for AI tailoring. Get a free key from <a href="https://aistudio.google.com/apikey" target="_blank">Google AI Studio</a>.</p>
      <div class="api-key-row">
        <input v-model="apiKey" type="password" placeholder="Paste your Gemini API key" class="pref-input" />
        <button class="save-btn" :disabled="saving" @click="saveApiKey">{{ saving ? 'Saving...' : 'Save' }}</button>
      </div>
      <span v-if="msg" class="msg">{{ msg }}</span>
      <div v-if="!apiKey" class="key-hint">No API key set. AI features won't work.</div>
    </div>

    <div class="pref-card">
      <h3>Model</h3>
      <p class="pref-desc">Select the Gemini model used for tailoring.</p>
      <div v-if="modelsLoading" class="loading">Loading models...</div>
      <div v-else-if="models.length === 0" class="pref-desc">No models available. Add an API key first.</div>
      <div v-else class="model-list">
        <div
          v-for="m in models"
          :key="m.id"
          :class="['model-card', { active: m.id === currentModel }]"
          @click="selectModel(m.id)"
        >
          <div class="model-header">
            <span class="model-name">{{ m.displayName }}</span>
            <span v-if="m.id === currentModel" class="model-badge">Active</span>
          </div>
          <div class="model-id">{{ m.id }}</div>
          <div class="model-limits">
            <span>Context: {{ fmt(m.inputTokenLimit) }}</span>
            <span>Max output: {{ fmt(m.outputTokenLimit) }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="pref-card">
      <h3>Usage &amp; Rate Limits</h3>
      <p class="pref-desc" v-if="usage">
        Model: <strong>{{ usage.model }}</strong>
        <template v-if="activeModel"> &mdash; {{ fmt(activeModel.inputTokenLimit) }} context window</template>
      </p>

      <div v-if="usage" class="limits-section">
        <div class="limit-row">
          <div class="limit-info">
            <span class="limit-name">Requests / min (RPM)</span>
            <span class="limit-nums">{{ usage.rpm }} / {{ LIMITS.rpm }}</span>
          </div>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: pct(usage.rpm, LIMITS.rpm) + '%', background: barColor(pct(usage.rpm, LIMITS.rpm)) }"></div>
          </div>
        </div>
        <div class="limit-row">
          <div class="limit-info">
            <span class="limit-name">Tokens / min (TPM)</span>
            <span class="limit-nums">{{ fmt(usage.tpm) }} / {{ fmt(LIMITS.tpm) }}</span>
          </div>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: pct(usage.tpm, LIMITS.tpm) + '%', background: barColor(pct(usage.tpm, LIMITS.tpm)) }"></div>
          </div>
        </div>
        <div class="limit-row">
          <div class="limit-info">
            <span class="limit-name">Requests / day (RPD)</span>
            <span class="limit-nums">{{ usage.rpd }} / {{ LIMITS.rpd }}</span>
          </div>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: pct(usage.rpd, LIMITS.rpd) + '%', background: barColor(pct(usage.rpd, LIMITS.rpd)) }"></div>
          </div>
        </div>
      </div>

      <div v-if="usage" class="usage-grid">
        <div class="usage-stat">
          <div class="usage-value">{{ usage.total_requests }}</div>
          <div class="usage-label">Total Requests</div>
        </div>
        <div class="usage-stat">
          <div class="usage-value">{{ fmt(usage.total_prompt_tokens) }}</div>
          <div class="usage-label">Prompt Tokens</div>
        </div>
        <div class="usage-stat">
          <div class="usage-value">{{ fmt(usage.total_completion_tokens) }}</div>
          <div class="usage-label">Completion Tokens</div>
        </div>
        <div class="usage-stat">
          <div class="usage-value">{{ fmt(usage.total_tokens) }}</div>
          <div class="usage-label">Total Tokens</div>
        </div>
        <div class="usage-stat" v-if="usage.errors > 0">
          <div class="usage-value error-val">{{ usage.errors }}</div>
          <div class="usage-label">Errors</div>
        </div>
      </div>

      <div v-if="!usage" class="pref-desc">Loading usage data...</div>
      <button v-if="usage" class="refresh-btn" @click="loadUsage">Refresh</button>
    </div>
  </div>
</template>

<style scoped>
.preferences-page { max-width: 650px; margin: 0 auto; }
h2 { margin-bottom: 16px; }
.pref-card {
  background: #fff; border: 1px solid #e0e0e0; border-radius: 12px;
  padding: 18px; margin-bottom: 12px;
}
.pref-card h3 { margin: 0 0 4px; font-size: 0.95rem; }
.pref-desc { color: #666; font-size: 0.82rem; margin: 0 0 12px; }
.pref-desc a { color: #0066cc; }
.pref-desc strong { color: #111; }
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
.key-hint {
  margin-top: 8px; padding: 8px 12px; background: #fff8e6; border: 1px solid #f0e0a0;
  border-radius: 8px; font-size: 0.8rem; color: #8a6d00;
}
.loading { color: #999; font-size: 0.85rem; }

/* Model selector */
.model-list {
  display: flex; flex-direction: column; gap: 6px;
  max-height: 240px; overflow-y: auto;
}
.model-card {
  border: 1px solid #e0e0e0; border-radius: 8px; padding: 10px 12px;
  cursor: pointer; transition: all 0.15s;
}
.model-card:hover { border-color: #999; }
.model-card.active { border-color: #111; background: #f5f5f5; }
.model-header { display: flex; align-items: center; justify-content: space-between; }
.model-name { font-weight: 700; font-size: 0.85rem; }
.model-badge {
  font-size: 0.65rem; font-weight: 700; background: #111; color: #fff;
  padding: 2px 8px; border-radius: 4px; text-transform: uppercase;
}
.model-id { font-size: 0.7rem; color: #999; font-family: ui-monospace, monospace; }
.model-limits { display: flex; gap: 12px; margin-top: 4px; font-size: 0.72rem; color: #666; }

/* Rate limits with progress bars */
.limits-section { margin-bottom: 14px; }
.limit-row { margin-bottom: 10px; }
.limit-info { display: flex; justify-content: space-between; margin-bottom: 3px; }
.limit-name { font-size: 0.78rem; font-weight: 600; color: #444; }
.limit-nums { font-size: 0.75rem; color: #888; font-family: ui-monospace, monospace; }
.progress-bar {
  height: 6px; background: #eee; border-radius: 3px; overflow: hidden;
}
.progress-fill {
  height: 100%; border-radius: 3px; transition: width 0.3s ease;
  min-width: 2px;
}

/* Usage stats */
.usage-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
  gap: 8px; margin-bottom: 10px;
}
.usage-stat {
  background: #f8f8f8; border-radius: 8px; padding: 10px; text-align: center;
}
.usage-value { font-size: 1.2rem; font-weight: 800; color: #111; }
.usage-value.error-val { color: #dc3545; }
.usage-label { font-size: 0.68rem; color: #888; margin-top: 2px; text-transform: uppercase; letter-spacing: 0.5px; }

.refresh-btn {
  margin-top: 6px; border: 1px solid #d0d0d0; background: #fff; border-radius: 6px;
  padding: 5px 14px; font-size: 0.78rem; font-weight: 600; cursor: pointer;
}
.refresh-btn:hover { background: #f5f5f5; }
</style>
