import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useEditorStore } from '../stores/editor'

describe('editor store — jobs', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('adds a job', () => {
    const store = useEditorStore()
    store.addJob()
    expect(store.jobs.size).toBe(1)
    const job = [...store.jobs.values()][0]
    expect(job.tailoringStatus).toBe('idle')
  })

  it('removes a job', () => {
    const store = useEditorStore()
    store.addJob()
    const id = [...store.jobs.keys()][0]
    store.removeJob(id)
    expect(store.jobs.size).toBe(0)
  })

  it('isolates state between jobs', () => {
    const store = useEditorStore()
    store.addJob()
    store.addJob()
    const [id1, id2] = [...store.jobs.keys()]
    store.updateJob(id1, { tailoringStatus: 'running' })
    expect(store.jobs.get(id1)!.tailoringStatus).toBe('running')
    expect(store.jobs.get(id2)!.tailoringStatus).toBe('idle')
  })

  it('updates job fields', () => {
    const store = useEditorStore()
    store.addJob()
    const id = [...store.jobs.keys()][0]
    store.updateJob(id, { title: 'ML Engineer @ Google', roleLevel: 'non-graduate' })
    expect(store.jobs.get(id)!.title).toBe('ML Engineer @ Google')
    expect(store.jobs.get(id)!.roleLevel).toBe('non-graduate')
  })

  it('sets active job', () => {
    const store = useEditorStore()
    store.addJob()
    const id = [...store.jobs.keys()][0]
    store.activeJobId = id
    expect(store.activeJobId).toBe(id)
  })

  it('resets single job tailoring state', () => {
    const store = useEditorStore()
    store.addJob()
    const id = [...store.jobs.keys()][0]
    store.updateJob(id, { tailoringStatus: 'done', result: 'some result' })
    store.resetJobTailoring(id)
    expect(store.jobs.get(id)!.tailoringStatus).toBe('idle')
    expect(store.jobs.get(id)!.result).toBeNull()
  })
})
