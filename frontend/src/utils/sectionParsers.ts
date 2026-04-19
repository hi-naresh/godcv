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

  // Experience stack
  stackUsed?: string[]

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
  return type === 'experience' || type === 'education' || type === 'projects' || type === 'skills'
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
    // Check for **Stack Used:** line (must be checked before new-entry detection since it also starts with **)
    const stackLine = current ? line.match(/^\*\*Stack Used:\*\*\s*(.+)$/) : null
    if (stackLine && current) {
      current.stackUsed = stackLine[1].split(',').map((s) => s.trim()).filter(Boolean)
    } else if (line.startsWith('**')) {
      flushCurrent()

      // Try to parse structured header: **Role — Company** *dates*
      // The bold part: everything between first ** and next **
      const headerMatch = line.match(/^\*\*(.+?)\*\*\s*(.*)$/)
      if (headerMatch) {
        const boldPart = headerMatch[1]
        const rest = headerMatch[2]

        // Split role and company on em-dash, en-dash, or hyphen (with spaces)
        const separatorMatch = boldPart.match(/^(.+?)\s*[—–-]\s+(.+)$/)

        // Parse dates from rest: **Start – End** or *Start – End*
        let startDate: string | undefined
        let endDate: string | undefined
        const dateMatch = rest.match(/\*{1,2}(.+?)\s*[–—-]\s*(.+?)\*{1,2}/)
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
        const parts = [header]
        if (entry.stackUsed && entry.stackUsed.length > 0) {
          parts.push(`**Stack Used:** ${entry.stackUsed.join(', ')}`)
        }
        if (entry.content) {
          parts.push(entry.content)
        }
        return parts.map((p, i) => i < parts.length - 1 ? p + '  ' : p).join('\n')
      }
      // Generic fallback
      if (entry.content) {
        return `${entry.header}\n${entry.content}`
      }
      return entry.header
    })
    .join('\n\n')
}

/**
 * Parse education-section markdown into structured entries.
 *
 * Expected format per entry:
 *   **Degree - University** *Start – End*
 *   coursework / content lines
 */
export function parseEducationEntries(content: string): EntryData[] {
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

  for (const rawLine of lines) {
    const line = rawLine.trimEnd()

    // New entry starts with ** but NOT *** (which is bold+italic content like ***Coursework**:*)
    if (line.startsWith('**') && !line.startsWith('***')) {
      flushCurrent()

      const headerMatch = line.match(/^\*\*(.+?)\*\*\s*(.*)$/)
      if (headerMatch) {
        const boldPart = headerMatch[1]
        const rest = headerMatch[2]

        // Split degree and university on " - " or " – "
        const separatorMatch = boldPart.match(/^(.+?)\s*[-–]\s+(.+)$/)

        let startDate: string | undefined
        let endDate: string | undefined
        const dateMatch = rest.match(/\*{1,2}(.+?)\s*[–—-]\s*(.+?)\*{1,2}/)
        if (dateMatch) {
          startDate = dateMatch[1].trim()
          endDate = dateMatch[2].trim()
        }

        if (separatorMatch) {
          current = {
            key: String(entries.length + 1),
            header: '',
            content: '',
            degree: separatorMatch[1].trim(),
            university: separatorMatch[2].trim(),
            startDate,
            endDate,
          }
        } else {
          current = {
            key: String(entries.length + 1),
            header: line,
            content: '',
          }
        }
      } else {
        current = {
          key: String(entries.length + 1),
          header: line,
          content: '',
        }
      }
    } else if (current) {
      contentLines.push(rawLine)
    } else if (line.trim() !== '') {
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
 * Reassemble structured education entries into markdown.
 */
export function assembleEducationEntries(entries: EntryData[]): string {
  return entries
    .map((entry) => {
      if (entry.degree && entry.university) {
        let header = `**${entry.degree} - ${entry.university}**`
        if (entry.startDate && entry.endDate) {
          header += ` *${entry.startDate} – ${entry.endDate}*`
        }
        if (entry.content) {
          return `${header}\n\n${entry.content}`
        }
        return header
      }
      if (entry.content) {
        return `${entry.header}\n\n${entry.content}`
      }
      return entry.header
    })
    .join('\n\n')
}

/**
 * Parse projects-section markdown into structured entries.
 *
 * Formats:
 *   **[Name](url)** at Company **| Stack -** tech1, tech2
 *   **Name** at Company **| Stack -** tech1, tech2
 *   **[Name](url)** | Stack - tech1, tech2
 */
export function parseProjectEntries(content: string): EntryData[] {
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
    if (line.startsWith('**')) {
      flushCurrent()

      let name: string | undefined
      let url: string | undefined
      let techStack: string[] | undefined

      // Extract tech stack from after "| Stack -" (with or without bold markers)
      const stackMatch = line.match(/\*{0,2}\|\s*Stack\s*-\*{0,2}\s*(.+)$/)
      const headerPart = stackMatch ? line.slice(0, line.indexOf(stackMatch[0])).trim() : line

      if (stackMatch) {
        techStack = stackMatch[1].split(',').map((s) => s.trim()).filter(Boolean)
      }

      // Extract name and optional URL from the header part
      // Pattern: **[Name](url)** possibly followed by "at Company"
      const linkMatch = headerPart.match(/^\*\*\[(.+?)\]\((.+?)\)\*\*/)
      if (linkMatch) {
        name = linkMatch[1]
        url = linkMatch[2]
      } else {
        // Pattern: **Name** possibly followed by "at Company"
        const plainMatch = headerPart.match(/^\*\*(.+?)\*\*/)
        if (plainMatch) {
          name = plainMatch[1]
        }
      }

      if (name) {
        current = {
          key: String(entries.length + 1),
          header: '',
          content: '',
          name,
          url,
          techStack,
        }
      } else {
        current = {
          key: String(entries.length + 1),
          header: line,
          content: '',
        }
      }
    } else if (current) {
      contentLines.push(line)
    } else if (line.trim() !== '') {
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
 * Reassemble structured project entries into markdown.
 */
export function assembleProjectEntries(entries: EntryData[]): string {
  return entries
    .map((entry) => {
      if (entry.name) {
        let header: string
        if (entry.url) {
          header = `**[${entry.name}](${entry.url})**`
        } else {
          header = `**${entry.name}**`
        }
        if (entry.techStack && entry.techStack.length > 0) {
          header += ` **| Stack -** ${entry.techStack.join(', ')}`
        }
        if (entry.content) {
          return `${header}\n${entry.content}`
        }
        return header
      }
      if (entry.content) {
        return `${entry.header}\n${entry.content}`
      }
      return entry.header
    })
    .join('\n\n')
}

/**
 * Parse skills-section markdown into structured category entries.
 *
 * Format per line: **Category:** skill1, skill2, skill3.
 */
export function parseSkillCategories(content: string): EntryData[] {
  const lines = content.split('\n')
  const entries: EntryData[] = []

  for (const rawLine of lines) {
    const line = rawLine.trimEnd()
    const match = line.match(/^\*\*(.+?):\*\*\s*(.+)$/)
    if (match) {
      const categoryName = match[1]
      let skillsStr = match[2].trim()
      // Strip trailing period
      if (skillsStr.endsWith('.')) {
        skillsStr = skillsStr.slice(0, -1)
      }
      const skills = skillsStr.split(',').map((s) => s.trim()).filter(Boolean)
      entries.push({
        key: String(entries.length + 1),
        header: '',
        content: '',
        categoryName,
        skills,
      })
    }
  }

  return entries
}

/**
 * Reassemble structured skill category entries into markdown.
 */
export function assembleSkillCategories(entries: EntryData[]): string {
  return entries
    .map((entry) => {
      if (entry.categoryName && entry.skills) {
        return `**${entry.categoryName}:** ${entry.skills.join(', ')}.`
      }
      if (entry.content) {
        return `${entry.header}\n${entry.content}`
      }
      return entry.header
    })
    .join('\n\n')
}

/**
 * Generic fallback parser — split on bold headers.
 */
export function parseGenericEntries(content: string): EntryData[] {
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
    if (line.startsWith('**')) {
      flushCurrent()
      current = {
        key: String(entries.length + 1),
        header: line,
        content: '',
      }
    } else if (current) {
      contentLines.push(line)
    } else if (line.trim() !== '') {
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
 * Reassemble generic entries into markdown.
 */
export function assembleGenericEntries(entries: EntryData[]): string {
  return entries
    .map((entry) => {
      if (entry.content) {
        return `${entry.header}\n${entry.content}`
      }
      return entry.header
    })
    .join('\n\n')
}

/**
 * Dispatcher: parse section content into entries based on section type.
 */
export function parseSectionEntries(content: string, type: SectionType): EntryData[] {
  switch (type) {
    case 'experience':
      return parseExperienceEntries(content)
    case 'education':
      return parseEducationEntries(content)
    case 'projects':
      return parseProjectEntries(content)
    case 'skills':
      return parseSkillCategories(content)
    default:
      return parseGenericEntries(content)
  }
}

/**
 * Dispatcher: assemble entries back into markdown based on section type.
 */
export function assembleSectionContent(entries: EntryData[], type: SectionType): string {
  switch (type) {
    case 'experience':
      return assembleExperienceEntries(entries)
    case 'education':
      return assembleEducationEntries(entries)
    case 'projects':
      return assembleProjectEntries(entries)
    case 'skills':
      return assembleSkillCategories(entries)
    default:
      return assembleGenericEntries(entries)
  }
}
