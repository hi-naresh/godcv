<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  modelValue: string[]
  placeholder?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string[]]
}>()

const inputText = ref('')

function addChip() {
  const val = inputText.value.trim().replace(/,+$/, '').trim()
  if (!val) return
  if (props.modelValue.some(s => s.toLowerCase() === val.toLowerCase())) {
    inputText.value = ''
    return
  }
  emit('update:modelValue', [...props.modelValue, val])
  inputText.value = ''
}

function removeChip(index: number) {
  const updated = props.modelValue.filter((_, i) => i !== index)
  emit('update:modelValue', updated)
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' || e.key === ',') {
    e.preventDefault()
    addChip()
  } else if (e.key === 'Backspace' && inputText.value === '' && props.modelValue.length > 0) {
    removeChip(props.modelValue.length - 1)
  }
}
</script>

<template>
  <div class="chip-input-wrap">
    <span v-for="(chip, i) in modelValue" :key="chip + i" class="chip">
      {{ chip }}
      <button class="chip-remove" @click="removeChip(i)" type="button">&times;</button>
    </span>
    <input
      v-model="inputText"
      class="chip-text-input"
      :placeholder="modelValue.length === 0 ? (placeholder || 'Type and press Enter') : ''"
      @keydown="onKeydown"
      @blur="addChip"
    />
  </div>
</template>

<style scoped>
.chip-input-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 4px 6px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  background: #fff;
  cursor: text;
  min-height: 32px;
  align-items: center;
}
.chip-input-wrap:focus-within {
  border-color: #667eea;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 2px 8px;
  background: #f0f0f0;
  border-radius: 12px;
  font-size: 0.78rem;
  line-height: 1.4;
  white-space: nowrap;
}
.chip-remove {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 0.85rem;
  color: #999;
  padding: 0 2px;
  line-height: 1;
}
.chip-remove:hover {
  color: #d00;
}
.chip-text-input {
  border: none;
  outline: none;
  flex: 1;
  min-width: 80px;
  font-size: 0.8rem;
  padding: 2px 4px;
  background: transparent;
}
</style>
