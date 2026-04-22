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

describe('skills section setext heading regression', () => {
  /**
   * When a skill is accepted into the Skills section the accepted markdown must
   * NOT trigger markdown's setext-heading rule (any text line directly followed
   * by "---" becomes an h2).  The accepted content must end with a blank line
   * before the section separator so the last skill category stays as a plain
   * paragraph, not a heading.
   *
   * Correct:   **Cloud:** AWS, Docker, Terraform.\n\n---
   * Broken:    **Cloud:** AWS, Docker, Terraform\n---   ← becomes <h2>
   */
  function simulateSkillAccept(md: string, skillContent: string): string {
    const skillsMatch = md.match(/(# Skills\n)([\s\S]*?)(\n---|\n# |\n*$)/)
    if (!skillsMatch) return md
    const before = skillsMatch[1]
    const content = skillsMatch[2].trimEnd().replace(/\.$/, '')
    const after = skillsMatch[3]
    return md.replace(skillsMatch[0], before + content + ', ' + skillContent + '.\n' + after)
  }

  it('does not promote last skills category to h2 when followed by ---', () => {
    const md = [
      '# Skills',
      '',
      '**Backend:** Python, FastAPI.',
      '',
      '**Cloud:** AWS, Docker.',
      '',
      '---',
      '# Experience',
    ].join('\n')

    const updated = simulateSkillAccept(md, 'Terraform')
    const html = renderResume(updated)

    // The last category must NOT be rendered as a heading
    expect(html).not.toMatch(/<h2[^>]*>.*Cloud.*<\/h2>/i)
    expect(html).not.toMatch(/<h1[^>]*>.*Cloud.*<\/h1>/i)
    // It should appear inside a paragraph
    expect(html).toMatch(/<p[^>]*>.*Cloud.*<\/p>/s)
    // The new skill must be present
    expect(html).toContain('Terraform')
  })

  it('does not promote last skills category to h2 when followed by # section', () => {
    const md = [
      '# Skills',
      '',
      '**Backend:** Python.',
      '',
      '**AI/ML:** PyTorch.',
      '',
      '# Experience',
    ].join('\n')

    const updated = simulateSkillAccept(md, 'TensorFlow')
    const html = renderResume(updated)

    expect(html).not.toMatch(/<h2[^>]*>.*AI\/ML.*<\/h2>/i)
    expect(html).toContain('TensorFlow')
  })

  it('places new skill inside last category with correct comma formatting', () => {
    const md = [
      '# Skills',
      '',
      '**Backend:** Python, FastAPI.',
      '',
      '**Cloud:** AWS, Docker.',
      '',
      '---',
    ].join('\n')

    const updated = simulateSkillAccept(md, 'Kubernetes')
    // Must end with period, no ".,"-style broken punctuation
    expect(updated).toContain('**Cloud:** AWS, Docker, Kubernetes.')
    expect(updated).not.toContain('.,')
  })

  it('preserves the rest of the document after accepting a skill', () => {
    const md = [
      '# Skills',
      '',
      '**Backend:** Python.',
      '',
      '---',
      '# Experience',
      '',
      '**Engineer — Corp** *2023 – Present*',
      '- Built systems.',
    ].join('\n')

    const updated = simulateSkillAccept(md, 'FastAPI')
    expect(updated).toContain('# Experience')
    expect(updated).toContain('Built systems.')
  })
})
