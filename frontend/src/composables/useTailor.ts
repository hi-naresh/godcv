import { useEditorStore } from '../stores/editor'

export function useTailor() {
  const store = useEditorStore()

  function startTailoring(jobId: string, apiKey?: string, resumeOverride?: string) {
    const job = store.jobs.get(jobId)
    if (!job) return

    store.resetJobTailoring(jobId)
    store.updateJob(jobId, { tailoringStatus: 'running' })

    const body: Record<string, string> = { job_description: job.jobDescription }
    if (apiKey) body.gemini_api_key = apiKey
    if (resumeOverride) body.resume_override = resumeOverride
    if (job.seniorityLevel) body.seniority_level = job.seniorityLevel

    fetch('/api/tailor', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(async (response) => {
      const reader = response.body?.getReader()
      if (!reader) return
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
            } catch {}
            eventType = ''
          }
        }
      }
    }).catch((err) => {
      store.updateJob(jobId, { tailoringStatus: 'error', error: err.message })
    })
  }

  function startBatchTailoring(apiKey?: string, resumeOverride?: string) {
    for (const [jobId, job] of store.jobs) {
      if (job.jobDescription.trim()) {
        startTailoring(jobId, apiKey, resumeOverride)
      }
    }
  }

  function handleEvent(jobId: string, event: string, data: Record<string, unknown>) {
    const job = store.jobs.get(jobId)
    if (!job) return

    switch (event) {
      case 'plan': {
        const plan = data.tool_calls as any[]
        const statuses: Record<string, 'pending' | 'running' | 'done'> = {}
        for (const call of plan || []) {
          const key = call.entry ? `${call.agent}:${call.entry}` : call.agent
          statuses[key] = call.action === 'keep' ? 'done' : 'pending'
        }
        store.updateJob(jobId, { tailoringPlan: plan, agentStatuses: statuses })
        break
      }
      case 'agent_start': {
        const statuses = { ...job.agentStatuses, [data.agent as string]: 'running' as const }
        store.updateJob(jobId, { agentStatuses: statuses })
        break
      }
      case 'agent_done': {
        const statuses = { ...job.agentStatuses, [data.agent as string]: 'done' as const }
        store.updateJob(jobId, { agentStatuses: statuses })
        break
      }
      case 'complete':
        store.updateJob(jobId, {
          tailoringStatus: 'done',
          result: data.markdown as string,
        })
        break
      case 'error':
        store.updateJob(jobId, {
          tailoringStatus: 'error',
          error: data.message as string,
        })
        break
    }
  }

  return { startTailoring, startBatchTailoring }
}
