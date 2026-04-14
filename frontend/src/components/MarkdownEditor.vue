<script setup lang="ts">
const props = withDefaults(defineProps<{
  modelValue: string
  label?: string
}>(), {
  label: 'Your Master Resume',
})
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

function onInput(e: Event) {
  emit('update:modelValue', (e.target as HTMLTextAreaElement).value)
}

function onDrop(e: DragEvent) {
  e.preventDefault()
  const file = e.dataTransfer?.files[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => emit('update:modelValue', reader.result as string)
  reader.readAsText(file)
}
</script>

<template>
  <div class="editor-wrapper">
    <label class="editor-label">{{ label }}</label>
    <textarea
      class="md-editor"
      :value="modelValue"
      @input="onInput"
      @drop.prevent="onDrop"
      @dragover.prevent
      placeholder="Paste your markdown resume here or drag & drop a .md file..."
    />
  </div>
</template>

<style scoped>
.editor-wrapper { display: flex; flex-direction: column; gap: 4px; }
.editor-label { font-size: 0.8rem; font-weight: 700; color: #555; }
.md-editor {
  width: 100%; min-height: 220px; resize: vertical;
  font: 12px/1.4 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  border: 1px dashed #b9b9b9; border-radius: 10px; padding: 10px; outline: none;
}
.md-editor:focus { border-color: #667eea; }
</style>
