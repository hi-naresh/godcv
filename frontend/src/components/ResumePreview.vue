<script setup lang="ts">
import { ref, watch, nextTick, computed, onMounted, onUnmounted } from 'vue'
import { useMarkdown } from '../composables/useMarkdown'
import type { Suggestion } from '../stores/editor'

const props = defineProps<{
  markdown: string
  pageMode: 'single' | 'multi'
  agentStatuses?: Record<string, 'pending' | 'running' | 'done'>
  suggestions?: Suggestion[]
}>()

const emit = defineEmits<{
  'accept-suggestion': [id: string]
  'deny-suggestion': [id: string]
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

function injectSuggestion(html: string, sug: Suggestion): string {
  const escaped = sug.content
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  const tooltip = `<span class="sug-tooltip"><button class="sug-accept" title="Accept">&#10003;</button><button class="sug-deny" title="Deny">&#10005;</button></span>`

  if (sug.section === 'Skills') {
    // For skills: inline span at end of skills text
    const sugHtml = `<span class="suggestion" data-sug-id="${sug.id}" title="${sug.context.replace(/"/g, '&quot;')}">${escaped}${tooltip}</span>`
    const skillsRegex = /(<h1>Skills<\/h1>)([\s\S]*?)(<h1>|<hr|$)/i
    html = html.replace(skillsRegex, (match, h1, content, next) => {
      return h1 + content.replace(/<\/p>(?![\s\S]*<\/p>)/, ', ' + sugHtml + '</p>') + next
    })
  } else if (sug.type === 'project' && sug.section === 'Projects') {
    // For new project entries: append as a highlighted block before the Projects section ends
    const projHtml = `<div class="suggestion suggestion-project" data-sug-id="${sug.id}" title="${sug.context.replace(/"/g, '&quot;')}">${escaped}${tooltip}</div>`
    // Find the end of the Projects section (before next h1 or hr)
    const projRegex = /(<h1>Projects<\/h1>)([\s\S]*?)(<h1>|<hr|$)/i
    html = html.replace(projRegex, (match, h1, content, next) => {
      return h1 + content + projHtml + next
    })
  } else {
    // For bullets: <li> with suggestion class directly
    const sugLi = `<li class="suggestion" data-sug-id="${sug.id}" title="${sug.context.replace(/"/g, '&quot;')}">${escaped}${tooltip}</li>`
    const parts = sug.section.split(':')
    const entryKey = parts[1] || ''
    if (entryKey) {
      const keyEscaped = entryKey.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
      const entryRegex = new RegExp(
        `(<strong>[^<]*${keyEscaped}[^<]*<\\/strong>[\\s\\S]*?<ul>)([\\s\\S]*?)(<\\/ul>)`,
        'i'
      )
      html = html.replace(entryRegex, (match, before, items, close) => {
        return before + items + sugLi + close
      })
    }
  }
  return html
}

const renderedHtml = computed(() => {
  let html = renderResume(props.markdown)
  // Inject refining badges into section h1 headers
  for (const section of refiningSections.value) {
    const regex = new RegExp(`(<h1>)(${section})(</h1>)`, 'i')
    html = html.replace(regex, `$1$2 <span class="refining-badge">refining...</span>$3`)
  }
  // Inject suggestion content as green-highlighted spans
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
  const min = 8
  const lineHeight = settings.value.lineSpacing

  document.documentElement.style.setProperty('--base-font-size', size + 'px')
  document.documentElement.style.setProperty('--line-height', String(lineHeight))

  requestAnimationFrame(() => {
    let safety = 100
    while (el.scrollHeight > el.clientHeight + 1 && size > min && safety--) {
      size = Math.max(min, size - 0.15)
      document.documentElement.style.setProperty('--base-font-size', size + 'px')
    }
    if (el.scrollHeight > el.clientHeight + 1) {
      showWarn.value = true
    }
  })
}

function applyMultiPageStyles() {
  showWarn.value = false
  document.documentElement.style.setProperty('--base-font-size', settings.value.fontSize + 'px')
  document.documentElement.style.setProperty('--line-height', String(settings.value.lineSpacing))
}

function handleSuggestionClick(e: Event) {
  const target = e.target as HTMLElement
  if (target.classList.contains('sug-accept')) {
    const id = target.closest('.suggestion')?.getAttribute('data-sug-id')
    if (id) emit('accept-suggestion', id)
  } else if (target.classList.contains('sug-deny')) {
    const id = target.closest('.suggestion')?.getAttribute('data-sug-id')
    if (id) emit('deny-suggestion', id)
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
    <section :class="['sheet', { 'sheet-multi': pageMode === 'multi' }]">
      <div ref="contentRef" class="sheet-content" v-html="renderedHtml" />
      <div class="warn" v-show="showWarn && pageMode === 'single'">Content exceeds one page at minimum size.</div>
    </section>
  </div>
</template>

<style scoped>
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
