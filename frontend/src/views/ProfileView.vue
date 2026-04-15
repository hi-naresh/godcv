<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useProfile } from '../composables/useProfile'
import { useEditorStore } from '../stores/editor'

const store = useEditorStore()
const { fetchProfile, createProfile, updateProfile } = useProfile()

const name = ref('')
const resume = ref('')
const apiKey = ref('')
const hasProfile = ref(false)
const saving = ref(false)
const msg = ref('')

onMounted(async () => {
  const p = await fetchProfile()
  if (p) {
    hasProfile.value = true
    name.value = p.name
    resume.value = p.master_resume
    apiKey.value = p.gemini_api_key || ''
    store.profile = p
  }
})

async function save() {
  saving.value = true
  try {
    if (hasProfile.value) {
      const p = await updateProfile({ name: name.value, master_resume: resume.value, gemini_api_key: apiKey.value })
      store.profile = p
    } else {
      const p = await createProfile(name.value, resume.value, apiKey.value)
      store.profile = p
      hasProfile.value = true
    }
    msg.value = 'Profile saved!'
    setTimeout(() => msg.value = '', 2000)
  } finally { saving.value = false }
}

</script>

<template>
  <div class="profile-page">
    <div class="profile-form">
      <h2>{{ hasProfile ? 'Edit Profile' : 'Create Profile' }}</h2>
      <label>Name</label>
      <input v-model="name" placeholder="Your name" />
      <label>Gemini API Key</label>
      <input v-model="apiKey" type="password" placeholder="Gemini API Key" />
      <label>Master Resume (Markdown)</label>
      <textarea v-model="resume" placeholder="Paste your full resume markdown here..." rows="20" />
      <button @click="save" :disabled="saving">{{ saving ? 'Saving...' : 'Save Profile' }}</button>
      <span v-if="msg" class="msg">{{ msg }}</span>
    </div>

  </div>
</template>

<style scoped>
.profile-page { max-width: 800px; margin: 0 auto; }
.profile-form {
  background: #fff; padding: 20px; border-radius: 12px;
  border: 1px solid #d9d9d9; display: flex; flex-direction: column; gap: 8px;
}
.profile-form label { font-weight: 600; font-size: 0.85rem; margin-top: 4px; }
.profile-form input, .profile-form textarea {
  width: 100%; padding: 8px; border: 1px solid #d0d0d0; border-radius: 8px;
  font-size: 0.9rem;
}
.profile-form textarea { font-family: ui-monospace, monospace; font-size: 0.8rem; }
.profile-form button {
  padding: 10px; font-weight: 600; border-radius: 8px;
  border: none; background: #111; color: #fff; cursor: pointer;
}
.msg { color: #28a745; font-size: 0.85rem; }
</style>
