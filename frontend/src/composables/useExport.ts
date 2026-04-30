import { useMarkdown } from './useMarkdown'

interface ExportOptions {
  markdown: string
  pageMode: 'single' | 'multi'
  filename?: string
  documentTitle?: string
  /** Invoked when the backend export fails so the caller can run their existing
   *  window.print() flow as a fallback. */
  onFallback?: () => void
}

export function useExport() {
  const { renderResume, getResumeSettings } = useMarkdown()

  function readComputedSizing(fallback: { fontSize: number; lineSpacing: number }) {
    const root = getComputedStyle(document.documentElement)
    const fs = parseFloat(root.getPropertyValue('--base-font-size'))
    const lh = parseFloat(root.getPropertyValue('--line-height'))
    return {
      fontSize: Number.isFinite(fs) && fs > 0 ? fs : fallback.fontSize,
      lineSpacing: Number.isFinite(lh) && lh > 0 ? lh : fallback.lineSpacing,
    }
  }

  function triggerDownload(blob: Blob, filename: string) {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  async function exportPdf(opts: ExportOptions): Promise<boolean> {
    const settings = getResumeSettings(opts.markdown)
    // Single-page mode runs the auto-fit loop (writes computed sizes onto
    // documentElement). Pick those up so the PDF matches what's on screen.
    // Multi-page mode uses the standard 11px / 1.4 baseline.
    const sizing = opts.pageMode === 'single'
      ? readComputedSizing(settings)
      : { fontSize: 11, lineSpacing: 1.4 }

    // Send raw role/date paragraphs to the backend. The backend's
    // _inject_dot_leaders measures glyphs against the real Georgia font file
    // and recomputes on each auto-shrink attempt, so pre-injecting here would
    // freeze a dot count for the wrong font size and dates wouldn't land flush
    // with the right margin.
    const html = renderResume(opts.markdown, { skipDotLeaders: true })
    const filename = opts.filename || 'resume.pdf'

    try {
      const res = await fetch('/api/export/pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          html,
          font_size: sizing.fontSize,
          line_spacing: sizing.lineSpacing,
          page_mode: opts.pageMode,
          filename,
          document_title: opts.documentTitle ?? null,
        }),
      })
      if (!res.ok) {
        const detail = await res.text().catch(() => '')
        throw new Error(`HTTP ${res.status}: ${detail}`)
      }
      const blob = await res.blob()
      triggerDownload(blob, filename)
      return true
    } catch (err) {
      console.warn('[export] backend PDF failed, falling back to browser print:', err)
      opts.onFallback?.()
      return false
    }
  }

  return { exportPdf }
}
