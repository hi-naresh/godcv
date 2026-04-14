export type SeniorityLevel = 'graduate' | 'junior' | 'mid-level' | 'senior' | 'lead' | 'principal'

export function detectSeniority(jobDescription: string): SeniorityLevel | null {
  const text = jobDescription.toLowerCase()

  if (/\b(principal|staff)\b/.test(text)) return 'principal'
  if (
    /\b(lead|head|manager)\b.*\b(engineer|developer|team)\b/.test(text) ||
    /\b(engineer|developer)\b.*\b(lead|head)\b/.test(text) ||
    /\btech(?:nical)?\s+lead\b/.test(text) ||
    /\blead\s+(?:software|backend|frontend|full\s*stack)\b/.test(text)
  ) return 'lead'
  if (/\bsenior\b/.test(text)) return 'senior'
  if (/\bjunior\b/.test(text)) return 'junior'
  if (/\b(?:graduate|grad|entry[\s-]level|new\s+grad|intern(?:ship)?|trainee)\b/.test(text)) return 'graduate'

  const yearsMatch = text.match(/(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)/)
  if (yearsMatch) {
    const years = parseInt(yearsMatch[1])
    if (years <= 1) return 'graduate'
    if (years <= 2) return 'junior'
    if (years <= 5) return 'mid-level'
    return 'senior'
  }

  const rangeMatch = text.match(/(\d+)\s*[-–]\s*(\d+)\s*(?:years?|yrs?)/)
  if (rangeMatch) {
    const upper = parseInt(rangeMatch[2])
    if (upper <= 2) return 'junior'
    if (upper <= 5) return 'mid-level'
    return 'senior'
  }

  return null
}

export const SENIORITY_OPTIONS: SeniorityLevel[] = [
  'graduate', 'junior', 'mid-level', 'senior', 'lead', 'principal'
]
