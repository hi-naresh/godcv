# Structured Section Editor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add section/entry reordering, structured fields for Experience/Education/Projects/Skills, and a reusable chip input to the Profile tab's section editor.

**Architecture:** Extract parsing/assembly logic into a standalone `sectionParsers.ts` utility (pure functions, easily testable). Create four specialized entry card components + one ChipInput component. Modify SectionCard to dispatch to the right entry component and support reordering. Modify SectionEditor to use the new parsers and support section reordering.

**Tech Stack:** Vue 3 + TypeScript, Vitest + @vue/test-utils, no new dependencies.

**Spec:** `docs/superpowers/specs/2026-04-16-structured-section-editor-design.md`

---

## File Structure

| File | Status | Responsibility |
|------|--------|----------------|
| `frontend/src/utils/sectionParsers.ts` | **New** | Pure parse/assemble functions for each section type + EntryData type |
| `frontend/src/__tests__/sectionParsers.test.ts` | **New** | Unit tests for all parsers and assemblers |
| `frontend/src/components/ChipInput.vue` | **New** | Reusable tag/chip input (Enter/comma to add, backspace/× to remove) |
| `frontend/src/components/ExperienceEntryCard.vue` | **New** | Structured experience entry (Role, Company, Start, End + bullets) |
| `frontend/src/components/EducationEntryCard.vue` | **New** | Structured education entry (Degree, University, Start, End + content) |
| `frontend/src/components/ProjectEntryCard.vue` | **New** | Structured project entry (Name, URL, TechStack chips + bullets) |
| `frontend/src/components/SkillCategoryCard.vue` | **New** | Structured skill category (Name + skill chips) |
| `frontend/src/components/SectionCard.vue` | **Modify** | Add sectionType prop, dispatch to correct entry component, entry reordering arrows |
| `frontend/src/components/SectionEditor.vue` | **Modify** | Section type map, section reordering arrows, use new parsers/assemblers |
| `frontend/src/components/EntryCard.vue` | **No change** | Remains generic fallback |

---

### Task 1: Section Parser Utilities — Types and Experience Parser

**Files:**
- Create: `frontend/src/utils/sectionParsers.ts`
- Create: `frontend/src/__tests__/sectionParsers.test.ts`

- [ ] **Step 1: Write failing tests for EntryData type and experience parser**

Create `frontend/src/__tests__/sectionParsers.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import { parseExperienceEntries, assembleExperienceEntries } from '../utils/sectionParsers'

describe('parseExperienceEntries', () => {
  it('parses a standard experience entry with role, company, and dates', () => {
    const content = `**Founding AI Engineer — NestDore (London based startup, ~10 people)**  *October 2025 – March 2026*
- Building the core **intelligent-matching engine** for landlords and tenants.
- Designing **data pipelines** feeding structured verified properties.`

    const entries = parseExperienceEntries(content)
    expect(entries).toHaveLength(1)
    expect(entries[0].role).toBe('Founding AI Engineer')
    expect(entries[0].company).toBe('NestDore (London based startup, ~10 people)')
    expect(entries[0].startDate).toBe('October 2025')
    expect(entries[0].endDate).toBe('March 2026')
    expect(entries[0].content).toContain('- Building the core')
    expect(entries[0].content).toContain('- Designing **data pipelines**')
  })

  it('parses multiple experience entries', () => {
    const content = `**AI/ML Engineer (Part-Time) — BotWot iCX (Remote, Indian SaaS startup, ~25 people)**  *Jan 2025 – Oct 2025*
- Building orchestrated **multi-agent CRM automation**.

**LLM Data Engineer (Intern) — InsurStaq.ai (Remote, Insurtech startup, seed stage, ~20 people)**  *March 2024 – Nov 2024*
- Built **end-to-end data pipelines and RAG workflows**.`

    const entries = parseExperienceEntries(content)
    expect(entries).toHaveLength(2)
    expect(entries[0].role).toBe('AI/ML Engineer (Part-Time)')
    expect(entries[0].company).toBe('BotWot iCX (Remote, Indian SaaS startup, ~25 people)')
    expect(entries[1].role).toBe('LLM Data Engineer (Intern)')
    expect(entries[1].company).toBe('InsurStaq.ai (Remote, Insurtech startup, seed stage, ~20 people)')
  })

  it('handles entry with Present as end date', () => {
    const content = `**Senior Dev — Acme Corp** *Jan 2023 – Present*
- Leading the team.`

    const entries = parseExperienceEntries(content)
    expect(entries).toHaveLength(1)
    expect(entries[0].endDate).toBe('Present')
  })

  it('falls back to generic entry for unparseable lines', () => {
    const content = `Some random text that doesn't match
- A bullet point`

    const entries = parseExperienceEntries(content)
    expect(entries).toHaveLength(1)
    expect(entries[0].header).toBe('Some random text that doesn\'t match')
    expect(entries[0].role).toBeUndefined()
  })

  it('handles entry with no dates', () => {
    const content = `**Developer — StartupXYZ**
- Built things.`

    const entries = parseExperienceEntries(content)
    expect(entries).toHaveLength(1)
    expect(entries[0].role).toBe('Developer')
    expect(entries[0].company).toBe('StartupXYZ')
    expect(entries[0].startDate).toBe('')
    expect(entries[0].endDate).toBe('')
  })
})

describe('assembleExperienceEntries', () => {
  it('assembles a standard experience entry', () => {
    const entries = [{
      key: 'e1',
      header: '',
      content: '- Built things.',
      role: 'AI Engineer',
      company: 'Acme (London)',
      startDate: 'Jan 2024',
      endDate: 'Present',
    }]
    const result = assembleExperienceEntries(entries)
    expect(result).toBe('**AI Engineer — Acme (London)** *Jan 2024 – Present*\n- Built things.')
  })

  it('omits date portion when both dates are empty', () => {
    const entries = [{
      key: 'e1',
      header: '',
      content: '- Did stuff.',
      role: 'Dev',
      company: 'Co',
      startDate: '',
      endDate: '',
    }]
    const result = assembleExperienceEntries(entries)
    expect(result).toBe('**Dev — Co**\n- Did stuff.')
  })

  it('assembles multiple entries separated by blank lines', () => {
    const entries = [
      { key: 'e1', header: '', content: '- A.', role: 'Dev', company: 'Co1', startDate: 'Jan 2024', endDate: 'Present' },
      { key: 'e2', header: '', content: '- B.', role: 'Lead', company: 'Co2', startDate: 'Jan 2023', endDate: 'Dec 2023' },
    ]
    const result = assembleExperienceEntries(entries)
    expect(result).toContain('**Dev — Co1** *Jan 2024 – Present*\n- A.')
    expect(result).toContain('**Lead — Co2** *Jan 2023 – Dec 2023*\n- B.')
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/__tests__/sectionParsers.test.ts`
Expected: FAIL — module `../utils/sectionParsers` not found.

- [ ] **Step 3: Implement sectionParsers.ts with types and experience parser**

Create `frontend/src/utils/sectionParsers.ts`:

```typescript
// ---------- Types ----------

export type SectionType = 'experience' | 'projects' | 'education' | 'skills' | 'generic'

export interface EntryData {
  key: string
  header: string
  content: string

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

const SECTION_TYPE_MAP: Record<string, SectionType> = {
  experience: 'experience',
  projects: 'projects',
  education: 'education',
  skills: 'skills',
}

export function getSectionType(name: string): SectionType {
  return SECTION_TYPE_MAP[name.toLowerCase()] || 'generic'
}

export function isMultiEntryType(type: SectionType): boolean {
  return type !== 'generic'
}

function makeKey(): string {
  return `entry-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`
}

// ---------- Helpers ----------

/** Split content into blocks starting with ** (bold markers) */
function splitBoldBlocks(content: string): string[] {
  return content.split(/(?=^\*\*)/m).map(b => b.trim()).filter(Boolean)
}

/** Split a block into first line and rest */
function splitFirstLine(block: string): [string, string] {
  const nlIdx = block.indexOf('\n')
  if (nlIdx === -1) return [block.trim(), '']
  return [block.substring(0, nlIdx).trim(), block.substring(nlIdx + 1).trim()]
}

// ---------- Experience ----------

const EXP_REGEX = /^\*\*(.+?)\s*[—–-]\s*(.+?)\*\*\s*\*(.+?)\*\s*$/
const EXP_NO_DATE_REGEX = /^\*\*(.+?)\s*[—–-]\s*(.+?)\*\*\s*$/

function parseDates(dateStr: string): [string, string] {
  const parts = dateStr.split(/\s*[–—-]\s*/)
  if (parts.length >= 2) return [parts[0].trim(), parts.slice(1).join(' – ').trim()]
  return [dateStr.trim(), '']
}

export function parseExperienceEntries(content: string): EntryData[] {
  const blocks = splitBoldBlocks(content)
  if (blocks.length === 0 && content.trim()) {
    // No bold blocks found — treat entire content as a single generic entry
    const [header, body] = splitFirstLine(content)
    return [{ key: makeKey(), header, content: body }]
  }

  return blocks.map(block => {
    const [firstLine, body] = splitFirstLine(block)

    let match = firstLine.match(EXP_REGEX)
    if (match) {
      const [startDate, endDate] = parseDates(match[3])
      return {
        key: makeKey(),
        header: firstLine,
        content: body,
        role: match[1].trim(),
        company: match[2].trim(),
        startDate,
        endDate,
      }
    }

    match = firstLine.match(EXP_NO_DATE_REGEX)
    if (match) {
      return {
        key: makeKey(),
        header: firstLine,
        content: body,
        role: match[1].trim(),
        company: match[2].trim(),
        startDate: '',
        endDate: '',
      }
    }

    // Fallback: generic entry
    return { key: makeKey(), header: firstLine.replace(/^\*\*|\*\*$/g, ''), content: body }
  })
}

export function assembleExperienceEntries(entries: EntryData[]): string {
  return entries
    .filter(e => (e.role ?? e.header ?? '').trim() || e.content.trim())
    .map(e => {
      if (e.role !== undefined) {
        const datePart = (e.startDate || e.endDate)
          ? ` *${e.startDate} – ${e.endDate}*`
          : ''
        const header = `**${e.role} — ${e.company}**${datePart}`
        return e.content.trim() ? `${header}\n${e.content}` : header
      }
      // Generic fallback
      return e.content.trim() ? `${e.header}\n${e.content}` : e.header
    })
    .join('\n\n')
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/__tests__/sectionParsers.test.ts`
Expected: All experience tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/utils/sectionParsers.ts frontend/src/__tests__/sectionParsers.test.ts
git commit -m "feat: add sectionParsers utility with experience parser and tests"
```

---

### Task 2: Education, Projects, and Skills Parsers

**Files:**
- Modify: `frontend/src/utils/sectionParsers.ts`
- Modify: `frontend/src/__tests__/sectionParsers.test.ts`

- [ ] **Step 1: Write failing tests for education parser**

Append to `frontend/src/__tests__/sectionParsers.test.ts`:

```typescript
import {
  parseExperienceEntries, assembleExperienceEntries,
  parseEducationEntries, assembleEducationEntries,
  parseProjectEntries, assembleProjectEntries,
  parseSkillCategories, assembleSkillCategories,
  parseSectionEntries, assembleSectionContent,
} from '../utils/sectionParsers'

// ... (keep existing experience tests) ...

describe('parseEducationEntries', () => {
  it('parses education entry with degree, university, and dates', () => {
    const content = `**M.Sc. in Artificial Intelligence - Brunel University London, UK.** *Jan 2025 – Jan 2026*  
***Coursework**:* Predictive Analytics; Neural Networks.`

    const entries = parseEducationEntries(content)
    expect(entries).toHaveLength(1)
    expect(entries[0].degree).toBe('M.Sc. in Artificial Intelligence')
    expect(entries[0].university).toBe('Brunel University London, UK.')
    expect(entries[0].startDate).toBe('Jan 2025')
    expect(entries[0].endDate).toBe('Jan 2026')
    expect(entries[0].content).toContain('Coursework')
  })

  it('parses multiple education entries', () => {
    const content = `**M.Sc. in AI - Brunel University.** *Jan 2025 – Jan 2026*  
***Coursework**:* ML.

**B.Sc. in IT - AURO University, Surat, IN.** *Aug 2021 – Jun 2024*  
***Coursework**:* OS.`

    const entries = parseEducationEntries(content)
    expect(entries).toHaveLength(2)
    expect(entries[0].degree).toBe('M.Sc. in AI')
    expect(entries[1].degree).toBe('B.Sc. in IT')
  })
})

describe('assembleEducationEntries', () => {
  it('assembles education entry', () => {
    const entries = [{
      key: 'ed1', header: '', content: '***Coursework**:* ML.',
      degree: 'M.Sc. in AI', university: 'Brunel University.',
      startDate: 'Jan 2025', endDate: 'Jan 2026',
    }]
    const result = assembleEducationEntries(entries)
    expect(result).toContain('**M.Sc. in AI - Brunel University.** *Jan 2025 – Jan 2026*')
    expect(result).toContain('***Coursework**:* ML.')
  })
})
```

- [ ] **Step 2: Write failing tests for projects parser**

Append to test file:

```typescript
describe('parseProjectEntries', () => {
  it('parses project with link and tech stack', () => {
    const content = `**[Luxury Concierge LLM Agent](https://kaiconcierge.ai)** at BotWot **| Stack -** Python, LangChain, FastAPI
- Multi-agent orchestration system.`

    const entries = parseProjectEntries(content)
    expect(entries).toHaveLength(1)
    expect(entries[0].name).toBe('Luxury Concierge LLM Agent')
    expect(entries[0].url).toBe('https://kaiconcierge.ai')
    expect(entries[0].techStack).toContain('Python')
    expect(entries[0].techStack).toContain('LangChain')
    expect(entries[0].techStack).toContain('FastAPI')
    expect(entries[0].content).toContain('- Multi-agent orchestration')
  })

  it('parses project without link', () => {
    const content = `**Framework Benchmark** at University **| Stack -** Python, R, scikit-learn
- Built pipeline.`

    const entries = parseProjectEntries(content)
    expect(entries).toHaveLength(1)
    expect(entries[0].name).toBe('Framework Benchmark')
    expect(entries[0].url).toBe('')
    expect(entries[0].techStack).toContain('Python')
  })

  it('parses simple project format without "at" clause', () => {
    const content = `**[MyProject](https://github.com/me/proj)** | Stack - React, Node.js
- Built a thing.`

    const entries = parseProjectEntries(content)
    expect(entries).toHaveLength(1)
    expect(entries[0].name).toBe('MyProject')
    expect(entries[0].url).toBe('https://github.com/me/proj')
  })
})

describe('assembleProjectEntries', () => {
  it('assembles project with link and tech stack', () => {
    const entries = [{
      key: 'p1', header: '', content: '- Built it.',
      name: 'MyProject', url: 'https://github.com/me/proj',
      techStack: ['React', 'Node.js'],
    }]
    const result = assembleProjectEntries(entries)
    expect(result).toBe('**[MyProject](https://github.com/me/proj)** | Stack - React, Node.js\n- Built it.')
  })

  it('assembles project without URL', () => {
    const entries = [{
      key: 'p1', header: '', content: '- Built it.',
      name: 'MyProject', url: '',
      techStack: ['React'],
    }]
    const result = assembleProjectEntries(entries)
    expect(result).toContain('**MyProject** | Stack - React')
  })
})
```

- [ ] **Step 3: Write failing tests for skills parser**

Append to test file:

```typescript
describe('parseSkillCategories', () => {
  it('parses skill categories with skills list', () => {
    const content = `**Data Engineering:** ETL Pipelines, API Integrations, MongoDB, Supabase, VectorDB.

**AI Orchestration:** LangChain, LangGraph, RAG Systems, PyTorch.
**Programming:** Python, TypeScript, Go.`

    const entries = parseSkillCategories(content)
    expect(entries).toHaveLength(3)
    expect(entries[0].categoryName).toBe('Data Engineering')
    expect(entries[0].skills).toContain('ETL Pipelines')
    expect(entries[0].skills).toContain('VectorDB')
    // trailing period should be stripped from last skill
    expect(entries[0].skills).not.toContain('VectorDB.')
    expect(entries[2].categoryName).toBe('Programming')
    expect(entries[2].skills).toEqual(['Python', 'TypeScript', 'Go'])
  })

  it('handles multi-line category (skills with trailing whitespace)', () => {
    const content = `**Cloud/Infra:** AWS, Azure, Docker, Kubernetes, Helm, CI/CD.  
**Programming:** Python, TypeScript.`

    const entries = parseSkillCategories(content)
    expect(entries).toHaveLength(2)
    expect(entries[0].categoryName).toBe('Cloud/Infra')
    expect(entries[0].skills).toContain('CI/CD')
  })
})

describe('assembleSkillCategories', () => {
  it('assembles skill categories', () => {
    const entries = [
      { key: 's1', header: '', content: '', categoryName: 'Languages', skills: ['Python', 'Go'] },
      { key: 's2', header: '', content: '', categoryName: 'Cloud', skills: ['AWS', 'GCP'] },
    ]
    const result = assembleSkillCategories(entries)
    expect(result).toBe('**Languages:** Python, Go.\n\n**Cloud:** AWS, GCP.')
  })
})
```

- [ ] **Step 4: Write failing tests for dispatcher functions**

Append to test file:

```typescript
describe('parseSectionEntries', () => {
  it('dispatches to experience parser', () => {
    const content = `**Dev — Co** *Jan 2024 – Present*
- Did stuff.`
    const entries = parseSectionEntries(content, 'experience')
    expect(entries[0].role).toBe('Dev')
  })

  it('dispatches to skills parser', () => {
    const content = `**Languages:** Python, Go.`
    const entries = parseSectionEntries(content, 'skills')
    expect(entries[0].categoryName).toBe('Languages')
  })

  it('falls back to generic for unknown type', () => {
    const content = `**Something**\nText here`
    const entries = parseSectionEntries(content, 'generic')
    expect(entries[0].header).toBeTruthy()
  })
})
```

- [ ] **Step 5: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/__tests__/sectionParsers.test.ts`
Expected: FAIL — functions not exported.

- [ ] **Step 6: Implement education, projects, skills parsers and dispatchers**

Add to `frontend/src/utils/sectionParsers.ts`:

```typescript
// ---------- Education ----------

const EDU_REGEX = /^\*\*(.+?)\s*[-–]\s*(.+?)\*\*\s*\*(.+?)\*\s*$/

export function parseEducationEntries(content: string): EntryData[] {
  const blocks = splitBoldBlocks(content)
  if (blocks.length === 0 && content.trim()) {
    const [header, body] = splitFirstLine(content)
    return [{ key: makeKey(), header, content: body }]
  }

  return blocks.map(block => {
    const [firstLine, body] = splitFirstLine(block)
    // Strip trailing whitespace chars (  \n) from first line
    const cleaned = firstLine.replace(/\s+$/, '')

    const match = cleaned.match(EDU_REGEX)
    if (match) {
      const [startDate, endDate] = parseDates(match[3])
      return {
        key: makeKey(),
        header: firstLine,
        content: body,
        degree: match[1].trim(),
        university: match[2].trim(),
        startDate,
        endDate,
      }
    }

    // Try without dates
    const noDateMatch = cleaned.match(/^\*\*(.+?)\s*[-–]\s*(.+?)\*\*\s*$/)
    if (noDateMatch) {
      return {
        key: makeKey(),
        header: firstLine,
        content: body,
        degree: noDateMatch[1].trim(),
        university: noDateMatch[2].trim(),
        startDate: '',
        endDate: '',
      }
    }

    return { key: makeKey(), header: firstLine.replace(/^\*\*|\*\*$/g, ''), content: body }
  })
}

export function assembleEducationEntries(entries: EntryData[]): string {
  return entries
    .filter(e => (e.degree ?? e.header ?? '').trim() || e.content.trim())
    .map(e => {
      if (e.degree !== undefined) {
        const datePart = (e.startDate || e.endDate)
          ? ` *${e.startDate} – ${e.endDate}*`
          : ''
        const header = `**${e.degree} - ${e.university}**${datePart}`
        return e.content.trim() ? `${header}\n${e.content}` : header
      }
      return e.content.trim() ? `${e.header}\n${e.content}` : e.header
    })
    .join('\n\n')
}

// ---------- Projects ----------

// Pattern: **[Name](url)** ... | Stack - tech1, tech2
const PROJ_LINK_REGEX = /^\*\*\[(.+?)\]\((.+?)\)\*\*(.+?)(?:\*\*\s*\|\s*Stack\s*[-–]\*\*\s*(.+)|(?:\|\s*Stack\s*[-–]\s*(.+)))$/
// Pattern: **Name** ... | Stack - tech1, tech2
const PROJ_NO_LINK_REGEX = /^\*\*(.+?)\*\*(.+?)(?:\*\*\s*\|\s*Stack\s*[-–]\*\*\s*(.+)|(?:\|\s*Stack\s*[-–]\s*(.+)))$/

function parseTechStack(raw: string): string[] {
  return raw.split(',').map(s => s.trim()).filter(Boolean)
}

export function parseProjectEntries(content: string): EntryData[] {
  const blocks = splitBoldBlocks(content)
  if (blocks.length === 0 && content.trim()) {
    const [header, body] = splitFirstLine(content)
    return [{ key: makeKey(), header, content: body }]
  }

  return blocks.map(block => {
    const [firstLine, body] = splitFirstLine(block)

    // Try link format: **[Name](url)** optional-text **| Stack -** tech1, tech2
    // or: **[Name](url)** | Stack - tech1, tech2
    let match = firstLine.match(/^\*\*\[(.+?)\]\((.+?)\)\*\*(.*)$/)
    if (match) {
      const afterLink = match[3]
      const techMatch = afterLink.match(/\*\*\s*\|\s*Stack\s*[-–]\*\*\s*(.+)/) ||
                         afterLink.match(/\|\s*Stack\s*[-–]\s*(.+)/)
      const techStack = techMatch ? parseTechStack(techMatch[1]) : []
      return {
        key: makeKey(),
        header: firstLine,
        content: body,
        name: match[1].trim(),
        url: match[2].trim(),
        techStack,
      }
    }

    // Try no-link format: **Name** optional-text **| Stack -** tech1, tech2
    match = firstLine.match(/^\*\*(.+?)\*\*(.*)$/)
    if (match) {
      const afterName = match[2]
      const techMatch = afterName.match(/\*\*\s*\|\s*Stack\s*[-–]\*\*\s*(.+)/) ||
                         afterName.match(/\|\s*Stack\s*[-–]\s*(.+)/)
      const techStack = techMatch ? parseTechStack(techMatch[1]) : []
      // Strip "at Company" text from name if present
      const namePart = match[1].trim()
      return {
        key: makeKey(),
        header: firstLine,
        content: body,
        name: namePart,
        url: '',
        techStack,
      }
    }

    return { key: makeKey(), header: firstLine, content: body }
  })
}

export function assembleProjectEntries(entries: EntryData[]): string {
  return entries
    .filter(e => (e.name ?? e.header ?? '').trim() || e.content.trim())
    .map(e => {
      if (e.name !== undefined) {
        const namePart = e.url
          ? `**[${e.name}](${e.url})**`
          : `**${e.name}**`
        const techPart = e.techStack && e.techStack.length > 0
          ? ` | Stack - ${e.techStack.join(', ')}`
          : ''
        const header = `${namePart}${techPart}`
        return e.content.trim() ? `${header}\n${e.content}` : header
      }
      return e.content.trim() ? `${e.header}\n${e.content}` : e.header
    })
    .join('\n\n')
}

// ---------- Skills ----------

const SKILL_CAT_REGEX = /^\*\*(.+?):\*\*\s*(.+)$/

export function parseSkillCategories(content: string): EntryData[] {
  // Skills are line-based, not block-based
  const lines = content.split('\n').map(l => l.trim()).filter(Boolean)
  const entries: EntryData[] = []

  for (const line of lines) {
    // Strip trailing whitespace (some lines end with   for markdown line break)
    const cleaned = line.replace(/\s+$/, '')
    const match = cleaned.match(SKILL_CAT_REGEX)
    if (match) {
      const categoryName = match[1].trim()
      const skillsRaw = match[2].trim()
      // Remove trailing period, then split
      const stripped = skillsRaw.replace(/\.\s*$/, '')
      const skills = stripped.split(',').map(s => s.trim()).filter(Boolean)
      entries.push({
        key: makeKey(),
        header: line,
        content: '',
        categoryName,
        skills,
      })
    } else {
      // Fallback — treat as generic content line
      entries.push({ key: makeKey(), header: line, content: '' })
    }
  }

  return entries
}

export function assembleSkillCategories(entries: EntryData[]): string {
  return entries
    .filter(e => (e.categoryName ?? e.header ?? '').trim())
    .map(e => {
      if (e.categoryName !== undefined && e.skills) {
        return `**${e.categoryName}:** ${e.skills.join(', ')}.`
      }
      return e.header
    })
    .join('\n\n')
}

// ---------- Generic (existing behavior) ----------

export function parseGenericEntries(content: string): EntryData[] {
  const blocks = splitBoldBlocks(content)
  if (blocks.length === 0 && content.trim()) {
    // No bold blocks — return single entry with full content
    return [{ key: makeKey(), header: '', content }]
  }

  return blocks.map(block => {
    const [header, body] = splitFirstLine(block)
    return { key: makeKey(), header, content: body }
  })
}

// ---------- Dispatchers ----------

export function parseSectionEntries(content: string, type: SectionType): EntryData[] {
  switch (type) {
    case 'experience': return parseExperienceEntries(content)
    case 'education': return parseEducationEntries(content)
    case 'projects': return parseProjectEntries(content)
    case 'skills': return parseSkillCategories(content)
    default: return parseGenericEntries(content)
  }
}

export function assembleSectionContent(entries: EntryData[], type: SectionType): string {
  switch (type) {
    case 'experience': return assembleExperienceEntries(entries)
    case 'education': return assembleEducationEntries(entries)
    case 'projects': return assembleProjectEntries(entries)
    case 'skills': return assembleSkillCategories(entries)
    default: {
      // Generic: same as old behavior
      return entries
        .filter(e => e.header.trim() || e.content.trim())
        .map(e => e.content.trim() ? `${e.header}\n${e.content}` : e.header)
        .join('\n\n')
    }
  }
}
```

- [ ] **Step 7: Run all tests to verify they pass**

Run: `cd frontend && npx vitest run src/__tests__/sectionParsers.test.ts`
Expected: All tests PASS.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/utils/sectionParsers.ts frontend/src/__tests__/sectionParsers.test.ts
git commit -m "feat: add education, projects, skills parsers with tests"
```

---

### Task 3: ChipInput Component

**Files:**
- Create: `frontend/src/components/ChipInput.vue`

- [ ] **Step 1: Create ChipInput.vue**

Create `frontend/src/components/ChipInput.vue`:

```vue
<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  modelValue: string[]
  placeholder?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string[]]
}>()

const inputText = ref('')

function addChip() {
  const val = inputText.value.trim().replace(/,+$/, '').trim()
  if (!val) return
  // Deduplicate (case-insensitive check)
  if (props.modelValue.some(s => s.toLowerCase() === val.toLowerCase())) {
    inputText.value = ''
    return
  }
  emit('update:modelValue', [...props.modelValue, val])
  inputText.value = ''
}

function removeChip(index: number) {
  const updated = props.modelValue.filter((_, i) => i !== index)
  emit('update:modelValue', updated)
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' || e.key === ',') {
    e.preventDefault()
    addChip()
  } else if (e.key === 'Backspace' && inputText.value === '' && props.modelValue.length > 0) {
    removeChip(props.modelValue.length - 1)
  }
}
</script>

<template>
  <div class="chip-input-wrap">
    <span v-for="(chip, i) in modelValue" :key="chip + i" class="chip">
      {{ chip }}
      <button class="chip-remove" @click="removeChip(i)" type="button">&times;</button>
    </span>
    <input
      v-model="inputText"
      class="chip-text-input"
      :placeholder="modelValue.length === 0 ? (placeholder || 'Type and press Enter') : ''"
      @keydown="onKeydown"
      @blur="addChip"
    />
  </div>
</template>

<style scoped>
.chip-input-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 4px 6px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  background: #fff;
  cursor: text;
  min-height: 32px;
  align-items: center;
}
.chip-input-wrap:focus-within {
  border-color: #667eea;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 2px 8px;
  background: #f0f0f0;
  border-radius: 12px;
  font-size: 0.78rem;
  line-height: 1.4;
  white-space: nowrap;
}
.chip-remove {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 0.85rem;
  color: #999;
  padding: 0 2px;
  line-height: 1;
}
.chip-remove:hover {
  color: #d00;
}
.chip-text-input {
  border: none;
  outline: none;
  flex: 1;
  min-width: 80px;
  font-size: 0.8rem;
  padding: 2px 4px;
  background: transparent;
}
</style>
```

- [ ] **Step 2: Verify by running the dev server and visually checking**

Run: `cd frontend && npm run dev`
(Manual: temporarily import ChipInput in ProfileView or SectionEditor and render with test data. Remove after check.)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ChipInput.vue
git commit -m "feat: add ChipInput reusable tag/chip input component"
```

---

### Task 4: Specialized Entry Card Components

**Files:**
- Create: `frontend/src/components/ExperienceEntryCard.vue`
- Create: `frontend/src/components/EducationEntryCard.vue`
- Create: `frontend/src/components/ProjectEntryCard.vue`
- Create: `frontend/src/components/SkillCategoryCard.vue`

- [ ] **Step 1: Create ExperienceEntryCard.vue**

Create `frontend/src/components/ExperienceEntryCard.vue`:

```vue
<script setup lang="ts">
import type { EntryData } from '../utils/sectionParsers'

const props = defineProps<{
  entry: EntryData
}>()

const emit = defineEmits<{
  'update:entry': [value: EntryData]
  remove: []
}>()

function update(fields: Partial<EntryData>) {
  emit('update:entry', { ...props.entry, ...fields })
}
</script>

<template>
  <div class="entry-card">
    <div class="entry-header">
      <div class="entry-fields">
        <div class="field-row">
          <div class="field">
            <label>Role</label>
            <input :value="entry.role" @input="update({ role: ($event.target as HTMLInputElement).value })" placeholder="e.g. AI Engineer" />
          </div>
          <div class="field">
            <label>Company + Location</label>
            <input :value="entry.company" @input="update({ company: ($event.target as HTMLInputElement).value })" placeholder="e.g. Acme Corp (London)" />
          </div>
        </div>
        <div class="field-row">
          <div class="field">
            <label>Start Date</label>
            <input :value="entry.startDate" @input="update({ startDate: ($event.target as HTMLInputElement).value })" placeholder="e.g. Jan 2024" />
          </div>
          <div class="field">
            <label>End Date</label>
            <input :value="entry.endDate" @input="update({ endDate: ($event.target as HTMLInputElement).value })" placeholder="e.g. Present" />
          </div>
        </div>
      </div>
      <button class="entry-remove-btn" @click="$emit('remove')" title="Remove entry">&times;</button>
    </div>
    <textarea
      class="entry-content"
      :value="entry.content"
      @input="update({ content: ($event.target as HTMLTextAreaElement).value })"
      placeholder="- Achievement or responsibility&#10;- Another bullet point"
      rows="3"
    />
  </div>
</template>

<style scoped>
.entry-card {
  border: 1px solid #e8e8e8; border-radius: 8px; padding: 10px;
  background: #fafafa;
}
.entry-header { display: flex; gap: 6px; margin-bottom: 6px; }
.entry-fields { flex: 1; display: flex; flex-direction: column; gap: 6px; }
.field-row { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.field { display: flex; flex-direction: column; gap: 2px; }
.field label { font-size: 0.7rem; font-weight: 600; color: #888; }
.field input {
  padding: 5px 8px; border: 1px solid #d9d9d9; border-radius: 6px;
  font-size: 0.82rem; font-family: ui-monospace, monospace;
}
.field input:focus { outline: none; border-color: #667eea; }
.entry-remove-btn {
  width: 26px; height: 26px; border: none; background: #f0f0f0;
  border-radius: 6px; font-size: 1rem; cursor: pointer; color: #999;
  display: flex; align-items: center; justify-content: center;
  align-self: flex-start;
}
.entry-remove-btn:hover { background: #ffe0e0; color: #d00; }
.entry-content {
  width: 100%; resize: vertical; padding: 6px 8px;
  border: 1px solid #d9d9d9; border-radius: 6px; font-size: 0.8rem;
  font-family: ui-monospace, monospace; line-height: 1.5;
}
.entry-content:focus { outline: none; border-color: #667eea; }
</style>
```

- [ ] **Step 2: Create EducationEntryCard.vue**

Create `frontend/src/components/EducationEntryCard.vue`:

```vue
<script setup lang="ts">
import type { EntryData } from '../utils/sectionParsers'

const props = defineProps<{
  entry: EntryData
}>()

const emit = defineEmits<{
  'update:entry': [value: EntryData]
  remove: []
}>()

function update(fields: Partial<EntryData>) {
  emit('update:entry', { ...props.entry, ...fields })
}
</script>

<template>
  <div class="entry-card">
    <div class="entry-header">
      <div class="entry-fields">
        <div class="field-row">
          <div class="field">
            <label>Degree</label>
            <input :value="entry.degree" @input="update({ degree: ($event.target as HTMLInputElement).value })" placeholder="e.g. M.Sc. in Computer Science" />
          </div>
          <div class="field">
            <label>University</label>
            <input :value="entry.university" @input="update({ university: ($event.target as HTMLInputElement).value })" placeholder="e.g. MIT, Cambridge, MA" />
          </div>
        </div>
        <div class="field-row">
          <div class="field">
            <label>Start Date</label>
            <input :value="entry.startDate" @input="update({ startDate: ($event.target as HTMLInputElement).value })" placeholder="e.g. Sep 2022" />
          </div>
          <div class="field">
            <label>End Date</label>
            <input :value="entry.endDate" @input="update({ endDate: ($event.target as HTMLInputElement).value })" placeholder="e.g. Jun 2024" />
          </div>
        </div>
      </div>
      <button class="entry-remove-btn" @click="$emit('remove')" title="Remove entry">&times;</button>
    </div>
    <textarea
      class="entry-content"
      :value="entry.content"
      @input="update({ content: ($event.target as HTMLTextAreaElement).value })"
      placeholder="Coursework, achievements, GPA..."
      rows="2"
    />
  </div>
</template>

<style scoped>
.entry-card {
  border: 1px solid #e8e8e8; border-radius: 8px; padding: 10px;
  background: #fafafa;
}
.entry-header { display: flex; gap: 6px; margin-bottom: 6px; }
.entry-fields { flex: 1; display: flex; flex-direction: column; gap: 6px; }
.field-row { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.field { display: flex; flex-direction: column; gap: 2px; }
.field label { font-size: 0.7rem; font-weight: 600; color: #888; }
.field input {
  padding: 5px 8px; border: 1px solid #d9d9d9; border-radius: 6px;
  font-size: 0.82rem; font-family: ui-monospace, monospace;
}
.field input:focus { outline: none; border-color: #667eea; }
.entry-remove-btn {
  width: 26px; height: 26px; border: none; background: #f0f0f0;
  border-radius: 6px; font-size: 1rem; cursor: pointer; color: #999;
  display: flex; align-items: center; justify-content: center;
  align-self: flex-start;
}
.entry-remove-btn:hover { background: #ffe0e0; color: #d00; }
.entry-content {
  width: 100%; resize: vertical; padding: 6px 8px;
  border: 1px solid #d9d9d9; border-radius: 6px; font-size: 0.8rem;
  font-family: ui-monospace, monospace; line-height: 1.5;
}
.entry-content:focus { outline: none; border-color: #667eea; }
</style>
```

- [ ] **Step 3: Create ProjectEntryCard.vue**

Create `frontend/src/components/ProjectEntryCard.vue`:

```vue
<script setup lang="ts">
import type { EntryData } from '../utils/sectionParsers'
import ChipInput from './ChipInput.vue'

const props = defineProps<{
  entry: EntryData
}>()

const emit = defineEmits<{
  'update:entry': [value: EntryData]
  remove: []
}>()

function update(fields: Partial<EntryData>) {
  emit('update:entry', { ...props.entry, ...fields })
}
</script>

<template>
  <div class="entry-card">
    <div class="entry-header">
      <div class="entry-fields">
        <div class="field-row">
          <div class="field">
            <label>Project Name</label>
            <input :value="entry.name" @input="update({ name: ($event.target as HTMLInputElement).value })" placeholder="e.g. MyProject" />
          </div>
          <div class="field">
            <label>URL</label>
            <input :value="entry.url" @input="update({ url: ($event.target as HTMLInputElement).value })" placeholder="e.g. https://github.com/you/project" />
          </div>
        </div>
        <div class="field">
          <label>Tech Stack</label>
          <ChipInput
            :modelValue="entry.techStack || []"
            @update:modelValue="update({ techStack: $event })"
            placeholder="Type a tech and press Enter"
          />
        </div>
      </div>
      <button class="entry-remove-btn" @click="$emit('remove')" title="Remove entry">&times;</button>
    </div>
    <textarea
      class="entry-content"
      :value="entry.content"
      @input="update({ content: ($event.target as HTMLTextAreaElement).value })"
      placeholder="- What you built and the impact&#10;- Quantified result"
      rows="3"
    />
  </div>
</template>

<style scoped>
.entry-card {
  border: 1px solid #e8e8e8; border-radius: 8px; padding: 10px;
  background: #fafafa;
}
.entry-header { display: flex; gap: 6px; margin-bottom: 6px; }
.entry-fields { flex: 1; display: flex; flex-direction: column; gap: 6px; }
.field-row { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.field { display: flex; flex-direction: column; gap: 2px; }
.field label { font-size: 0.7rem; font-weight: 600; color: #888; }
.field input {
  padding: 5px 8px; border: 1px solid #d9d9d9; border-radius: 6px;
  font-size: 0.82rem; font-family: ui-monospace, monospace;
}
.field input:focus { outline: none; border-color: #667eea; }
.entry-remove-btn {
  width: 26px; height: 26px; border: none; background: #f0f0f0;
  border-radius: 6px; font-size: 1rem; cursor: pointer; color: #999;
  display: flex; align-items: center; justify-content: center;
  align-self: flex-start;
}
.entry-remove-btn:hover { background: #ffe0e0; color: #d00; }
.entry-content {
  width: 100%; resize: vertical; padding: 6px 8px;
  border: 1px solid #d9d9d9; border-radius: 6px; font-size: 0.8rem;
  font-family: ui-monospace, monospace; line-height: 1.5;
}
.entry-content:focus { outline: none; border-color: #667eea; }
</style>
```

- [ ] **Step 4: Create SkillCategoryCard.vue**

Create `frontend/src/components/SkillCategoryCard.vue`:

```vue
<script setup lang="ts">
import type { EntryData } from '../utils/sectionParsers'
import ChipInput from './ChipInput.vue'

const props = defineProps<{
  entry: EntryData
}>()

const emit = defineEmits<{
  'update:entry': [value: EntryData]
  remove: []
}>()

function update(fields: Partial<EntryData>) {
  emit('update:entry', { ...props.entry, ...fields })
}
</script>

<template>
  <div class="skill-cat-card">
    <div class="skill-cat-header">
      <input
        class="cat-name-input"
        :value="entry.categoryName"
        @input="update({ categoryName: ($event.target as HTMLInputElement).value })"
        placeholder="Category name (e.g. Programming)"
      />
      <button class="entry-remove-btn" @click="$emit('remove')" title="Remove category">&times;</button>
    </div>
    <ChipInput
      :modelValue="entry.skills || []"
      @update:modelValue="update({ skills: $event })"
      placeholder="Type a skill and press Enter"
    />
  </div>
</template>

<style scoped>
.skill-cat-card {
  border: 1px solid #e8e8e8; border-radius: 8px; padding: 10px;
  background: #fafafa;
  display: flex; flex-direction: column; gap: 6px;
}
.skill-cat-header {
  display: flex; align-items: center; gap: 6px;
}
.cat-name-input {
  flex: 1; padding: 5px 8px; border: 1px solid #d9d9d9; border-radius: 6px;
  font-size: 0.82rem; font-weight: 600;
}
.cat-name-input:focus { outline: none; border-color: #667eea; }
.entry-remove-btn {
  width: 26px; height: 26px; border: none; background: #f0f0f0;
  border-radius: 6px; font-size: 1rem; cursor: pointer; color: #999;
  display: flex; align-items: center; justify-content: center;
}
.entry-remove-btn:hover { background: #ffe0e0; color: #d00; }
</style>
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ExperienceEntryCard.vue frontend/src/components/EducationEntryCard.vue frontend/src/components/ProjectEntryCard.vue frontend/src/components/SkillCategoryCard.vue
git commit -m "feat: add specialized entry card components for Experience, Education, Projects, Skills"
```

---

### Task 5: Update SectionCard with Type Dispatch and Entry Reordering

**Files:**
- Modify: `frontend/src/components/SectionCard.vue`

- [ ] **Step 1: Rewrite SectionCard.vue**

Replace the full content of `frontend/src/components/SectionCard.vue`:

```vue
<script setup lang="ts">
import { ref } from 'vue'
import type { EntryData, SectionType } from '../utils/sectionParsers'
import EntryCard from './EntryCard.vue'
import ExperienceEntryCard from './ExperienceEntryCard.vue'
import EducationEntryCard from './EducationEntryCard.vue'
import ProjectEntryCard from './ProjectEntryCard.vue'
import SkillCategoryCard from './SkillCategoryCard.vue'

const props = defineProps<{
  title: string
  sectionType: SectionType
  content?: string
  entries?: EntryData[]
  isFirst?: boolean
  isLast?: boolean
}>()

const emit = defineEmits<{
  'update:content': [value: string]
  'update:entries': [value: EntryData[]]
  remove: []
  moveUp: []
  moveDown: []
}>()

const collapsed = ref(false)

const isMultiEntry = ['experience', 'education', 'projects', 'skills'].includes(props.sectionType)

function updateEntry(index: number, updated: EntryData) {
  if (!props.entries) return
  const list = [...props.entries]
  list[index] = updated
  emit('update:entries', list)
}

function removeEntry(index: number) {
  if (!props.entries) return
  emit('update:entries', props.entries.filter((_, i) => i !== index))
}

function moveEntryUp(index: number) {
  if (!props.entries || index === 0) return
  const list = [...props.entries]
  ;[list[index - 1], list[index]] = [list[index], list[index - 1]]
  emit('update:entries', list)
}

function moveEntryDown(index: number) {
  if (!props.entries || index >= props.entries.length - 1) return
  const list = [...props.entries]
  ;[list[index], list[index + 1]] = [list[index + 1], list[index]]
  emit('update:entries', list)
}

function addEntry() {
  const key = `new-${Date.now()}`
  const base: EntryData = { key, header: '', content: '' }

  let newEntry: EntryData
  switch (props.sectionType) {
    case 'experience':
      newEntry = { ...base, role: '', company: '', startDate: '', endDate: '' }
      break
    case 'education':
      newEntry = { ...base, degree: '', university: '', startDate: '', endDate: '' }
      break
    case 'projects':
      newEntry = { ...base, name: '', url: '', techStack: [] }
      break
    case 'skills':
      newEntry = { ...base, categoryName: '', skills: [] }
      break
    default:
      newEntry = base
  }

  emit('update:entries', [...(props.entries || []), newEntry])
}

const ADD_LABELS: Record<string, string> = {
  experience: '+ Add Experience',
  education: '+ Add Education',
  projects: '+ Add Project',
  skills: '+ Add Skill Category',
}

const addLabel = ADD_LABELS[props.sectionType] || '+ Add Entry'
</script>

<template>
  <div class="section-card">
    <div class="section-header" @click="collapsed = !collapsed">
      <div class="section-arrows" @click.stop>
        <button v-if="!isFirst" class="arrow-btn" @click="$emit('moveUp')" title="Move section up">&#9650;</button>
        <button v-if="!isLast" class="arrow-btn" @click="$emit('moveDown')" title="Move section down">&#9660;</button>
      </div>
      <span class="collapse-icon">{{ collapsed ? '+' : '-' }}</span>
      <h3>{{ title }}</h3>
      <span class="entry-count" v-if="isMultiEntry && entries">{{ entries.length }} {{ sectionType === 'skills' ? 'categories' : 'entries' }}</span>
      <button class="section-remove-btn" @click.stop="$emit('remove')" title="Remove section">&times;</button>
    </div>

    <div v-show="!collapsed" class="section-body">
      <!-- Single-content section (generic) -->
      <template v-if="!isMultiEntry">
        <textarea
          class="section-textarea"
          :value="content"
          @input="$emit('update:content', ($event.target as HTMLTextAreaElement).value)"
          :placeholder="`${title} content (markdown)...`"
          rows="4"
        />
      </template>

      <!-- Multi-entry section -->
      <template v-else>
        <div class="entries-list">
          <div v-for="(entry, index) in entries" :key="entry.key" class="entry-wrapper">
            <div class="entry-arrows">
              <button v-if="index > 0" class="arrow-btn" @click="moveEntryUp(index)" title="Move up">&#9650;</button>
              <button v-if="entries && index < entries.length - 1" class="arrow-btn" @click="moveEntryDown(index)" title="Move down">&#9660;</button>
            </div>
            <div class="entry-content-area">
              <ExperienceEntryCard
                v-if="sectionType === 'experience'"
                :entry="entry"
                @update:entry="updateEntry(index, $event)"
                @remove="removeEntry(index)"
              />
              <EducationEntryCard
                v-else-if="sectionType === 'education'"
                :entry="entry"
                @update:entry="updateEntry(index, $event)"
                @remove="removeEntry(index)"
              />
              <ProjectEntryCard
                v-else-if="sectionType === 'projects'"
                :entry="entry"
                @update:entry="updateEntry(index, $event)"
                @remove="removeEntry(index)"
              />
              <SkillCategoryCard
                v-else-if="sectionType === 'skills'"
                :entry="entry"
                @update:entry="updateEntry(index, $event)"
                @remove="removeEntry(index)"
              />
              <EntryCard
                v-else
                :header="entry.header"
                :content="entry.content"
                @update:header="updateEntry(index, { ...entry, header: $event })"
                @update:content="updateEntry(index, { ...entry, content: $event })"
                @remove="removeEntry(index)"
              />
            </div>
          </div>
        </div>
        <button class="add-entry-btn" @click="addEntry">{{ addLabel }}</button>
      </template>
    </div>
  </div>
</template>

<style scoped>
.section-card {
  background: #fff; border: 1px solid #e0e0e0; border-radius: 12px;
  overflow: hidden;
}
.section-header {
  display: flex; align-items: center; gap: 8px;
  padding: 12px 14px; cursor: pointer; user-select: none;
  background: #f8f8f8; border-bottom: 1px solid #e0e0e0;
}
.section-header:hover { background: #f0f0f0; }
.section-arrows {
  display: flex; flex-direction: column; gap: 2px;
}
.arrow-btn {
  width: 18px; height: 16px; border: none; background: transparent;
  cursor: pointer; font-size: 0.6rem; color: #999; border-radius: 3px;
  display: flex; align-items: center; justify-content: center; padding: 0;
}
.arrow-btn:hover { background: #e0e0e0; color: #333; }
.collapse-icon {
  width: 20px; height: 20px; display: flex; align-items: center;
  justify-content: center; font-weight: 700; font-size: 1rem; color: #666;
}
.section-header h3 { margin: 0; font-size: 0.9rem; flex: 1; }
.entry-count { font-size: 0.75rem; color: #999; }
.section-remove-btn {
  width: 24px; height: 24px; border: none; background: transparent;
  font-size: 1.1rem; cursor: pointer; color: #bbb; border-radius: 4px;
}
.section-remove-btn:hover { background: #ffe0e0; color: #d00; }
.section-body { padding: 12px 14px; }
.section-textarea {
  width: 100%; resize: vertical; padding: 8px; border: 1px solid #d9d9d9;
  border-radius: 8px; font-size: 0.82rem; font-family: ui-monospace, monospace;
  line-height: 1.5;
}
.section-textarea:focus { outline: none; border-color: #667eea; }
.entries-list { display: flex; flex-direction: column; gap: 8px; }
.entry-wrapper { display: flex; gap: 4px; align-items: flex-start; }
.entry-arrows {
  display: flex; flex-direction: column; gap: 2px; padding-top: 8px;
  min-width: 20px;
}
.entry-content-area { flex: 1; min-width: 0; }
.add-entry-btn {
  margin-top: 8px; width: 100%; padding: 8px; border: 1px dashed #ccc;
  border-radius: 8px; background: #fafafa; font-size: 0.82rem;
  font-weight: 600; cursor: pointer; color: #666;
}
.add-entry-btn:hover { background: #f0f0f0; border-color: #999; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/SectionCard.vue
git commit -m "feat: update SectionCard with type dispatch, entry reordering arrows"
```

---

### Task 6: Update SectionEditor with New Parsers and Section Reordering

**Files:**
- Modify: `frontend/src/components/SectionEditor.vue`

- [ ] **Step 1: Rewrite SectionEditor.vue**

Replace the full content of `frontend/src/components/SectionEditor.vue`:

```vue
<script setup lang="ts">
import { ref, watch } from 'vue'
import SectionCard from './SectionCard.vue'
import {
  getSectionType, isMultiEntryType,
  parseSectionEntries, assembleSectionContent,
  type EntryData, type SectionType,
} from '../utils/sectionParsers'

const props = defineProps<{ markdown: string }>()
const emit = defineEmits<{ 'update:markdown': [value: string] }>()

// --- Frontmatter fields ---
const fmName = ref('')
const fmTitle = ref('')
const fmEmail = ref('')
const fmPhone = ref('')
const fmPortfolio = ref('')
const fmGithub = ref('')
const fmLinkedin = ref('')
const fmFontSize = ref('11')
const fmLineSpacing = ref('1.4')

// --- Sections ---
interface SectionState {
  name: string
  sectionType: SectionType
  content: string
  entries: EntryData[]
}

const sections = ref<SectionState[]>([])
let skipEmit = false

// --- Parse markdown into state ---
function parseMarkdown(md: string) {
  skipEmit = true

  // Parse frontmatter
  const fmMatch = md.match(/^---\s*\n([\s\S]*?)\n---\s*\n?([\s\S]*)/)
  const fmBlock = fmMatch ? fmMatch[1] : ''
  const body = fmMatch ? fmMatch[2] : md

  const fmData: Record<string, string> = {}
  for (const line of fmBlock.split('\n')) {
    const kv = line.match(/^\s*([A-Za-z0-9_]+)\s*:\s*(.*)\s*$/)
    if (kv) fmData[kv[1]] = kv[2].trim().replace(/^["'](.*)["']$/, '$1')
  }

  fmName.value = fmData.name || ''
  fmTitle.value = fmData.title || ''
  fmEmail.value = fmData.email || ''
  fmPhone.value = fmData.phone || ''
  fmPortfolio.value = fmData.portfolio || ''
  fmGithub.value = fmData.github || ''
  fmLinkedin.value = fmData.linkedin || ''
  fmFontSize.value = fmData.font_size || '11'
  fmLineSpacing.value = fmData.line_spacing || '1.4'

  // Parse sections
  const sectionList: SectionState[] = []
  const parts = body.split(/^# /m)

  for (const part of parts) {
    const trimmed = part.trim()
    if (!trimmed) continue

    const newlineIdx = trimmed.indexOf('\n')
    const name = newlineIdx > -1 ? trimmed.substring(0, newlineIdx).trim() : trimmed.trim()
    let content = newlineIdx > -1 ? trimmed.substring(newlineIdx + 1) : ''
    // Strip separator lines
    content = content.replace(/^\s*---\s*$/gm, '').trim()

    const sectionType = getSectionType(name)

    if (isMultiEntryType(sectionType)) {
      const entries = parseSectionEntries(content, sectionType)
      sectionList.push({ name, sectionType, content: '', entries })
    } else {
      sectionList.push({ name, sectionType, content, entries: [] })
    }
  }

  sections.value = sectionList
  skipEmit = false
}

// --- Reassemble markdown from state ---
function assembleMarkdown(): string {
  const fmLines = [
    '---',
    `name: ${fmName.value}`,
    `title: ${fmTitle.value}`,
    `email: ${fmEmail.value}`,
    `phone: ${fmPhone.value}`,
  ]
  if (fmPortfolio.value) fmLines.push(`portfolio: ${fmPortfolio.value}`)
  if (fmGithub.value) fmLines.push(`github: ${fmGithub.value}`)
  if (fmLinkedin.value) fmLines.push(`linkedin: ${fmLinkedin.value}`)
  fmLines.push(`font_size: ${fmFontSize.value}`)
  fmLines.push(`line_spacing: ${fmLineSpacing.value}`)
  fmLines.push('')
  fmLines.push('---')

  const sectionParts: string[] = []
  for (const section of sections.value) {
    let sectionContent = ''
    if (isMultiEntryType(section.sectionType)) {
      sectionContent = assembleSectionContent(section.entries, section.sectionType)
    } else {
      sectionContent = section.content
    }
    sectionParts.push(`# ${section.name}\n\n${sectionContent}`)
  }

  return fmLines.join('\n') + '\n' + sectionParts.join('\n\n---\n\n') + '\n'
}

function emitUpdate() {
  if (skipEmit) return
  emit('update:markdown', assembleMarkdown())
}

// Parse on initial load
parseMarkdown(props.markdown)

// Re-parse if markdown prop changes externally
watch(() => props.markdown, (newVal) => {
  const current = assembleMarkdown()
  if (newVal.trim() !== current.trim()) {
    parseMarkdown(newVal)
  }
})

// --- Section management ---
function addSection() {
  sections.value.push({
    name: 'New Section',
    sectionType: 'generic',
    content: '',
    entries: [],
  })
  emitUpdate()
}

function removeSection(index: number) {
  sections.value.splice(index, 1)
  emitUpdate()
}

function moveSectionUp(index: number) {
  if (index === 0) return
  const list = sections.value
  ;[list[index - 1], list[index]] = [list[index], list[index - 1]]
  sections.value = [...list]
  emitUpdate()
}

function moveSectionDown(index: number) {
  if (index >= sections.value.length - 1) return
  const list = sections.value
  ;[list[index], list[index + 1]] = [list[index + 1], list[index]]
  sections.value = [...list]
  emitUpdate()
}

function updateSectionContent(index: number, value: string) {
  sections.value[index].content = value
  emitUpdate()
}

function updateSectionEntries(index: number, entries: EntryData[]) {
  sections.value[index].entries = entries
  emitUpdate()
}

// Template for new resumes
const STARTER_TEMPLATE = `---
name: Your Name
title: Software Engineer | City
email: your@email.com
phone: +1234567890
github: github.com/you
linkedin: linkedin.com/in/you
font_size: 11
line_spacing: 1.4

---
# Summary

A brief professional summary.

---
# Education

**Degree — University** *Start – End*
***Coursework***: Subject1; Subject2.

---
# Skills

**Category:** Skill1, Skill2, Skill3.

---
# Experience

**Role — Company (Location)** *Start – Present*
- Achievement or responsibility.

---
# Projects

**[Project Name](https://github.com/you/project)** | Stack - Tech1, Tech2
- What you built and the impact.
`

function loadTemplate() {
  parseMarkdown(STARTER_TEMPLATE)
  emit('update:markdown', STARTER_TEMPLATE)
}
</script>

<template>
  <div class="section-editor">
    <!-- Empty state -->
    <div v-if="!props.markdown && sections.length === 0" class="empty-state">
      <p>No resume yet. Start with a template or paste your markdown.</p>
      <button class="template-btn" @click="loadTemplate">Start with Template</button>
    </div>

    <template v-else>
      <!-- Resume Header -->
      <div class="fm-card">
        <h3>Resume Header</h3>
        <div class="fm-grid">
          <div class="fm-field">
            <label>Name</label>
            <input v-model="fmName" @input="emitUpdate()" placeholder="Your Name" />
          </div>
          <div class="fm-field">
            <label>Title / Location</label>
            <input v-model="fmTitle" @input="emitUpdate()" placeholder="Software Engineer | City" />
          </div>
          <div class="fm-field">
            <label>Email</label>
            <input v-model="fmEmail" @input="emitUpdate()" placeholder="you@email.com" />
          </div>
          <div class="fm-field">
            <label>Phone</label>
            <input v-model="fmPhone" @input="emitUpdate()" placeholder="+1234567890" />
          </div>
          <div class="fm-field">
            <label>Portfolio</label>
            <input v-model="fmPortfolio" @input="emitUpdate()" placeholder="yoursite.com" />
          </div>
          <div class="fm-field">
            <label>GitHub</label>
            <input v-model="fmGithub" @input="emitUpdate()" placeholder="github.com/you" />
          </div>
          <div class="fm-field">
            <label>LinkedIn</label>
            <input v-model="fmLinkedin" @input="emitUpdate()" placeholder="linkedin.com/in/you" />
          </div>
        </div>
      </div>

      <!-- Section Cards -->
      <SectionCard
        v-for="(section, index) in sections"
        :key="section.name + '-' + index"
        :title="section.name"
        :sectionType="section.sectionType"
        :content="section.content"
        :entries="section.entries"
        :isFirst="index === 0"
        :isLast="index === sections.length - 1"
        @update:content="updateSectionContent(index, $event)"
        @update:entries="updateSectionEntries(index, $event)"
        @remove="removeSection(index)"
        @moveUp="moveSectionUp(index)"
        @moveDown="moveSectionDown(index)"
      />

      <!-- Add Section -->
      <button class="add-section-btn" @click="addSection">+ Add Section</button>
    </template>
  </div>
</template>

<style scoped>
.section-editor { display: flex; flex-direction: column; gap: 10px; }

.empty-state {
  text-align: center; padding: 40px; color: #999;
  border: 2px dashed #e0e0e0; border-radius: 12px; background: #fafafa;
}
.empty-state p { margin-bottom: 12px; }
.template-btn {
  padding: 10px 24px; border: none; background: #111; color: #fff;
  border-radius: 8px; font-weight: 600; cursor: pointer;
}

.fm-card {
  background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 14px;
}
.fm-card h3 { margin: 0 0 10px; font-size: 0.9rem; }
.fm-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 8px;
}
.fm-field { display: flex; flex-direction: column; gap: 2px; }
.fm-field label { font-size: 0.75rem; font-weight: 600; color: #666; }
.fm-field input {
  padding: 6px 8px; border: 1px solid #d9d9d9; border-radius: 6px;
  font-size: 0.82rem;
}
.fm-field input:focus { outline: none; border-color: #667eea; }

.add-section-btn {
  width: 100%; padding: 10px; border: 1px dashed #ccc; border-radius: 10px;
  background: #fafafa; font-size: 0.85rem; font-weight: 600;
  cursor: pointer; color: #666;
}
.add-section-btn:hover { background: #f0f0f0; border-color: #999; }
</style>
```

- [ ] **Step 2: Run all tests to verify nothing breaks**

Run: `cd frontend && npx vitest run`
Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/SectionEditor.vue
git commit -m "feat: update SectionEditor with type-aware parsing and section reordering"
```

---

### Task 7: Integration Testing — Load Sample Resume and Verify Round-Trip

**Files:**
- Modify: `frontend/src/__tests__/sectionParsers.test.ts`

- [ ] **Step 1: Write round-trip test with real sample resume data**

Append to `frontend/src/__tests__/sectionParsers.test.ts`:

```typescript
describe('round-trip: parse then assemble', () => {
  it('experience entries survive round-trip', () => {
    const original = `**Founding AI Engineer — NestDore (London based startup, ~10 people)**  *October 2025 – March 2026*
- Building the core **intelligent-matching engine**.
- Designing **data pipelines**.

**AI/ML Engineer (Part-Time) — BotWot iCX (Remote, Indian SaaS startup, ~25 people)**  *Jan 2025 – Oct 2025*
- Building orchestrated **multi-agent CRM automation**.`

    const entries = parseExperienceEntries(original)
    const assembled = assembleExperienceEntries(entries)
    // Re-parse the assembled output
    const reparsed = parseExperienceEntries(assembled)
    expect(reparsed).toHaveLength(2)
    expect(reparsed[0].role).toBe('Founding AI Engineer')
    expect(reparsed[0].company).toBe('NestDore (London based startup, ~10 people)')
    expect(reparsed[1].role).toBe('AI/ML Engineer (Part-Time)')
  })

  it('skill categories survive round-trip', () => {
    const original = `**Data Engineering:** ETL Pipelines, API Integrations, MongoDB, Supabase, VectorDB.

**Programming:** Python, TypeScript, Go.`

    const entries = parseSkillCategories(original)
    const assembled = assembleSkillCategories(entries)
    const reparsed = parseSkillCategories(assembled)
    expect(reparsed).toHaveLength(2)
    expect(reparsed[0].categoryName).toBe('Data Engineering')
    expect(reparsed[0].skills).toContain('VectorDB')
    expect(reparsed[1].skills).toEqual(['Python', 'TypeScript', 'Go'])
  })

  it('project entries survive round-trip', () => {
    const original = `**[MyProject](https://github.com/me/proj)** | Stack - React, Node.js
- Built a thing.`

    const entries = parseProjectEntries(original)
    const assembled = assembleProjectEntries(entries)
    const reparsed = parseProjectEntries(assembled)
    expect(reparsed).toHaveLength(1)
    expect(reparsed[0].name).toBe('MyProject')
    expect(reparsed[0].url).toBe('https://github.com/me/proj')
    expect(reparsed[0].techStack).toEqual(['React', 'Node.js'])
  })

  it('education entries survive round-trip', () => {
    const original = `**M.Sc. in AI - Brunel University.** *Jan 2025 – Jan 2026*
***Coursework**:* ML, DL.`

    const entries = parseEducationEntries(original)
    const assembled = assembleEducationEntries(entries)
    const reparsed = parseEducationEntries(assembled)
    expect(reparsed).toHaveLength(1)
    expect(reparsed[0].degree).toBe('M.Sc. in AI')
    expect(reparsed[0].university).toBe('Brunel University.')
  })
})
```

- [ ] **Step 2: Run all tests**

Run: `cd frontend && npx vitest run`
Expected: All tests PASS.

- [ ] **Step 3: Start dev server and manually verify with sample resume**

Run: `cd frontend && npm run dev`

Manual verification checklist:
1. Navigate to `/profile` tab
2. Verify the sample resume loads with structured fields (not raw markdown)
3. Experience section shows 4 entries with Role, Company, Start Date, End Date fields
4. Education section shows 2 entries with Degree, University, Start Date, End Date fields
5. Skills section shows categories with chip inputs
6. Projects section shows entries with Name, URL, Tech Stack chips
7. Section up/down arrows work — move a section and verify preview updates
8. Entry up/down arrows work — reorder entries within a section
9. Add a new skill category — type name, add skills via Enter/comma
10. Edit an experience entry — change role, verify preview updates
11. Save the profile and reload — verify no data loss

- [ ] **Step 4: Commit**

```bash
git add frontend/src/__tests__/sectionParsers.test.ts
git commit -m "test: add round-trip integration tests for section parsers"
```

---

### Task 8: Type Check and Final Cleanup

**Files:**
- Possibly fix any TypeScript errors across modified files

- [ ] **Step 1: Run type checker**

Run: `cd frontend && npx vue-tsc --noEmit`
Expected: No errors. If there are errors, fix them.

- [ ] **Step 2: Run full test suite**

Run: `cd frontend && npx vitest run`
Expected: All tests PASS.

- [ ] **Step 3: Build to verify production build works**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors.

- [ ] **Step 4: Final commit if any fixes were needed**

```bash
git add -u frontend/src/
git commit -m "fix: resolve TypeScript and build issues"
```

(Skip this commit if no fixes were needed.)
