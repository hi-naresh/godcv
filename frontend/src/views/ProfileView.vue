<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useProfile } from '../composables/useProfile'
import { useEditorStore } from '../stores/editor'

const store = useEditorStore()
const { fetchProfile, createProfile, updateProfile, fetchInsights, deleteInsight } = useProfile()

const name = ref('')
const resume = ref('')
const apiKey = ref('')
const insights = ref<any[]>([])
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
    insights.value = await fetchInsights()
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

async function removeInsight(id: number) {
  await deleteInsight(id)
  insights.value = insights.value.filter(i => i.id !== id)
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

    <div v-if="insights.length" class="insights">
      <h3>Learned Role Insights</h3>
      <div v-for="insight in insights" :key="insight.id" class="insight-card">
        <div class="insight-header">
          <strong>{{ insight.role_type }}</strong>
          <span class="count">{{ insight.tailoring_count }}x tailored</span>
          <button class="delete-btn" @click="removeInsight(insight.id)">Remove</button>
        </div>
        <div class="insight-body">
          <div v-if="insight.strongest_points?.length">
            <small>Strongest points:</small>
            <ul><li v-for="p in insight.strongest_points" :key="p">{{ p }}</li></ul>
          </div>
        </div>
      </div>
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
.insights { margin-top: 20px; }
.insights h3 { margin-bottom: 10px; }
.insight-card {
  background: #fff; border: 1px solid #e0e0e0; border-radius: 10px;
  padding: 12px; margin-bottom: 8px;
}
.insight-header { display: flex; align-items: center; gap: 10px; }
.count { color: #666; font-size: 0.8rem; }
.delete-btn {
  margin-left: auto; font-size: 0.75rem; background: none;
  border: 1px solid #ddd; border-radius: 6px; padding: 2px 8px; cursor: pointer;
  color: #dc3545;
}
.insight-body { margin-top: 6px; font-size: 0.85rem; }
.insight-body ul { margin: 4px 0 0 16px; }
</style>
