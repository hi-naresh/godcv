import { marked } from 'marked'

marked.setOptions({ gfm: true, breaks: false })

export interface ResumeSettings {
  fontSize: number
  lineSpacing: number
}

export interface DotLeaderOpts {
  /** The actual font size (px) at which the role line will be rendered.
   *  Pass the auto-fitted size when the preview's --base-font-size is dynamic. */
  fontSizePx: number
  /** Available content width in CSS px (page width minus side padding).
   *  Defaults to the standard A4 single-page sheet content width. */
  contentWidthPx?: number
  /** "single" | "multi" — only matters when contentWidthPx isn't provided. */
  pageMode?: 'single' | 'multi'
}

export interface RenderResumeOpts {
  fontSizePx?: number
  contentWidthPx?: number
  pageMode?: 'single' | 'multi'
  /** Skip frontend dot-leader injection. The backend's PDF pipeline injects
   *  dots at the actual rendered font size (and re-injects on each shrink
   *  attempt), so pre-injecting here would freeze a stale dot count and
   *  also short-circuit the backend's regex. */
  skipDotLeaders?: boolean
}

// CSS px values that mirror the backend's PDF point geometry. A4 is 210mm wide;
// 1mm = 3.7795px at 96dpi. Margins match backend `_PAGE_MARGIN_MM`.
const A4_WIDTH_PX = 210 * 3.7795
const PAGE_MARGIN_PX: Record<'single' | 'multi', number> = {
  single: 6 * 3.7795,
  multi: 14 * 3.7795,
}

// Reuse a single canvas for measurements. In test environments (jsdom) the
// 2d context is unavailable; we fall back to a char-count approximation in
// that case so unit tests can still exercise renderResume.
let _measureCtx: CanvasRenderingContext2D | null | undefined
function getMeasureCtx(): CanvasRenderingContext2D | null {
  if (_measureCtx !== undefined) return _measureCtx
  try {
    const canvas = (typeof document !== 'undefined') ? document.createElement('canvas') : null
    _measureCtx = canvas?.getContext('2d') ?? null
  } catch {
    _measureCtx = null
  }
  return _measureCtx
}

function measurePx(text: string, fontShorthand: string, letterSpacingPx: number = 0): number {
  const ctx = getMeasureCtx()
  let width: number
  if (ctx) {
    ctx.font = fontShorthand
    width = ctx.measureText(text).width
  } else {
    // Fallback when canvas isn't available. Extract font size from the CSS
    // shorthand (e.g. "700 13.5px Georgia, ..."). Bold serif averages ~0.55em
    // per char; regular ~0.50em. The dot character is ~0.25em.
    const sizeMatch = fontShorthand.match(/(\d+(?:\.\d+)?)px/)
    const sizePx = sizeMatch ? parseFloat(sizeMatch[1]) : 11
    const isBold = /\b(700|bold)\b/.test(fontShorthand)
    const perChar = text === '·' ? 0.25 : (isBold ? 0.55 : 0.50)
    width = text.length * perChar * sizePx
  }
  if (letterSpacingPx > 0 && text.length > 1) {
    width += (text.length - 1) * letterSpacingPx
  }
  return width
}

/** Split <p>role + <br/> + stack</p> into two adjacent <p>s so the dot-leader
 *  injection regex can match the role line cleanly. Mirrors backend
 *  `_split_role_paragraphs` exactly. */
function splitRoleParagraphs(html: string): string {
  return html.replace(
    /(<p>\s*<strong>[^<]+<\/strong>\s+<em>[^<]+<\/em>)<br\s*\/?>\s*([\s\S]*?<\/p>)/g,
    '$1</p><p>$2',
  )
}

/** Inject a precisely-calibrated dot-leader between strong and em on role lines.
 *  Mirrors backend `_inject_dot_leaders` — same font (Georgia/Times serif),
 *  same dot scale (0.9em), same letter-spacing (0.15em of own font), same
 *  safety margin. The result is that the on-screen preview and the exported
 *  PDF agree on dot count for every role line. */
function injectDotLeaders(html: string, opts: DotLeaderOpts): string {
  const fontPx = Math.max(opts.fontSizePx, 6)
  const mode = opts.pageMode ?? 'single'
  const contentWidthPx = opts.contentWidthPx ?? (A4_WIDTH_PX - 2 * PAGE_MARGIN_PX[mode])

  const dotSizePx = fontPx * 0.9
  const dotLetterSpacingPx = dotSizePx * 0.15
  const SERIF = 'Georgia, "Times New Roman", serif'
  const dotFont = `400 ${dotSizePx}px ${SERIF}`
  const boldFont = `700 ${fontPx}px ${SERIF}`
  const regularFont = `400 ${fontPx}px ${SERIF}`

  const singleDotPx = measurePx('·', dotFont) + dotLetterSpacingPx
  const spacePadPx = measurePx(' ', regularFont) * 2
  const safetyPx = fontPx * 0.12

  return html.replace(
    /<p>\s*<strong>([^<]+)<\/strong>\s+<em>([^<]+)<\/em>\s*<\/p>/g,
    (_match, title: string, date: string) => {
      const titlePx = measurePx(title, boldFont)
      const datePx = measurePx(date, boldFont)
      const gap = contentWidthPx - titlePx - datePx - spacePadPx - safetyPx
      const dotCount = Math.max(6, Math.floor(gap / singleDotPx))
      const dots = '·'.repeat(dotCount)
      return (
        `<p class="role-line">` +
        `<strong>${title}</strong>` +
        ` <span class="dot-leader" aria-hidden="true">${dots}</span> ` +
        `<em>${date}</em></p>`
      )
    },
  )
}

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
    if (meta.length) parts.push(`<div class="meta">${meta.join('<span class="sep"> &middot; </span>')}</div>`)
    return parts.length ? `<header class="cv-head">${parts.join('')}<hr class="thin"/></header>` : ''
  }

  function renderResume(md: string, opts?: RenderResumeOpts): string {
    const { data, body } = parseFrontmatter(md)
    const header = Object.keys(data).length ? buildHeader(data) : ''
    let bodyHtml = marked.parse(body) as string
    bodyHtml = splitRoleParagraphs(bodyHtml)

    if (!opts?.skipDotLeaders) {
      // Default to the frontmatter font size if no live size is provided.
      const fontSizePx = opts?.fontSizePx ?? (parseFloat(data.font_size) || 11)
      bodyHtml = injectDotLeaders(bodyHtml, {
        fontSizePx,
        contentWidthPx: opts?.contentWidthPx,
        pageMode: opts?.pageMode,
      })
    }

    return `${header}<div class="md">${bodyHtml}</div>`
  }

  function getResumeSettings(md: string): ResumeSettings {
    const { data } = parseFrontmatter(md)
    return {
      fontSize: parseFloat(data.font_size) || 11,
      lineSpacing: parseFloat(data.line_spacing) || 1.4,
    }
  }

  return { renderResume, parseFrontmatter, getResumeSettings, injectDotLeaders, splitRoleParagraphs }
}
