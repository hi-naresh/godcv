import { useEditorStore } from '../stores/editor'

export function useTailor() {
  const store = useEditorStore()

  function startTailoring(jobDescription: string, apiKey?: string, resumeOverride?: string) {
    store.resetTailoring()
    store.tailoringStatus = 'running'

    const body: Record<string, string> = { job_description: jobDescription }
    if (apiKey) body.gemini_api_key = apiKey
    if (resumeOverride) body.resume_override = resumeOverride

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
              handleEvent(eventType, data)
            } catch {}
            eventType = ''
          }
        }
      }
    }).catch((err) => {
      store.tailoringStatus = 'error'
      store.error = err.message
    })
  }

  function handleEvent(event: string, data: Record<string, unknown>) {
    switch (event) {
      case 'plan':
        store.tailoringPlan = data.tool_calls as any[]
        for (const call of store.tailoringPlan || []) {
          const key = call.entry ? `${call.agent}:${call.entry}` : call.agent
          store.agentStatuses[key] = call.action === 'keep' ? 'done' : 'pending'
        }
        break
      case 'agent_start':
        store.agentStatuses[data.agent as string] = 'running'
        break
      case 'agent_done':
        store.agentStatuses[data.agent as string] = 'done'
        break
      case 'complete':
        store.tailoringStatus = 'done'
        store.tailoringResult = data.markdown as string
        store.markdown = data.markdown as string
        break
      case 'error':
        store.tailoringStatus = 'error'
        store.error = data.message as string
        break
    }
  }

  return { startTailoring }
}
