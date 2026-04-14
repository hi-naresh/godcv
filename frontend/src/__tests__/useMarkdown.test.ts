import { describe, it, expect } from 'vitest'
import { useMarkdown } from '../composables/useMarkdown'

const { renderResume, parseFrontmatter, getResumeSettings } = useMarkdown()

describe('parseFrontmatter', () => {
  it('extracts name and title', () => {
    const md = '---\nname: John Doe\ntitle: Engineer\n---\n# Summary\nHello'
    const { data, body } = parseFrontmatter(md)
    expect(data.name).toBe('John Doe')
    expect(data.title).toBe('Engineer')
    expect(body).toContain('# Summary')
  })

  it('extracts font_size and line_spacing', () => {
    const md = '---\nname: Jane\nfont_size: 10.5\nline_spacing: 1.3\n---\nBody'
    const { data } = parseFrontmatter(md)
    expect(data.font_size).toBe('10.5')
    expect(data.line_spacing).toBe('1.3')
  })

  it('returns empty data for no frontmatter', () => {
    const md = '# Summary\nHello'
    const { data, body } = parseFrontmatter(md)
    expect(Object.keys(data).length).toBe(0)
    expect(body).toBe(md)
  })
})

describe('getResumeSettings', () => {
  it('returns custom font_size and line_spacing', () => {
    const md = '---\nname: Jane\nfont_size: 10.5\nline_spacing: 1.3\n---\nBody'
    const settings = getResumeSettings(md)
    expect(settings.fontSize).toBe(10.5)
    expect(settings.lineSpacing).toBe(1.3)
  })

  it('returns defaults when not specified', () => {
    const md = '---\nname: Jane\n---\nBody'
    const settings = getResumeSettings(md)
    expect(settings.fontSize).toBe(11)
    expect(settings.lineSpacing).toBe(1.4)
  })

  it('returns defaults for no frontmatter', () => {
    const settings = getResumeSettings('# Hello')
    expect(settings.fontSize).toBe(11)
    expect(settings.lineSpacing).toBe(1.4)
  })
})

describe('renderResume', () => {
  it('renders header with name and meta', () => {
    const md = '---\nname: John Doe\ntitle: Engineer\nemail: john@example.com\n---\n# Summary\nHello'
    const html = renderResume(md)
    expect(html).toContain('class="name"')
    expect(html).toContain('John Doe')
    expect(html).toContain('john@example.com')
  })

  it('does not crash on empty input', () => {
    const html = renderResume('')
    expect(html).toBeDefined()
  })

  it('does not crash on malformed markdown', () => {
    const html = renderResume('---\nbroken\n# Huh')
    expect(html).toBeDefined()
  })
})
