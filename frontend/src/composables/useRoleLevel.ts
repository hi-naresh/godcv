export type RoleLevel = 'graduate' | 'non-graduate'

export function detectRoleLevel(jobDescription: string): RoleLevel | null {
  const text = jobDescription.toLowerCase()

  if (/\b(principal|staff)\b/.test(text)) return 'non-graduate'
  if (/\b(lead|head|manager)\b.*\b(engineer|developer|team)\b/.test(text)
    || /\b(engineer|developer)\b.*\b(lead|head)\b/.test(text)
    || /\btech(nical)?\s+lead\b/.test(text)
    || /\blead\s+(software|backend|frontend|full\s*stack)\b/.test(text)) {
    return 'non-graduate'
  }
  if (/\bsenior\b/.test(text)) return 'non-graduate'
  if (/\bjunior\b/.test(text)) return 'graduate'
  if (/\b(graduate|grad|entry[\s-]level|new\s+grad|intern(ship)?|trainee)\b/.test(text)) {
    return 'graduate'
  }

  const yearsMatch = text.match(/(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)/)
  if (yearsMatch) {
    const years = parseInt(yearsMatch[1], 10)
    return years <= 2 ? 'graduate' : 'non-graduate'
  }
  const rangeMatch = text.match(/(\d+)\s*[-–]\s*(\d+)\s*(?:years?|yrs?)/)
  if (rangeMatch) {
    const upper = parseInt(rangeMatch[2], 10)
    return upper <= 2 ? 'graduate' : 'non-graduate'
  }

  return null
}

/**
 * Extract a job title from JD text. Looks for common patterns like
 * "Role Title - Company" or "Role Title at Company" in the first few lines.
 */
export function detectJobTitle(jobDescription: string): string | null {
  const lines = jobDescription.trim().split('\n').slice(0, 5)
  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.length > 120) continue

    // "Role - Company" or "Role at Company" or "Role | Company" or "Role @ Company"
    const match = trimmed.match(/^(.+?)\s*(?:[-–—|@]|at|,)\s*(.+)$/i)
    if (match) {
      const role = match[1].trim()
      const company = match[2].trim().split(/[.,;(]/)[0].trim()
      // Filter out lines that are clearly not titles
      if (role.split(' ').length <= 8 && company.split(' ').length <= 6) {
        return `${role} @ ${company}`
      }
    }

    // Just a short title line by itself (< 60 chars, first line)
    if (trimmed.length < 60 && lines.indexOf(line) === 0 && /engineer|developer|designer|manager|analyst|scientist|lead/i.test(trimmed)) {
      return trimmed
    }
  }
  return null
}
