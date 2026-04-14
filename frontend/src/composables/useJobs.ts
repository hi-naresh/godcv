import { useEditorStore, type JobState } from '../stores/editor'
import { detectSeniority } from './useSeniority'

export function useJobs() {
  const store = useEditorStore()

  function addJob(): string {
    return store.addJob()
  }

  function removeJob(id: string) {
    store.removeJob(id)
  }

  function updateJobDescription(id: string, jd: string) {
    const detected = detectSeniority(jd)
    const job = store.jobs.get(id)
    const updates: Partial<JobState> = { jobDescription: jd }
    if (detected && (!job?.seniorityLevel || job.seniorityLevel === null)) {
      updates.seniorityLevel = detected
    }
    store.updateJob(id, updates)
  }

  function setJobTitle(id: string, title: string) {
    store.updateJob(id, { title })
  }

  function setJobSeniority(id: string, level: string | null) {
    store.updateJob(id, { seniorityLevel: level as any })
  }

  function getJobList(): JobState[] {
    return [...store.jobs.values()]
  }

  return { addJob, removeJob, updateJobDescription, setJobTitle, setJobSeniority, getJobList }
}
