export interface SavedCV {
  id: number
  profile_id: number
  name: string
  markdown: string
  job_title: string | null
  company: string | null
  created_at: string
}

export function useSavedCVs() {
  async function fetchSavedCVs(): Promise<SavedCV[]> {
    try {
      const res = await fetch('/api/saved-cvs')
      if (!res.ok) return []
      return await res.json()
    } catch { return [] }
  }

  async function saveCV(name: string, markdown: string, jobTitle?: string, company?: string): Promise<SavedCV> {
    const res = await fetch('/api/saved-cvs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, markdown, job_title: jobTitle || null, company: company || null }),
    })
    return res.json()
  }

  async function deleteCV(id: number): Promise<void> {
    await fetch(`/api/saved-cvs/${id}`, { method: 'DELETE' })
  }

  async function getCV(id: number): Promise<SavedCV | null> {
    try {
      const res = await fetch(`/api/saved-cvs/${id}`)
      if (!res.ok) return null
      return await res.json()
    } catch { return null }
  }

  return { fetchSavedCVs, saveCV, deleteCV, getCV }
}
