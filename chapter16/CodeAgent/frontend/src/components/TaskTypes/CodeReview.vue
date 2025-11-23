<template>
  <div class="code-review">
    <div class="node-section">
      <div class="node-header">
        <h2>节点1 - 生成待审查代码上下文</h2>
      </div>
      <div class="dual-column-layout">
        <div class="column">
          <label>目标对象列表</label>
          <CodeEditor
            v-model="targetObjects"
            language="text"
            height="100px"
            placeholder="输入需要审查的目标对象列表..."
          />
        </div>
        <div class="column">
          <button class="generate-context-btn" @click="handleGenerateContext">
            🚀 上下文生成
          </button>
        </div>
      </div>
      <div v-if="generatedContext" class="context-result">
        <CodeEditor
          v-model="generatedContext"
          :readonly="true"
          language="text"
          height="120px"
        />
        <button class="copy-btn" @click="handleCopyContext">
          📋 复制
        </button>
      </div>
    </div>

    <div class="node-section">
      <div class="node-header">
        <h2>节点2 - 重构需求信息收集</h2>
      </div>
      <div class="form-layout">
        <div class="form-row">
          <label>需求描述</label>
          <textarea
            v-model="requirementDescription"
            class="text-area"
            placeholder="详细描述代码审查需求..."
            rows="3"
          ></textarea>
        </div>
        <div class="form-row">
          <label>关键业务规则</label>
          <textarea
            v-model="businessRules"
            class="text-area"
            placeholder="输入关键业务规则和约束条件..."
            rows="2"
          ></textarea>
        </div>
        <div class="form-row">
          <label>待审查代码上下文</label>
          <CodeEditor
            v-model="codeContext"
            language="javascript"
            height="300px"
            placeholder="粘贴待审查的代码，支持多种编程语言..."
          />
        </div>
      </div>
    </div>

    <div class="node-section">
      <div class="node-header">
        <h2>节点6 - 重新生成上下文</h2>
      </div>
      <div class="node-content">
        <button class="regenerate-context-btn" @click="handleRegenerateContext">
          🔄 重新生成上下文
        </button>
        <div v-if="regeneratedContext" class="context-result">
          <CodeEditor
            v-model="regeneratedContext"
            :readonly="true"
            language="text"
            height="160px"
          />
          <button class="copy-btn" @click="handleCopyRegeneratedContext">
            📋 复制
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// 代码审查任务类型组件 - 实现代码审查相关的节点功能
import { ref } from 'vue'
import CodeEditor from '../Common/CodeEditor.vue'

const targetObjects = ref('')
const generatedContext = ref('')
const requirementDescription = ref('')
const businessRules = ref('')
const codeContext = ref('')
const regeneratedContext = ref('')

const handleGenerateContext = () => {
  // 生成上下文逻辑
  generatedContext.value = `代码审查上下文:
  目标对象: ${targetObjects.value}
  生成时间: ${new Date().toISOString()}

  审查范围包括:
  - 代码规范检查
  - 潜在bug检测
  - 性能优化建议
  - 安全漏洞扫描`
}

const handleCopyContext = () => {
  navigator.clipboard.writeText(generatedContext.value)
  // 显示成功反馈
}

const handleRegenerateContext = () => {
  // 重新生成上下文逻辑
  regeneratedContext.value = `重新生成的审查上下文:
  需求: ${requirementDescription.value}
  业务规则: ${businessRules.value}
  代码摘要: ${codeContext.value.substring(0, 50)}...

  包含:
  - 更新后的代码结构分析
  - 重构建议
  - 最佳实践推荐`
}

const handleCopyRegeneratedContext = () => {
  navigator.clipboard.writeText(regeneratedContext.value)
  // 显示成功反馈
}
</script>

<style scoped>
.code-review {
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

.dual-column-layout {
  display: flex;
  gap: 20px;
  align-items: flex-end;
  margin-bottom: 20px;
}

.column {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.column label {
  font-size: 14px;
  color: #d1d5db;
}

.generate-context-btn {
  padding: 10px 20px;
  background: #3b82f6;
  border: none;
  border-radius: 4px;
  color: white;
  cursor: pointer;
  transition: background-color 0.2s;
  align-self: flex-start;
}

.generate-context-btn:hover {
  background: #2563eb;
}

.context-result {
  position: relative;
  margin-top: 16px;
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

.copy-btn:hover {
  background: #4b5563;
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

.regenerate-context-btn {
  padding: 10px 20px;
  background: #f59e0b;
  border: none;
  border-radius: 4px;
  color: white;
  cursor: pointer;
  transition: background-color 0.2s;
}

.regenerate-context-btn:hover {
  background: #d97706;
}
</style>