<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { useMarkdown } from '../composables/useMarkdown'

const props = defineProps<{ markdown: string }>()
const { renderResume } = useMarkdown()
const contentRef = ref<HTMLElement>()
const showWarn = ref(false)

watch(() => props.markdown, async () => {
  await nextTick()
  fitToOnePage()
}, { immediate: true })

function fitToOnePage() {
  const el = contentRef.value
  if (!el) return
  showWarn.value = false
  let size = 11
  const min = 8

  document.documentElement.style.setProperty('--base-font-size', size + 'px')
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
</script>

<template>
  <section class="sheet">
    <div ref="contentRef" class="sheet-content" v-html="renderResume(markdown)" />
    <div class="warn" v-show="showWarn">Content exceeds one page at minimum size.</div>
  </section>
</template>
