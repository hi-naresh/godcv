<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{ modelValue: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const open = ref(false)

function save() {
  open.value = false
}
</script>

<template>
  <div class="api-key-wrapper">
    <button class="api-key-btn" @click="open = !open" title="API Key">
      <span class="key-icon">&#128273;</span>
      <span v-if="modelValue" class="key-dot"></span>
    </button>
    <div v-if="open" class="api-key-popover">
      <label class="popover-label">Gemini API Key</label>
      <input
        type="password"
        class="api-key-input"
        :value="modelValue"
        @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
        placeholder="Paste your Gemini API key"
      />
      <button class="save-btn" @click="save">Done</button>
    </div>
    <div v-if="open" class="popover-backdrop" @click="open = false" />
  </div>
</template>

<style scoped>
.api-key-wrapper { position: relative; }
.api-key-btn {
  position: relative; border: none; background: #333; color: #fff;
  border-radius: 8px; padding: 6px 10px; cursor: pointer; font-size: 0.85rem;
}
.api-key-btn:hover { background: #555; }
.key-icon { font-style: normal; }
.key-dot {
  position: absolute; top: 4px; right: 4px;
  width: 6px; height: 6px; border-radius: 50%; background: #28a745;
}
.api-key-popover {
  position: absolute; right: 0; top: 100%; margin-top: 8px;
  background: #fff; border: 1px solid #d0d0d0; border-radius: 10px;
  padding: 12px; width: 280px; box-shadow: 0 8px 24px rgba(0,0,0,.15);
  z-index: 100; display: flex; flex-direction: column; gap: 8px;
}
.popover-label { font-size: 0.8rem; font-weight: 600; color: #555; }
.api-key-input {
  width: 100%; padding: 8px; border: 1px solid #d0d0d0;
  border-radius: 6px; font-size: 0.85rem;
}
.save-btn {
  align-self: flex-end; padding: 6px 16px; border: none;
  background: #111; color: #fff; border-radius: 6px; font-weight: 600;
  cursor: pointer; font-size: 0.8rem;
}
.popover-backdrop {
  position: fixed; inset: 0; z-index: 99;
}
</style>
