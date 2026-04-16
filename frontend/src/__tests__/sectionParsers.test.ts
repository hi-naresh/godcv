import { describe, it, expect } from 'vitest'
import {
  getSectionType,
  isMultiEntryType,
  parseExperienceEntries,
  assembleExperienceEntries,
  type SectionType,
  type EntryData,
} from '../utils/sectionParsers'

describe('getSectionType', () => {
  it('returns "experience" for Experience heading', () => {
    expect(getSectionType('Experience')).toBe('experience')
  })

  it('returns "education" for Education heading', () => {
    expect(getSectionType('Education')).toBe('education')
  })

  it('returns "skills" for Skills heading', () => {
    expect(getSectionType('Skills')).toBe('skills')
  })

  it('returns "projects" for Projects heading', () => {
    expect(getSectionType('Projects')).toBe('projects')
  })

  it('returns "generic" for unknown headings', () => {
    expect(getSectionType('Summary')).toBe('generic')
    expect(getSectionType('Volunteering and Interests')).toBe('generic')
  })

  it('is case-insensitive', () => {
    expect(getSectionType('experience')).toBe('experience')
    expect(getSectionType('SKILLS')).toBe('skills')
  })
})

describe('isMultiEntryType', () => {
  it('returns true for experience, education, projects', () => {
    expect(isMultiEntryType('experience')).toBe(true)
    expect(isMultiEntryType('education')).toBe(true)
    expect(isMultiEntryType('projects')).toBe(true)
  })

  it('returns false for skills and generic', () => {
    expect(isMultiEntryType('skills')).toBe(false)
    expect(isMultiEntryType('generic')).toBe(false)
  })
})

describe('parseExperienceEntries', () => {
  it('parses a standard experience entry with role, company, dates', () => {
    const content =
      '**Founding AI Engineer — NestDore (London based startup, ~10 people)**  *October 2025 – March 2026*\n' +
      '- Building the core intelligent-matching engine.\n' +
      '- Designing data pipelines.'

    const entries = parseExperienceEntries(content)
    expect(entries).toHaveLength(1)
    expect(entries[0].role).toBe('Founding AI Engineer')
    expect(entries[0].company).toBe('NestDore (London based startup, ~10 people)')
    expect(entries[0].startDate).toBe('October 2025')
    expect(entries[0].endDate).toBe('March 2026')
    expect(entries[0].content).toContain('- Building the core')
    expect(entries[0].content).toContain('- Designing data pipelines.')
  })

  it('parses multiple experience entries', () => {
    const content =
      '**Founding AI Engineer — NestDore (London based startup, ~10 people)**  *October 2025 – March 2026*\n' +
      '- Building the core engine.\n' +
      '\n' +
      '**AI/ML Engineer (Part-Time) — BotWot iCX (Remote, Indian SaaS startup, ~25 people)**  *Jan 2025 – Oct 2025*\n' +
      '- Building orchestrated multi-agent CRM automation.'

    const entries = parseExperienceEntries(content)
    expect(entries).toHaveLength(2)
    expect(entries[0].role).toBe('Founding AI Engineer')
    expect(entries[0].company).toBe('NestDore (London based startup, ~10 people)')
    expect(entries[1].role).toBe('AI/ML Engineer (Part-Time)')
    expect(entries[1].company).toBe('BotWot iCX (Remote, Indian SaaS startup, ~25 people)')
    expect(entries[1].startDate).toBe('Jan 2025')
    expect(entries[1].endDate).toBe('Oct 2025')
  })

  it('handles "Present" as end date', () => {
    const content =
      '**Software Engineer — Acme Corp**  *Jan 2024 – Present*\n' +
      '- Working on things.'

    const entries = parseExperienceEntries(content)
    expect(entries).toHaveLength(1)
    expect(entries[0].startDate).toBe('Jan 2024')
    expect(entries[0].endDate).toBe('Present')
  })

  it('falls back to generic entry for unparseable lines', () => {
    const content = 'Just some plain text that is not formatted as experience.'

    const entries = parseExperienceEntries(content)
    expect(entries).toHaveLength(1)
    expect(entries[0].role).toBeUndefined()
    expect(entries[0].company).toBeUndefined()
    expect(entries[0].header).toBe('Just some plain text that is not formatted as experience.')
  })

  it('handles entries with no dates', () => {
    const content =
      '**Software Engineer — Acme Corp**\n' +
      '- Did some work.'

    const entries = parseExperienceEntries(content)
    expect(entries).toHaveLength(1)
    expect(entries[0].role).toBe('Software Engineer')
    expect(entries[0].company).toBe('Acme Corp')
    expect(entries[0].startDate).toBeUndefined()
    expect(entries[0].endDate).toBeUndefined()
    expect(entries[0].content).toContain('- Did some work.')
  })

  it('handles hyphen separator between role and company', () => {
    const content =
      '**Student Software Engineer (Intern) - SAILC AURO, Surat, IN (University)** *Jan 2022 – Dec 2023*\n' +
      '- Developed blockchain-based payment system.'

    const entries = parseExperienceEntries(content)
    expect(entries).toHaveLength(1)
    expect(entries[0].role).toBe('Student Software Engineer (Intern)')
    expect(entries[0].company).toBe('SAILC AURO, Surat, IN (University)')
  })
})

describe('assembleExperienceEntries', () => {
  it('assembles a standard entry with role, company, and dates', () => {
    const entries: EntryData[] = [
      {
        key: '1',
        header: '',
        content: '- Building the core engine.',
        role: 'Founding AI Engineer',
        company: 'NestDore',
        startDate: 'October 2025',
        endDate: 'March 2026',
      },
    ]

    const result = assembleExperienceEntries(entries)
    expect(result).toBe(
      '**Founding AI Engineer — NestDore** *October 2025 – March 2026*\n- Building the core engine.'
    )
  })

  it('omits date portion when both dates are empty', () => {
    const entries: EntryData[] = [
      {
        key: '1',
        header: '',
        content: '- Did some work.',
        role: 'Software Engineer',
        company: 'Acme Corp',
      },
    ]

    const result = assembleExperienceEntries(entries)
    expect(result).toBe('**Software Engineer — Acme Corp**\n- Did some work.')
  })

  it('assembles multiple entries separated by blank lines', () => {
    const entries: EntryData[] = [
      {
        key: '1',
        header: '',
        content: '- Task A.',
        role: 'Role A',
        company: 'Company A',
        startDate: 'Jan 2024',
        endDate: 'Present',
      },
      {
        key: '2',
        header: '',
        content: '- Task B.',
        role: 'Role B',
        company: 'Company B',
        startDate: 'Jan 2023',
        endDate: 'Dec 2023',
      },
    ]

    const result = assembleExperienceEntries(entries)
    expect(result).toBe(
      '**Role A — Company A** *Jan 2024 – Present*\n- Task A.\n\n' +
      '**Role B — Company B** *Jan 2023 – Dec 2023*\n- Task B.'
    )
  })
})
