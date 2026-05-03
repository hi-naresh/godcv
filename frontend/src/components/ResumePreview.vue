<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue'
import { useMarkdown } from '../composables/useMarkdown'

const props = defineProps<{
  markdown: string
  originalMarkdown?: string
  pageMode: 'single' | 'multi'
  rawMode?: boolean
  agentStatuses?: Record<string, 'pending' | 'running' | 'done'>
}>()

const emit = defineEmits<{
  'update:markdown': [value: string]
}>()

const { renderResume, getResumeSettings } = useMarkdown()
const contentRef = ref<HTMLElement>()
const showWarn = ref(false)

const settings = computed(() => getResumeSettings(props.markdown))

// Dynamic font size: starts at the frontmatter value, then fitToOnePage
// updates it after auto-fit so dot-leader counts in the DOM match what the
// PDF export will produce. 0 means "use frontmatter setting".
const effectiveFontSize = ref(0)

// Map agent keys to section header text for inline indicators
const refiningSections = computed(() => {
  if (!props.agentStatuses) return new Set<string>()
  const sections = new Set<string>()
  for (const [key, status] of Object.entries(props.agentStatuses)) {
    if (status === 'running' || status === 'pending') {
      const agent = key.split(':')[0]
      if (agent === 'summary') sections.add('Summary')
      else if (agent === 'skills') sections.add('Skills')
      else if (agent === 'experience') sections.add('Experience')
      else if (agent === 'projects') sections.add('Projects')
    }
  }
  return sections
})

// Build a set of normalized text lines from rendered HTML for diffing
function extractTextLines(html: string): Set<string> {
  const lines = new Set<string>()
  const liRegex = /<li>([\s\S]*?)<\/li>/gi
  let m
  while ((m = liRegex.exec(html)) !== null) {
    const text = m[1].replace(/<[^>]+>/g, '').trim()
    if (text) lines.add(text)
  }
  const pRegex = /<p>([\s\S]*?)<\/p>/gi
  while ((m = pRegex.exec(html)) !== null) {
    const text = m[1].replace(/<[^>]+>/g, '').trim()
    if (text.length > 20) lines.add(text)
  }
  return lines
}

// Extract a Map<normalizedText, normalizedText> from a tag type for closest-match lookup
function extractTextMap(html: string, tag: 'li' | 'p'): Map<string, string> {
  const map = new Map<string, string>()
  const rx = tag === 'li' ? /<li>([\s\S]*?)<\/li>/gi : /<p>([\s\S]*?)<\/p>/gi
  let m
  while ((m = rx.exec(html)) !== null) {
    const text = m[1].replace(/<[^>]+>/g, '').trim()
    if (text && (tag === 'li' ? text.length > 0 : text.length > 20)) map.set(text, text)
  }
  return map
}

// Returns 0-indexed positions in newWords that are "added" (not matched by LCS with origWords)
function getChangedPositions(origWords: string[], newWords: string[]): Set<number> {
  const m = origWords.length, n = newWords.length
  const dp: number[][] = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0))
  for (let i = 1; i <= m; i++)
    for (let j = 1; j <= n; j++)
      dp[i][j] = origWords[i-1].toLowerCase() === newWords[j-1].toLowerCase()
        ? dp[i-1][j-1] + 1
        : Math.max(dp[i-1][j], dp[i][j-1])

  const changed = new Set<number>()
  let i = m, j = n
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && origWords[i-1].toLowerCase() === newWords[j-1].toLowerCase()) {
      i--; j--
    } else if (j > 0 && (i === 0 || dp[i][j-1] >= dp[i-1][j])) {
      changed.add(j - 1); j--
    } else {
      i--
    }
  }
  return changed
}

// Build a global set of all words (≥2 chars, lowercased, stripped of punctuation)
// that appear anywhere in the original HTML. Used to distinguish "moved" words
// (existed in original but shifted position) from truly new words.
function buildOriginalWordSet(originalHtml: string): Set<string> {
  const set = new Set<string>()
  const text = originalHtml.replace(/<[^>]+>/g, ' ')
  for (const w of text.split(/\s+/)) {
    const clean = w.replace(/[^a-zA-Z0-9]/g, '').toLowerCase()
    if (clean.length >= 2) set.add(clean)
  }
  return set
}

// Inject <span class="word-changed"> around changed words directly into innerHtml,
// leaving every HTML tag (bold, italic, etc.) completely untouched.
// globalOrigWords: set of every word that appeared anywhere in the original document.
// Words in that set are "moved/reordered" — not highlighted even if LCS marks them added.
function injectChangedSpans(innerHtml: string, origText: string, globalOrigWords: Set<string>): string {
  const newText = innerHtml.replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim()
  if (!newText) return innerHtml

  const origWords = origText.split(/\s+/).filter(Boolean)
  const newWords = newText.split(/\s+/).filter(Boolean)
  const changedPositions = getChangedPositions(origWords, newWords)
  if (changedPositions.size === 0) return innerHtml

  // Walk the HTML: pass tags through as-is, annotate words only in text nodes
  let wordIndex = 0
  let result = ''
  let pos = 0
  while (pos < innerHtml.length) {
    if (innerHtml[pos] === '<') {
      const tagEnd = innerHtml.indexOf('>', pos)
      if (tagEnd === -1) { result += innerHtml.slice(pos); break }
      result += innerHtml.slice(pos, tagEnd + 1)
      pos = tagEnd + 1
    } else {
      const nextTag = innerHtml.indexOf('<', pos)
      const textEnd = nextTag === -1 ? innerHtml.length : nextTag
      const textNode = innerHtml.slice(pos, textEnd)
      result += textNode.replace(/(\S+)/g, (word) => {
        const idx = wordIndex++
        if (!changedPositions.has(idx)) return word
        // Skip words already present anywhere in the original (moved, not new)
        const clean = word.replace(/[^a-zA-Z0-9]/g, '').toLowerCase()
        if (clean.length >= 2 && globalOrigWords.has(clean)) return word
        return `<span class="word-changed">${word}</span>`
      })
      pos = textEnd
    }
  }
  return result
}

// Jaccard similarity between two texts (word-level)
function jaccard(a: string, b: string): number {
  const wa = new Set(a.toLowerCase().split(/\s+/).filter(Boolean))
  const wb = new Set(b.toLowerCase().split(/\s+/).filter(Boolean))
  let inter = 0
  for (const w of wa) if (wb.has(w)) inter++
  const union = wa.size + wb.size - inter
  return union > 0 ? inter / union : 0
}

// Find the closest original text by Jaccard similarity (returns null if below threshold)
function findClosest(text: string, candidates: Map<string, string>, threshold = 0.25): string | null {
  let bestKey: string | null = null
  let bestScore = threshold
  for (const [key] of candidates) {
    const score = jaccard(text, key)
    if (score > bestScore) { bestScore = score; bestKey = key }
  }
  return bestKey
}

function highlightChanges(tailoredHtml: string, originalHtml: string): string {
  const originalLines = extractTextLines(originalHtml)
  const origLiMap = extractTextMap(originalHtml, 'li')
  const origPMap = extractTextMap(originalHtml, 'p')
  // One-time global word set: any word already in the original is "moved", not "new"
  const globalOrigWords = buildOriginalWordSet(originalHtml)

  // Highlight <li> elements with word-level diff
  let html = tailoredHtml.replace(/<li>([\s\S]*?)<\/li>/gi, (match, inner) => {
    const text = inner.replace(/<[^>]+>/g, '').trim()
    if (!text || originalLines.has(text)) return match
    if (match.includes('class="suggestion') || match.includes('class="sug')) return match

    const closest = findClosest(text, origLiMap)
    if (closest) {
      return `<li>${injectChangedSpans(inner, closest, globalOrigWords)}</li>`
    }
    return `<li class="changed-content">${inner}</li>`
  })

  // Highlight <p> elements with word-level diff.
  // This regex only matches bare <p> (no class attribute) — role-line, meta,
  // name, role paragraphs are already skipped because they have class attrs.
  html = html.replace(/<p>([\s\S]*?)<\/p>/gi, (match, inner) => {
    const text = inner.replace(/<[^>]+>/g, '').trim()
    if (!text || text.length <= 20 || originalLines.has(text)) return match
    if (match.includes('class="suggestion') || match.includes('class="sug')) return match
    if (match.includes('class="meta"') || match.includes('class="name"') || match.includes('class="role"')) return match
    // Skip any paragraph that contains <em>: these are structural lines —
    // education coursework ("*Coursework:* ..."), volunteering dates, etc.
    // Role-line title+date paragraphs are already class="role-line" so they
    // never reach here; this guard catches the remaining <em>-bearing lines.
    if (inner.includes('<em>')) return match

    const closest = findClosest(text, origPMap)
    if (closest) {
      return `<p>${injectChangedSpans(inner, closest, globalOrigWords)}</p>`
    }
    return `<p class="changed-content">${inner}</p>`
  })

  return html
}

const renderedHtml = computed(() => {
  const fontSizePx = effectiveFontSize.value || settings.value.fontSize
  let html = renderResume(props.markdown, { fontSizePx, pageMode: props.pageMode })

  // Highlight content that differs from original
  if (props.originalMarkdown && props.originalMarkdown !== props.markdown) {
    const originalHtml = renderResume(props.originalMarkdown)
    html = highlightChanges(html, originalHtml)
  }

  // Inject refining badges into section h1 headers
  for (const section of refiningSections.value) {
    const regex = new RegExp(`(<h1>)(${section})(</h1>)`, 'i')
    html = html.replace(regex, `$1$2 <span class="refining-badge">refining...</span>$3`)
  }
  return html
})

watch([() => props.markdown, () => props.pageMode], async () => {
  await nextTick()
  if (props.pageMode === 'single') {
    fitToOnePage()
  } else {
    applyMultiPageStyles()
  }
}, { immediate: true })

function fitToOnePage() {
  const el = contentRef.value
  if (!el) return
  showWarn.value = false
  let size = settings.value.fontSize
  const lh = settings.value.lineSpacing
  const min = 8
  const maxSize = Math.min(settings.value.fontSize + 2, 16)

  document.documentElement.style.setProperty('--base-font-size', size + 'px')
  document.documentElement.style.setProperty('--line-height', String(lh))

  requestAnimationFrame(() => {
    const target = el.clientHeight

    // Phase 1: shrink font if overflowing
    let safety = 100
    while (el.scrollHeight > target + 1 && size > min && safety--) {
      size = Math.max(min, size - 0.15)
      document.documentElement.style.setProperty('--base-font-size', size + 'px')
    }
    if (el.scrollHeight > target + 1) {
      showWarn.value = true
      effectiveFontSize.value = size
      return
    }

    // Phase 2: grow font to fill space (up to max)
    safety = 100
    while (el.scrollHeight < target - 10 && size < maxSize && safety--) {
      size = Math.min(maxSize, size + 0.15)
      document.documentElement.style.setProperty('--base-font-size', size + 'px')
      if (el.scrollHeight > target + 1) {
        size -= 0.15
        document.documentElement.style.setProperty('--base-font-size', size + 'px')
        break
      }
    }
    // Publish the auto-fitted size so renderResume re-injects the right dot count.
    effectiveFontSize.value = size

    // Phase 3: binary search for the largest line-height that doesn't overflow
    // Use scrollHeight vs clientHeight as the only overflow check (position-independent)
    if (el.scrollHeight <= target) {
      let lo = lh
      let hi = Math.min(2.4, lh * 1.5) // generous upper bound
      // Verify hi actually overflows; if not, just use it
      document.documentElement.style.setProperty('--line-height', String(hi))
      if (el.scrollHeight <= target) {
        // Even max doesn't overflow — keep it
      } else {
        // Binary search between lo and hi
        safety = 50
        while (hi - lo > 0.0005 && safety--) {
          const mid = +((lo + hi) / 2).toFixed(4)
          document.documentElement.style.setProperty('--line-height', String(mid))
          if (el.scrollHeight > target) {
            hi = mid
          } else {
            lo = mid
          }
        }
        document.documentElement.style.setProperty('--line-height', String(lo))
      }
    }
  })
}

function applyMultiPageStyles() {
  showWarn.value = false
  // Reset to standard sizing — multi-page should never condense
  const stdSize = settings.value.fontSize || 11
  const stdLh = settings.value.lineSpacing || 1.4
  document.documentElement.style.setProperty('--base-font-size', stdSize + 'px')
  document.documentElement.style.setProperty('--line-height', String(stdLh))
  effectiveFontSize.value = stdSize
}

/** Force standard sizing before print when in multi-page mode. */
function ensureMultiPageSizingForPrint() {
  if (props.pageMode === 'multi') {
    applyMultiPageStyles()
  }
}

defineExpose({ ensureMultiPageSizingForPrint })

</script>

<template>
  <div :class="['preview-container', { 'multi-page': pageMode === 'multi' }]">
    <section v-show="!rawMode" :class="['sheet', { 'sheet-multi': pageMode === 'multi' }]">
      <div ref="contentRef" class="sheet-content" v-html="renderedHtml" />
      <div class="warn" v-show="showWarn && pageMode === 'single'">Content exceeds one page at minimum size.</div>
    </section>
    <textarea
      v-show="rawMode"
      class="raw-editor"
      :value="markdown"
      @input="emit('update:markdown', ($event.target as HTMLTextAreaElement).value)"
      spellcheck="false"
    />
  </div>
</template>

<style scoped>
.raw-editor {
  width: var(--page-w); min-height: var(--page-h);
  font-family: ui-monospace, 'SF Mono', Monaco, 'Cascadia Code', monospace;
  font-size: 0.8rem; line-height: 1.5;
  padding: 12px; border: 1px solid #d0d0d0; border-radius: 8px;
  resize: vertical; background: #fafafa; color: #111;
  white-space: pre-wrap; word-wrap: break-word;
}
.raw-editor:focus { outline: none; border-color: #667eea; }
.preview-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.sheet-multi {
  height: auto !important;
  min-height: var(--page-h);
}
</style>
