<script setup lang="ts">
import { ref, watch, nextTick, computed, onMounted, onUnmounted } from 'vue'
import { useMarkdown } from '../composables/useMarkdown'
import type { Suggestion } from '../stores/editor'

const props = defineProps<{
  markdown: string
  originalMarkdown?: string
  pageMode: 'single' | 'multi'
  rawMode?: boolean
  agentStatuses?: Record<string, 'pending' | 'running' | 'done'>
  suggestions?: Suggestion[]
}>()

const emit = defineEmits<{
  'accept-suggestion': [id: string]
  'deny-suggestion': [id: string]
  'update:markdown': [value: string]
}>()

const { renderResume, getResumeSettings } = useMarkdown()
const contentRef = ref<HTMLElement>()
const showWarn = ref(false)

const settings = computed(() => getResumeSettings(props.markdown))

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

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function makeTooltip(acceptLabel: string = '&#10003;', denyLabel: string = '&#10005;'): string {
  return `<span class="sug-tooltip"><button class="sug-accept" title="Accept">${acceptLabel}</button><button class="sug-deny" title="Dismiss">${denyLabel}</button></span>`
}

function injectSuggestion(html: string, sug: Suggestion): string {
  const escaped = escapeHtml(sug.content)
  const titleAttr = `title="${escapeHtml(sug.context)}"`

  // --- REMOVE: wrap existing text in red strikethrough ---
  if (sug.type === 'remove') {
    const tooltip = makeTooltip('&#10005;', '&#8630;')  // ✕ to confirm remove, ↶ to keep
    const contentToFind = escapeHtml(sug.content.replace(/^- /, '').trim())
    // Try to find and wrap the exact text in the HTML
    const textRegex = new RegExp(`(<li>)([^<]*${escapeRegex(contentToFind)}[^<]*)(<\\/li>)`, 'i')
    const match = html.match(textRegex)
    if (match) {
      html = html.replace(textRegex, `<li class="suggestion-remove" data-sug-id="${sug.id}" ${titleAttr}>$2${tooltip}</li>`)
    }
    return html
  }

  // --- REPLACE: show old as strikethrough + new as green ---
  if (sug.type === 'replace' && sug.old_content) {
    const tooltip = makeTooltip()
    const oldText = escapeHtml(sug.old_content.replace(/^- /, '').trim())
    const textRegex = new RegExp(`(<li>)([^<]*${escapeRegex(oldText)}[^<]*)(<\\/li>)`, 'i')
    const match = html.match(textRegex)
    if (match) {
      const replacement = `<li class="suggestion-replace" data-sug-id="${sug.id}" ${titleAttr}><span class="sug-old">$2</span> <span class="sug-new">${escaped}</span>${tooltip}</li>`
      html = html.replace(textRegex, replacement)
    }
    return html
  }

  // --- ADD: skill ---
  const tooltip = makeTooltip()
  if (sug.section === 'Skills') {
    const sugHtml = `<span class="suggestion" data-sug-id="${sug.id}" ${titleAttr}>${escaped}${tooltip}</span>`
    const category = sug.skill_category

    if (category) {
      // Target the specific category paragraph containing **Category:**
      const catEscaped = escapeRegex(category)
      const catRegex = new RegExp(
        `(<p><strong>${catEscaped}:<\\/strong>\\s*)(.*?)(<\\/p>)`,
        'i'
      )
      const catMatch = html.match(catRegex)
      if (catMatch) {
        html = html.replace(catRegex, `$1$2, ${sugHtml}$3`)
      }
    }

    // Fallback: append to the last </p> in the Skills section
    if (!category || !html.match(new RegExp(escapeRegex(category), 'i'))) {
      const skillsRegex = /(<h1>Skills<\/h1>)([\s\S]*?)(<h1>|<hr|$)/i
      html = html.replace(skillsRegex, (_match, h1, content, next) => {
        return h1 + content.replace(/<\/p>(?![\s\S]*<\/p>)/, ', ' + sugHtml + '</p>') + next
      })
    }
  } else if (sug.type === 'project' && sug.section === 'Projects') {
    // --- ADD: new project entry ---
    const projHtml = `<div class="suggestion suggestion-project" data-sug-id="${sug.id}" ${titleAttr}>${escaped}${tooltip}</div>`
    const projRegex = /(<h1>Projects<\/h1>)([\s\S]*?)(<h1>|<hr|$)/i
    html = html.replace(projRegex, (_match, h1, content, next) => {
      return h1 + content + projHtml + next
    })
  } else {
    // --- ADD: bullet ---
    const sugLi = `<li class="suggestion" data-sug-id="${sug.id}" ${titleAttr}>${escaped}${tooltip}</li>`
    const parts = sug.section.split(':')
    const entryKey = parts[1] || ''
    if (entryKey) {
      const keyEscaped = escapeRegex(entryKey)
      const entryRegex = new RegExp(
        `(<strong>[^<]*${keyEscaped}[^<]*<\\/strong>[\\s\\S]*?<ul>)([\\s\\S]*?)(<\\/ul>)`,
        'i'
      )
      html = html.replace(entryRegex, (_match, before, items, close) => {
        return before + items + sugLi + close
      })
    }
  }
  return html
}

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
  let html = renderResume(props.markdown)

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
  // Inject suggestion content
  if (props.suggestions?.length) {
    for (const sug of props.suggestions) {
      html = injectSuggestion(html, sug)
    }
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
}

/** Force standard sizing before print when in multi-page mode. */
function ensureMultiPageSizingForPrint() {
  if (props.pageMode === 'multi') {
    applyMultiPageStyles()
  }
}

defineExpose({ ensureMultiPageSizingForPrint })

function handleSuggestionClick(e: Event) {
  const target = e.target as HTMLElement
  const sugEl = target.closest('[data-sug-id]')
  if (!sugEl) return
  const id = sugEl.getAttribute('data-sug-id')
  if (!id) return
  if (target.classList.contains('sug-accept')) {
    emit('accept-suggestion', id)
  } else if (target.classList.contains('sug-deny')) {
    emit('deny-suggestion', id)
  }
}

onMounted(() => {
  contentRef.value?.addEventListener('click', handleSuggestionClick)
})

onUnmounted(() => {
  contentRef.value?.removeEventListener('click', handleSuggestionClick)
})
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
