import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { SeniorityLevel } from '../composables/useSeniority'

export interface ToolCall {
  agent: string
  action: string
  entry?: string
  instructions?: string
  promote?: string[]
  demote?: string[]
}

export interface ScoreMetrics {
  keyword_match: number
  skills_coverage: number
  experience_fit: string
  overall_fit: number
}

export interface JobScoring {
  before: ScoreMetrics
  after: ScoreMetrics | null
  gap_suggestions: string[]
}

export interface ATSBreakdownItem {
  score: number
  detail: string
}

export interface ATSResult {
  ats_score: number
  breakdown: Record<string, ATSBreakdownItem>
  brutal_verdict: string
}

export interface Suggestion {
  id: string
  section: string
  type: 'skill' | 'bullet' | 'project' | 'remove' | 'replace'
  content: string
  old_content?: string
  skill_category?: string
  context: string
}

export interface JobAnalysis {
  job_title: string
  company: string
  position_level: string
  role_type: string
  key_requirements: string[]
  matched_strengths: string[]
}

export interface Profile {
  id: number
  name: string
  master_resume: string
  gemini_api_key: string
  page_mode: 'single' | 'multi'
  fabrication_mode: boolean
}

export interface JobState {
  id: string
  title: string
  jobDescription: string
  seniorityLevel: SeniorityLevel | null
  tailoringStatus: 'idle' | 'analyzing' | 'analyzed' | 'running' | 'done' | 'error'
  statusMessage: string | null
  tailoringPlan: ToolCall[] | null
  agentStatuses: Record<string, 'pending' | 'running' | 'done'>
  result: string | null
  error: string | null
  pageMode: 'single' | 'multi'
  analysis: JobAnalysis | null
  scoring: JobScoring | null
  atsResult: ATSResult | null
  suggestions: Suggestion[]
}

let _jobCounter = 0

export const useEditorStore = defineStore('editor', () => {
  const markdown = ref('')
  const profile = ref<Profile | null>(null)
  const jobs = ref<Map<string, JobState>>(new Map())
  const activeJobId = ref<string | null>(null)
  const pageMode = ref<'single' | 'multi'>('single')

  function addJob(): string {
    const id = `job-${++_jobCounter}`
    jobs.value.set(id, {
      id,
      title: '',
      jobDescription: '',
      seniorityLevel: null,
      tailoringStatus: 'idle',
      statusMessage: null,
      tailoringPlan: null,
      agentStatuses: {},
      result: null,
      error: null,
      pageMode: 'single',
      analysis: null,
      scoring: null,
      atsResult: null,
      suggestions: [],
    })
    jobs.value = new Map(jobs.value)
    return id
  }

  function removeJob(id: string) {
    jobs.value.delete(id)
    jobs.value = new Map(jobs.value)
    if (activeJobId.value === id) {
      activeJobId.value = null
    }
  }

  function updateJob(id: string, updates: Partial<JobState>) {
    const job = jobs.value.get(id)
    if (!job) return
    Object.assign(job, updates)
    jobs.value = new Map(jobs.value)
  }

  function resetJobTailoring(id: string) {
    updateJob(id, {
      tailoringStatus: 'idle',
      statusMessage: null,
      tailoringPlan: null,
      agentStatuses: {},
      result: null,
      error: null,
      analysis: null,
      scoring: null,
      atsResult: null,
      suggestions: [],
    })
  }

  return {
    markdown, profile, jobs, activeJobId, pageMode,
    addJob, removeJob, updateJob, resetJobTailoring,
  }
})
