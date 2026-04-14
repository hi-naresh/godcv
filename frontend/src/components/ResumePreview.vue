<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue'
import { useMarkdown } from '../composables/useMarkdown'

const props = defineProps<{
  markdown: string
  pageMode: 'single' | 'multi'
}>()

const { renderResume, getResumeSettings } = useMarkdown()
const contentRef = ref<HTMLElement>()
const showWarn = ref(false)

const settings = computed(() => getResumeSettings(props.markdown))

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
      <div ref="contentRef" class="sheet-content" v-html="renderResume(markdown)" />
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
