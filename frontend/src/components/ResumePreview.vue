<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue'
import { useMarkdown } from '../composables/useMarkdown'

const props = defineProps<{
  markdown: string
  pageMode: 'single' | 'multi'
  agentStatuses?: Record<string, 'pending' | 'running' | 'done'>
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

const renderedHtml = computed(() => {
  let html = renderResume(props.markdown)
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
