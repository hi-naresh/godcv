import { ref } from 'vue'
import type { Profile } from '../stores/editor'

export function useProfile() {
  const loading = ref(false)

  async function fetchProfile(): Promise<Profile | null> {
    try {
      const res = await fetch('/api/profile')
      if (res.status === 404) return null
      return await res.json()
    } catch { return null }
  }

  async function createProfile(name: string, masterResume: string, apiKey: string = ''): Promise<Profile> {
    const res = await fetch('/api/profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, master_resume: masterResume, gemini_api_key: apiKey }),
    })
    return res.json()
  }

  async function updateProfile(data: Partial<{
    name: string
    master_resume: string
    gemini_api_key: string
    page_mode: string
    stealth_mode: boolean
    max_projects: number
    max_bullets_per_entry: number
    require_quantified_bullets: boolean
  }>): Promise<Profile> {
    const res = await fetch('/api/profile', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return res.json()
  }

  async function fetchInsights() {
    const res = await fetch('/api/profile/insights')
    return res.json()
  }

  async function deleteInsight(id: number) {
    await fetch(`/api/profile/insights/${id}`, { method: 'DELETE' })
  }

  return { loading, fetchProfile, createProfile, updateProfile, fetchInsights, deleteInsight }
}
