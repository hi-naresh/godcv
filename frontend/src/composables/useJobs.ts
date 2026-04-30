import { useEditorStore, type JobState } from '../stores/editor'
import { detectRoleLevel } from './useRoleLevel'

export function useJobs() {
  const store = useEditorStore()

  function addJob(): string {
    return store.addJob()
  }

  function removeJob(id: string) {
    store.removeJob(id)
  }

  function updateJobDescription(id: string, jd: string) {
    const detected = detectRoleLevel(jd)
    const job = store.jobs.get(id)
    const updates: Partial<JobState> = { jobDescription: jd }
    if (detected && (!job?.roleLevel || job.roleLevel === null)) {
      updates.roleLevel = detected
    }
    store.updateJob(id, updates)
  }

  function setJobTitle(id: string, title: string) {
    store.updateJob(id, { title })
  }

  function setRoleLevel(id: string, level: string | null) {
    store.updateJob(id, { roleLevel: level as any })
  }

  function getJobList(): JobState[] {
    return [...store.jobs.values()]
  }

  return { addJob, removeJob, updateJobDescription, setJobTitle, setRoleLevel, getJobList }
}
