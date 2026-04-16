export type SectionType = 'experience' | 'education' | 'skills' | 'projects' | 'generic'

export interface EntryData {
  key: string
  header: string          // kept for generic fallback
  content: string         // bullet points

  // Experience / Education
  role?: string
  company?: string
  degree?: string
  university?: string
  startDate?: string
  endDate?: string

  // Projects
  name?: string
  url?: string
  techStack?: string[]

  // Skills
  categoryName?: string
  skills?: string[]
}

const SECTION_MAP: Record<string, SectionType> = {
  experience: 'experience',
  education: 'education',
  skills: 'skills',
  projects: 'projects',
}

export function getSectionType(name: string): SectionType {
  return SECTION_MAP[name.toLowerCase()] ?? 'generic'
}

export function isMultiEntryType(type: SectionType): boolean {
  return type === 'experience' || type === 'education' || type === 'projects'
}

/**
 * Parse experience-section markdown into structured entries.
 *
 * Expected format per entry:
 *   **Role — Company**  *Start – End*
 *   - bullet 1
 *   - bullet 2
 *
 * Separators between role and company: em-dash (—), en-dash (–), or hyphen (-).
 * Dates in italics with en-dash separator.
 */
export function parseExperienceEntries(content: string): EntryData[] {
  const lines = content.split('\n')
  const entries: EntryData[] = []
  let current: EntryData | null = null
  let contentLines: string[] = []

  function flushCurrent() {
    if (current) {
      current.content = contentLines.join('\n').trim()
      entries.push(current)
      current = null
      contentLines = []
    }
  }

  for (const line of lines) {
    // Check if this line starts a new entry (begins with **)
    if (line.startsWith('**')) {
      flushCurrent()

      // Try to parse structured header: **Role — Company** *dates*
      // The bold part: everything between first ** and next **
      const headerMatch = line.match(/^\*\*(.+?)\*\*\s*(.*)$/)
      if (headerMatch) {
        const boldPart = headerMatch[1]
        const rest = headerMatch[2]

        // Split role and company on em-dash, en-dash, or hyphen (with spaces)
        const separatorMatch = boldPart.match(/^(.+?)\s*[—–-]\s+(.+)$/)

        // Parse dates from rest: *Start – End*
        let startDate: string | undefined
        let endDate: string | undefined
        const dateMatch = rest.match(/\*(.+?)\s*[–—-]\s*(.+?)\*/)
        if (dateMatch) {
          startDate = dateMatch[1].trim()
          endDate = dateMatch[2].trim()
        }

        if (separatorMatch) {
          current = {
            key: String(entries.length + 1),
            header: '',
            content: '',
            role: separatorMatch[1].trim(),
            company: separatorMatch[2].trim(),
            startDate,
            endDate,
          }
        } else {
          // Bold text with no separator — generic entry with header
          current = {
            key: String(entries.length + 1),
            header: line,
            content: '',
          }
        }
      } else {
        // Malformed bold — treat as generic
        current = {
          key: String(entries.length + 1),
          header: line,
          content: '',
        }
      }
    } else if (current) {
      // Content line belonging to current entry
      contentLines.push(line)
    } else if (line.trim() !== '') {
      // No current entry and line doesn't start with ** — generic fallback
      flushCurrent()
      current = {
        key: String(entries.length + 1),
        header: line,
        content: '',
      }
    }
  }

  flushCurrent()
  return entries
}

/**
 * Reassemble structured experience entries into markdown.
 */
export function assembleExperienceEntries(entries: EntryData[]): string {
  return entries
    .map((entry) => {
      if (entry.role && entry.company) {
        let header = `**${entry.role} — ${entry.company}**`
        if (entry.startDate && entry.endDate) {
          header += ` *${entry.startDate} – ${entry.endDate}*`
        }
        if (entry.content) {
          return `${header}\n${entry.content}`
        }
        return header
      }
      // Generic fallback
      if (entry.content) {
        return `${entry.header}\n${entry.content}`
      }
      return entry.header
    })
    .join('\n\n')
}
