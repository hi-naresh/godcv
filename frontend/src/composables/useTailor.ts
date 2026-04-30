import { useEditorStore } from '../stores/editor'
import { useToast } from './useToast'

export function useTailor() {
  const store = useEditorStore()
  const { show: showToast } = useToast()

  function startTailoring(jobId: string, apiKey?: string, resumeOverride?: string, analyzeOnly: boolean = false) {
    const job = store.jobs.get(jobId)
    if (!job) return

    // Check for API key before starting
    const key = apiKey || store.profile?.gemini_api_key || ''
    if (!key) {
      showToast(
        'No API key configured. Add your Gemini API key to use AI tailoring.',
        'warning',
        { label: 'Go to Preferences', route: '/preferences' },
        8000,
      )
      return
    }

    store.resetJobTailoring(jobId)
    store.updateJob(jobId, {
      tailoringStatus: analyzeOnly ? 'analyzing' : 'running',
      statusMessage: analyzeOnly ? 'Agent: Analyzing job requirements...' : 'Agent: Starting tailoring...',
    })

    const body: Record<string, any> = { job_description: job.jobDescription }
    if (apiKey) body.gemini_api_key = apiKey
    if (resumeOverride) body.resume_override = resumeOverride
    if (job.seniorityLevel) body.seniority_level = job.seniorityLevel
    if (analyzeOnly) body.analyze_only = true
    body.page_mode = store.pageMode

    fetch('/api/tailor', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(async (response) => {
      // Handle HTTP errors (400, 422, 500, etc.)
      if (!response.ok) {
        let message = `Server error (${response.status})`
        try {
          const errorData = await response.json()
          message = errorData.detail || errorData.message || message
        } catch {
          // Response wasn't JSON, use status text
          message = `${response.status}: ${response.statusText || 'Unknown error'}`
        }
        store.updateJob(jobId, { tailoringStatus: 'error', error: message })
        if (message.toLowerCase().includes('api key')) {
          showToast(message, 'error', { label: 'Go to Preferences', route: '/preferences' }, 8000)
        }
        return
      }

      const reader = response.body?.getReader()
      if (!reader) {
        store.updateJob(jobId, { tailoringStatus: 'error', error: 'No response stream available' })
        return
      }

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        let eventType = ''
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim()
          } else if (line.startsWith('data: ') && eventType) {
            try {
              const data = JSON.parse(line.slice(6))
              handleEvent(jobId, eventType, data)
            } catch (e) {
              console.warn(`[GodCV] Failed to parse SSE data for event "${eventType}":`, line.slice(6))
            }
            eventType = ''
          }
        }
      }

      // Stream ended — always clear status message
      const finalJob = store.jobs.get(jobId)
      if (finalJob) {
        store.updateJob(jobId, { statusMessage: null })
        if (finalJob.tailoringStatus === 'running' || finalJob.tailoringStatus === 'analyzing') {
          store.updateJob(jobId, {
            tailoringStatus: 'error',
            error: 'Connection closed before completing',
          })
        }
      }
    }).catch((err) => {
      const message = err instanceof TypeError
        ? 'Cannot connect to server. Is the backend running?'
        : (err.message || 'Unknown network error')
      store.updateJob(jobId, { tailoringStatus: 'error', statusMessage: null, error: message })
    })
  }

  function startBatchAnalysis(apiKey?: string, resumeOverride?: string) {
    for (const [jobId, job] of store.jobs) {
      if (job.jobDescription.trim()) {
        startTailoring(jobId, apiKey, resumeOverride, true)
      }
    }
  }

  function startBatchTailoring(apiKey?: string, resumeOverride?: string) {
    for (const [jobId, job] of store.jobs) {
      if (job.jobDescription.trim()) {
        startTailoring(jobId, apiKey, resumeOverride, false)
      }
    }
  }

  function handleEvent(jobId: string, event: string, data: Record<string, unknown>) {
    const job = store.jobs.get(jobId)
    if (!job) return

    switch (event) {
      case 'status':
        store.updateJob(jobId, { statusMessage: `Agent: ${data.message as string}` })
        break
      case 'plan': {
        const plan = data.tool_calls as any[]
        const analysis = data.analysis as Record<string, unknown> | undefined
        const rawScoring = data.scoring as any | undefined
        const statuses: Record<string, 'pending' | 'running' | 'done'> = {}
        for (const call of plan || []) {
          const key = call.entry ? `${call.agent}:${call.entry}` : call.agent
          if (call.action === 'keep' || call.action === 'include') {
            statuses[key] = 'done'
          } else if (call.action === 'exclude') {
            // Don't show excluded entries in status
          } else {
            statuses[key] = 'pending'
          }
        }
        const updates: Partial<typeof job> = { tailoringPlan: plan, agentStatuses: statuses }
        if (rawScoring) {
          updates.scoring = {
            before: rawScoring.before,
            after: null,
            gap_suggestions: rawScoring.gap_suggestions || [],
          }
        }
        if (analysis) {
          updates.analysis = {
            job_title: (analysis.job_title as string) || '',
            company: (analysis.company as string) || '',
            position_level: (analysis.position_level as string) || '',
            role_type: (analysis.role_type as string) || '',
            key_requirements: (analysis.key_requirements as string[]) || [],
            matched_strengths: (analysis.matched_strengths as string[]) || [],
          }
        }
        // Use AI-extracted job info if available and user hasn't manually set them
        if (analysis) {
          const aiTitle = analysis.job_title as string
          const aiCompany = analysis.company as string
          const aiPosition = analysis.position_level as string
          if (aiTitle && aiCompany && !job.title) {
            updates.title = `${aiTitle} @ ${aiCompany}`
          } else if (aiTitle && !job.title) {
            updates.title = aiTitle
          }
          if (aiPosition && !job.seniorityLevel) {
            updates.seniorityLevel = aiPosition as any
          }
        }
        store.updateJob(jobId, updates)
        break
      }
      case 'agent_start': {
        const agent = data.agent as string
        const statuses = { ...job.agentStatuses, [agent]: 'running' as const }
        store.updateJob(jobId, { agentStatuses: statuses, statusMessage: `Agent: Refining ${agent}...` })
        break
      }
      case 'agent_done': {
        const statuses = { ...job.agentStatuses, [data.agent as string]: 'done' as const }
        store.updateJob(jobId, { agentStatuses: statuses })
        break
      }
      case 'analysis_complete':
        store.updateJob(jobId, { tailoringStatus: 'analyzed', statusMessage: null })
        break
      case 'complete':
        store.updateJob(jobId, {
          tailoringStatus: 'done',
          statusMessage: null,
          result: data.markdown as string,
        })
        break
      case 'scoring_after':
        if (job.scoring) {
          store.updateJob(jobId, {
            scoring: { ...job.scoring, after: data as any },
          })
        }
        break
      case 'ats_score':
        store.updateJob(jobId, { atsResult: data as any })
        break
      case 'error':
        store.updateJob(jobId, {
          tailoringStatus: 'error',
          error: data.message as string || 'Unknown error from server',
        })
        break
    }
  }

  function analyzeJob(jobId: string, apiKey?: string, resumeOverride?: string) {
    startTailoring(jobId, apiKey, resumeOverride, true)
  }

  function tailorJob(jobId: string, apiKey?: string, resumeOverride?: string) {
    const job = store.jobs.get(jobId)
    if (!job) return

    // If we have an existing plan from analysis, use /execute to skip re-analysis
    if (job.tailoringPlan && job.analysis) {
      const existingPlan = {
        tool_calls: job.tailoringPlan,
        sections_unchanged: [],
        section_order: null,
        scoring: job.scoring ? { before: job.scoring.before, gap_suggestions: job.scoring.gap_suggestions } : {},
        analysis: job.analysis,
      }

      // Reset only tailoring artifacts, keep analysis
      store.updateJob(jobId, {
        tailoringStatus: 'running',
        statusMessage: 'Agent: Starting tailoring...',
        agentStatuses: {},
        result: null,
        error: null,
        atsResult: null,
      })

      const body: Record<string, any> = {
        job_description: job.jobDescription,
        plan: existingPlan,
      }
      if (apiKey) body.gemini_api_key = apiKey
      if (resumeOverride) body.resume_override = resumeOverride
      if (job.seniorityLevel) body.seniority_level = job.seniorityLevel

      fetch('/api/tailor/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      }).then(async (response) => {
        if (!response.ok) {
          let message = `Server error (${response.status})`
          try {
            const errorData = await response.json()
            message = errorData.detail || errorData.message || message
          } catch {
            message = `${response.status}: ${response.statusText || 'Unknown error'}`
          }
          store.updateJob(jobId, { tailoringStatus: 'error', statusMessage: null, error: message })
          return
        }

        const reader = response.body?.getReader()
        if (!reader) {
          store.updateJob(jobId, { tailoringStatus: 'error', statusMessage: null, error: 'No response stream' })
          return
        }

        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''
          let eventType = ''
          for (const line of lines) {
            if (line.startsWith('event: ')) {
              eventType = line.slice(7).trim()
            } else if (line.startsWith('data: ') && eventType) {
              try {
                const data = JSON.parse(line.slice(6))
                handleEvent(jobId, eventType, data)
              } catch (e) {
                console.warn(`[GodCV] Failed to parse SSE data for event "${eventType}"`)
              }
              eventType = ''
            }
          }
        }

        const finalJob = store.jobs.get(jobId)
        if (finalJob) {
          store.updateJob(jobId, { statusMessage: null })
          if (finalJob.tailoringStatus === 'running') {
            store.updateJob(jobId, { tailoringStatus: 'error', error: 'Connection closed' })
          }
        }
      }).catch((err) => {
        const message = err instanceof TypeError
          ? 'Cannot connect to server. Is the backend running?'
          : (err.message || 'Unknown network error')
        store.updateJob(jobId, { tailoringStatus: 'error', statusMessage: null, error: message })
      })
    } else {
      // No existing plan — run full tailoring
      startTailoring(jobId, apiKey, resumeOverride, false)
    }
  }

  return { startTailoring, startBatchAnalysis, startBatchTailoring, analyzeJob, tailorJob }
}
