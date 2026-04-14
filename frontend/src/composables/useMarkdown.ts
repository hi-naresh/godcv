import { marked } from 'marked'

marked.setOptions({ gfm: true, breaks: false })

export function useMarkdown() {
  function parseFrontmatter(md: string): { data: Record<string, string>; body: string } {
    const match = md.match(/^---\s*\n([\s\S]*?)\n---\s*\n?([\s\S]*)/)
    if (!match) return { data: {}, body: md }
    const raw = match[1]
    const data: Record<string, string> = {}
    for (const line of raw.split('\n')) {
      const kv = line.match(/^\s*([A-Za-z0-9_]+)\s*:\s*(.*)\s*$/)
      if (kv) {
        const val = kv[2].trim().replace(/^["'](.*)["']$/, '$1')
        if (!kv[1].startsWith('#')) data[kv[1]] = val
      }
    }
    return { data, body: match[2] }
  }

  function escapeHtml(s: string): string {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
  }

  function buildHeader(data: Record<string, string>): string {
    const safe = (x?: string) => x ? escapeHtml(x) : ''
    const linkify = (v: string) => /^https?:\/\//i.test(v) ? v : 'https://' + v.replace(/^\/+/, '')
    const parts: string[] = []
    if (data.name) parts.push(`<div class="name">${safe(data.name)}</div>`)
    if (data.title) parts.push(`<div class="role">${safe(data.title)}</div>`)
    const meta: string[] = []
    if (data.email) meta.push(`<a href="mailto:${safe(data.email)}">${safe(data.email)}</a>`)
    if (data.phone) meta.push(`<a href="tel:${safe(data.phone)}">${safe(data.phone)}</a>`)
    for (const key of ['portfolio', 'github', 'linkedin']) {
      if (data[key]) meta.push(`<a href="${linkify(data[key])}" target="_blank" rel="noopener">${safe(data[key])}</a>`)
    }
    if (meta.length) parts.push(`<div class="meta">${meta.join(' &middot; ')}</div>`)
    return parts.length ? `<header class="cv-head">${parts.join('')}<hr class="thin"/></header>` : ''
  }

  function renderResume(md: string): string {
    const { data, body } = parseFrontmatter(md)
    const header = Object.keys(data).length ? buildHeader(data) : ''
    const bodyHtml = marked.parse(body) as string
    return `${header}<div class="md">${bodyHtml}</div>`
  }

  return { renderResume, parseFrontmatter }
}
