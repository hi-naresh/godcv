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
  // Extract text from <li> elements
  const liRegex = /<li>([\s\S]*?)<\/li>/gi
  let m
  while ((m = liRegex.exec(html)) !== null) {
    const text = m[1].replace(/<[^>]+>/g, '').trim()
    if (text) lines.add(text)
  }
  // Extract text from <p> elements (summary, skills lines)
  const pRegex = /<p>([\s\S]*?)<\/p>/gi
  while ((m = pRegex.exec(html)) !== null) {
    const text = m[1].replace(/<[^>]+>/g, '').trim()
    if (text.length > 20) lines.add(text) // skip tiny fragments
  }
  return lines
}

function highlightChanges(tailoredHtml: string, originalHtml: string): string {
  const originalLines = extractTextLines(originalHtml)

  // Highlight <li> elements whose text differs from original
  let html = tailoredHtml.replace(/<li>([\s\S]*?)<\/li>/gi, (match, inner) => {
    const text = inner.replace(/<[^>]+>/g, '').trim()
    if (!text || originalLines.has(text)) return match
    // Check if it's already a suggestion (don't double-highlight)
    if (match.includes('class="suggestion') || match.includes('class="sug')) return match
    return `<li class="changed-content">${inner}</li>`
  })

  // Highlight <p> elements in summary/skills that changed
  html = html.replace(/<p>([\s\S]*?)<\/p>/gi, (match, inner) => {
    const text = inner.replace(/<[^>]+>/g, '').trim()
    if (!text || text.length <= 20 || originalLines.has(text)) return match
    if (match.includes('class="suggestion') || match.includes('class="sug')) return match
    // Don't highlight header meta (name, title, links)
    if (match.includes('class="meta"') || match.includes('class="name"') || match.includes('class="role"')) return match
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
