<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useProfile } from '../composables/useProfile'
import { useEditorStore } from '../stores/editor'
import SectionEditor from '../components/SectionEditor.vue'
import ResumePreview from '../components/ResumePreview.vue'

const store = useEditorStore()
const { fetchProfile, createProfile, updateProfile } = useProfile()

const name = ref('')
const apiKey = ref('')
const hasProfile = ref(false)
const saving = ref(false)
const msg = ref('')
const loaded = ref(false)

const fontSize = computed(() => {
  const m = store.markdown.match(/font_size:\s*([\d.]+)/)
  return m ? m[1] : '11'
})
const lineSpacing = computed(() => {
  const m = store.markdown.match(/line_spacing:\s*([\d.]+)/)
  return m ? m[1] : '1.4'
})

onMounted(async () => {
  const p = await fetchProfile()
  if (p) {
    hasProfile.value = true
    name.value = p.name
    apiKey.value = p.gemini_api_key || ''
    if (!store.markdown) store.markdown = p.master_resume || ''
    store.profile = p
    if (p.page_mode) store.pageMode = p.page_mode
  }
  loaded.value = true
})

function onResumeUpdate(md: string) {
  store.markdown = md
}

function updateSetting(key: 'font_size' | 'line_spacing', val: string) {
  const regex = new RegExp(`(${key}:\\s*)[\\d.]+`)
  if (regex.test(store.markdown)) {
    store.markdown = store.markdown.replace(regex, `$1${val}`)
  }
}

async function save() {
  saving.value = true
  try {
    if (hasProfile.value) {
      const p = await updateProfile({
        name: name.value,
        master_resume: store.markdown,
        gemini_api_key: apiKey.value,
      })
      store.profile = p
    } else {
      const p = await createProfile(name.value, store.markdown, apiKey.value)
      store.profile = p
      hasProfile.value = true
    }
    msg.value = 'Profile saved!'
    setTimeout(() => msg.value = '', 2000)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="profile-layout">
    <!-- LEFT: Section Editor -->
    <div class="profile-left">
      <div class="profile-header-card">
        <h2>{{ hasProfile ? 'Edit Profile' : 'Create Profile' }}</h2>
        <div class="profile-fields">
          <div class="field">
            <label>Name</label>
            <input v-model="name" placeholder="Your name" />
          </div>
          <div class="field">
            <label>Gemini API Key</label>
            <input v-model="apiKey" type="password" placeholder="Gemini API Key" />
          </div>
        </div>
        <div class="profile-fields" style="margin-top: 8px;">
          <div class="field">
            <label>Font Size (pt)</label>
            <input type="number" :value="fontSize" @input="updateSetting('font_size', ($event.target as HTMLInputElement).value)" min="8" max="16" step="0.5" />
          </div>
          <div class="field">
            <label>Line Spacing</label>
            <input type="number" :value="lineSpacing" @input="updateSetting('line_spacing', ($event.target as HTMLInputElement).value)" min="1" max="2.5" step="0.1" />
          </div>
        </div>
      </div>

      <SectionEditor v-if="loaded" :markdown="store.markdown" @update:markdown="onResumeUpdate" />

      <div class="save-bar">
        <button class="save-btn" @click="save" :disabled="saving">
          {{ saving ? 'Saving...' : 'Save Profile' }}
        </button>
        <span v-if="msg" class="msg">{{ msg }}</span>
      </div>
    </div>

    <!-- RIGHT: Live Preview -->
    <div class="profile-right">
      <div class="preview-label">Preview</div>
      <ResumePreview
        v-if="store.markdown"
        :markdown="store.markdown"
        :pageMode="store.pageMode"
      />
      <div v-else class="empty-preview">
        <p>Fill in your resume to see a live preview</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.profile-layout {
  display: flex; align-items: flex-start; justify-content: center;
  gap: 18px; padding: 0 18px; max-width: 1400px; margin: 0 auto;
}

.profile-left {
  width: min(480px, 38vw); min-width: 340px;
  position: sticky; top: 60px; align-self: flex-start;
  display: flex; flex-direction: column; gap: 10px;
  max-height: calc(100vh - 80px); overflow-y: auto;
}

.profile-right {
  flex: 1; max-width: 240mm;
  position: sticky; top: 60px; align-self: flex-start;
  display: flex; flex-direction: column; gap: 8px;
}

.preview-label {
  font-size: 0.8rem; font-weight: 600; color: #999; text-transform: uppercase;
  letter-spacing: 0.5px;
}

.empty-preview {
  width: var(--page-w); min-height: 300px;
  background: #fff; border: 2px dashed #d9d9d9; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  color: #999; font-size: 0.85rem;
}

.profile-header-card {
  background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 16px;
}
.profile-header-card h2 { margin: 0 0 10px; }
.profile-fields { display: flex; gap: 12px; }
.field { flex: 1; display: flex; flex-direction: column; gap: 4px; }
.field label { font-weight: 600; font-size: 0.82rem; color: #555; }
.field input {
  padding: 8px; border: 1px solid #d0d0d0; border-radius: 8px; font-size: 0.85rem;
}

.save-bar {
  display: flex; align-items: center; gap: 10px;
  position: sticky; bottom: 12px;
  background: #fff; border: 1px solid #e0e0e0; border-radius: 12px;
  padding: 12px 16px; box-shadow: 0 -2px 8px rgba(0,0,0,.05);
}
.save-btn {
  padding: 10px 24px; font-weight: 700; border-radius: 8px;
  border: none; background: #111; color: #fff; cursor: pointer; font-size: 0.9rem;
}
.save-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.msg { color: #28a745; font-size: 0.85rem; }

@media (max-width: 900px) {
  .profile-layout { flex-direction: column; align-items: stretch; }
  .profile-left {
    width: 100%; min-width: unset; position: static;
    max-height: unset;
  }
  .profile-right { max-width: 100%; position: static; }
}
</style>
