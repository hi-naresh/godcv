import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface ToolCall {
  agent: string
  action: string
  entry?: string
  instructions?: string
  promote?: string[]
  demote?: string[]
}

export interface Profile {
  id: number
  name: string
  master_resume: string
  gemini_api_key: string
}

export const useEditorStore = defineStore('editor', () => {
  const markdown = ref('')
  const profile = ref<Profile | null>(null)
  const tailoringStatus = ref<'idle' | 'running' | 'done' | 'error'>('idle')
  const tailoringPlan = ref<ToolCall[] | null>(null)
  const agentStatuses = ref<Record<string, 'pending' | 'running' | 'done'>>({})
  const tailoringResult = ref<string | null>(null)
  const error = ref<string | null>(null)

  function resetTailoring() {
    tailoringStatus.value = 'idle'
    tailoringPlan.value = null
    agentStatuses.value = {}
    tailoringResult.value = null
    error.value = null
  }

  return {
    markdown, profile,
    tailoringStatus, tailoringPlan, agentStatuses, tailoringResult, error,
    resetTailoring,
  }
})
