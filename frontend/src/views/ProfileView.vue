<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useProfile } from '../composables/useProfile'
import { useEditorStore } from '../stores/editor'
import SectionEditor from '../components/SectionEditor.vue'

const store = useEditorStore()
const { fetchProfile, createProfile, updateProfile } = useProfile()

const name = ref('')
const apiKey = ref('')
const resume = ref('')
const hasProfile = ref(false)
const saving = ref(false)
const msg = ref('')

onMounted(async () => {
  const p = await fetchProfile()
  if (p) {
    hasProfile.value = true
    name.value = p.name
    apiKey.value = p.gemini_api_key || ''
    resume.value = p.master_resume || ''
    store.profile = p
  }
})

function onResumeUpdate(md: string) {
  resume.value = md
}

async function save() {
  saving.value = true
  try {
    if (hasProfile.value) {
      const p = await updateProfile({
        name: name.value,
        master_resume: resume.value,
        gemini_api_key: apiKey.value,
      })
      store.profile = p
      if (store.markdown !== resume.value) store.markdown = resume.value
    } else {
      const p = await createProfile(name.value, resume.value, apiKey.value)
      store.profile = p
      store.markdown = resume.value
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
  <div class="profile-page">
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
    </div>

    <SectionEditor :markdown="resume" @update:markdown="onResumeUpdate" />

    <div class="save-bar">
      <button class="save-btn" @click="save" :disabled="saving">
        {{ saving ? 'Saving...' : 'Save Profile' }}
      </button>
      <span v-if="msg" class="msg">{{ msg }}</span>
    </div>
  </div>
</template>

<style scoped>
.profile-page {
  max-width: 800px; margin: 0 auto;
  display: flex; flex-direction: column; gap: 12px;
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
</style>
