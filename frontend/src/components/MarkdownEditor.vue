<script setup lang="ts">
const props = defineProps<{ modelValue: string }>()
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
  <textarea
    class="md-editor"
    :value="modelValue"
    @input="onInput"
    @drop.prevent="onDrop"
    @dragover.prevent
    placeholder="Paste or type Markdown here... (drag & drop .md files supported)"
  />
</template>

<style scoped>
.md-editor {
  width: 100%; min-height: 300px; resize: vertical;
  font: 13px/1.4 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  border: 1px dashed #b9b9b9; border-radius: 10px; padding: 10px; outline: none;
}
.md-editor:focus { border-color: #6a6a6a; }
</style>
