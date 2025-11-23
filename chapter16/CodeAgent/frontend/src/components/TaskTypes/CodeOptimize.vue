<template>
  <div class="code-optimize">
    <div class="node-section">
      <div class="node-header">
        <h2>节点1 - 优化需求信息收集</h2>
      </div>
      <div class="form-layout">
        <div class="form-row">
          <label>需求类型</label>
          <input v-model="requirementType" class="input-field" placeholder="选择或输入需求类型...">
        </div>
        <div class="form-row">
          <label>需求描述</label>
          <textarea v-model="requirementDescription" class="text-area" placeholder="详细描述优化需求..." rows="3"></textarea>
        </div>
        <div class="form-row">
          <label>约束条件</label>
          <textarea v-model="constraints" class="text-area" placeholder="输入优化约束条件..." rows="2"></textarea>
        </div>
        <div class="form-row">
          <label>待优化的代码上下文</label>
          <CodeEditor
            v-model="codeContext"
            language="python"
            height="300px"
            placeholder="粘贴待优化的Python代码，支持markdown格式..."
          />
        </div>
      </div>
    </div>

    <div class="node-section">
      <div class="node-header">
        <h2>节点2 - 生成上下文</h2>
      </div>
      <div class="node-content">
        <button class="generate-context-btn" @click="handleGenerateContext">
          🚀 上下文生成
        </button>
        <div v-if="generatedContext" class="context-result">
          <CodeEditor
            v-model="generatedContext"
            :readonly="true"
            language="text"
            height="200px"
          />
          <button class="copy-btn" @click="handleCopyContext">
            📋 复制
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// 代码优化任务类型组件 - 实现代码优化相关的节点功能
import { ref } from 'vue'
import CodeEditor from '../Common/CodeEditor.vue'

const requirementType = ref('')
const requirementDescription = ref('')
const constraints = ref('')
const codeContext = ref('')
const generatedContext = ref('')

const handleGenerateContext = () => {
  // 生成上下文逻辑
  generatedContext.value = `优化上下文:
  类型: ${requirementType.value}
  描述: ${requirementDescription.value}
  约束: ${constraints.value}
  代码: ${codeContext.value.substring(0, 100)}...`
}

const handleCopyContext = () => {
  navigator.clipboard.writeText(generatedContext.value)
  // 显示成功反馈
}
</script>

<style scoped>
.code-optimize {
  padding: 20px;
}

.node-section {
  margin-bottom: 40px;
  background-color: #1f2937;
  border-radius: 8px;
  padding: 20px;
  border: 1px solid #374151;
}

.node-header h2 {
  font-size: 18px;
  color: #f3f4f6;
  margin-bottom: 8px;
}

.form-layout {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-row label {
  font-size: 14px;
  color: #d1d5db;
}

.input-field {
  height: 40px;
  background: #2d3748;
  border: 1px solid #4b5563;
  border-radius: 4px;
  padding: 0 12px;
  color: #f3f4f6;
}

.input-field:focus {
  border-color: #3b82f6;
  outline: none;
}

.text-area {
  background: #2d3748;
  border: 1px solid #4b5563;
  border-radius: 4px;
  padding: 12px;
  color: #f3f4f6;
  font-family: inherit;
  resize: vertical;
}

.text-area:focus {
  border-color: #3b82f6;
  outline: none;
}

.generate-context-btn {
  padding: 10px 20px;
  background: #3b82f6;
  border: none;
  border-radius: 4px;
  color: white;
  cursor: pointer;
  transition: background-color 0.2s;
}

.context-result {
  margin-top: 20px;
  position: relative;
}

.copy-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  background: #374151;
  border: none;
  border-radius: 4px;
  padding: 8px 12px;
  color: #f3f4f6;
  cursor: pointer;
  z-index: 10;
}
</style>