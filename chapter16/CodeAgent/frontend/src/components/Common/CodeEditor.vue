<template>
  <div class="code-editor-container">
    <div class="editor-header">
      <span class="language-badge">{{ language }}</span>
      <div class="editor-actions">
        <button class="action-btn" @click="handleCopy" title="复制代码">
          📋
        </button>
        <button class="action-btn" @click="handleFormat" title="格式化代码">
          🛠️
        </button>
      </div>
    </div>
    <textarea
      v-if="!usePrismEditor"
      ref="textareaRef"
      v-model="localValue"
      :class="['code-textarea', { readonly }]"
      :readonly="readonly"
      :placeholder="placeholder"
      :style="{ height }"
      @input="handleInput"
    ></textarea>
    <div v-else class="prism-editor-placeholder">
      <!-- Prism编辑器占位 - 实际项目中需要集成vue-prism-editor -->
      <pre><code :class="`language-${language}`">{{ localValue }}</code></pre>
    </div>
  </div>
</template>

<script setup lang="ts">
// 通用代码编辑器组件 - 支持语法高亮、复制、格式化等功能
import { ref, watch, computed } from 'vue'

interface Props {
  modelValue: string
  language?: string
  height?: string
  readonly?: boolean
  placeholder?: string
}

const props = withDefaults(defineProps<Props>(), {
  language: 'text',
  height: '200px',
  readonly: false,
  placeholder: '请输入代码...'
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const textareaRef = ref<HTMLTextAreaElement>()
const localValue = ref(props.modelValue)

const usePrismEditor = computed(() => {
  // 在实际项目中，可以根据需要启用Prism编辑器
  return false
})

watch(() => props.modelValue, (newValue) => {
  localValue.value = newValue
})

const handleInput = () => {
  emit('update:modelValue', localValue.value)
}

const handleCopy = async () => {
  try {
    await navigator.clipboard.writeText(localValue.value)
    // 显示复制成功反馈
    console.log('代码已复制到剪贴板')
  } catch (err) {
    console.error('复制失败:', err)
  }
}

const handleFormat = () => {
  // 代码格式化逻辑
  console.log('格式化代码')
  // 在实际项目中，这里可以集成Prettier等格式化工具
}
</script>

<style scoped>
.code-editor-container {
  border: 1px solid #4b5563;
  border-radius: 4px;
  background: #2d3748;
  overflow: hidden;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #374151;
  border-bottom: 1px solid #4b5563;
}

.language-badge {
  font-size: 12px;
  color: #9ca3af;
  background: #1f2937;
  padding: 2px 8px;
  border-radius: 4px;
}

.editor-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  background: transparent;
  border: none;
  color: #d1d5db;
  cursor: pointer;
  padding: 4px;
  border-radius: 2px;
  transition: background-color 0.2s;
}

.action-btn:hover {
  background: #4b5563;
}

.code-textarea {
  width: 100%;
  background: #2d3748;
  border: none;
  padding: 16px;
  color: #f3f4f6;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 14px;
  line-height: 1.5;
  resize: vertical;
  outline: none;
}

.code-textarea.readonly {
  background: #374151;
  color: #9ca3af;
}

.prism-editor-placeholder {
  padding: 16px;
  background: #1e1e1e;
  color: #d4d4d4;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 14px;
  line-height: 1.5;
  overflow-x: auto;
}
</style>