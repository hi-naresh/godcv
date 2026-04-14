<script setup lang="ts">
import { onMounted } from 'vue'
import { useEditorStore } from '../stores/editor'
import { useProfile } from '../composables/useProfile'
import MarkdownEditor from '../components/MarkdownEditor.vue'
import ResumePreview from '../components/ResumePreview.vue'
import JobInput from '../components/JobInput.vue'
import AgentProgress from '../components/AgentProgress.vue'

const store = useEditorStore()
const { fetchProfile } = useProfile()

onMounted(async () => {
  const p = await fetchProfile()
  if (p) {
    store.profile = p
    if (!store.markdown) store.markdown = p.master_resume
  }
})

function exportPdf() { window.print() }
</script>

<template>
  <div class="editor-layout">
    <aside class="sidebar">
      <h2>GodCV Editor</h2>
      <small>Paste or drag your .md resume. AI tailors it section-by-section.</small>
      <MarkdownEditor v-model="store.markdown" />
      <div class="controls">
        <button @click="exportPdf">Print / PDF</button>
      </div>
      <JobInput />
      <AgentProgress />
    </aside>
    <ResumePreview :markdown="store.markdown" />
  </div>
</template>

<style scoped>
.editor-layout {
  display: flex; align-items: flex-start; justify-content: center;
  gap: 18px; padding: 0 18px;
}
.sidebar {
  width: min(440px, 32vw); min-width: 300px;
  position: sticky; top: 60px; align-self: flex-start;
  background: #fff; border: 1px solid #d9d9d9; border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0,0,0,.08); padding: 14px;
  display: flex; flex-direction: column; gap: 10px;
}
h2 { margin: 0; font-size: 1.05rem; }
.controls { display: flex; flex-wrap: wrap; gap: 8px; }
.controls button {
  appearance: none; border: 1px solid #c9c9c9; background: #fafafa;
  border-radius: 10px; padding: 8px 12px; cursor: pointer; font-weight: 600;
}
</style>
