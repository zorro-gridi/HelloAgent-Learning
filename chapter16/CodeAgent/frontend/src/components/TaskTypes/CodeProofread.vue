<template>
  <div class="code-proofread">
    <div class="node-section">
      <div class="node-header">
        <h2>节点1 - 代码校对信息收集</h2>
      </div>
      <div class="dual-column-code-layout">
        <div class="code-column">
          <label>优化前代码</label>
          <CodeEditor
            v-model="beforeOptimizationCode"
            language="javascript"
            height="250px"
            placeholder="粘贴优化前的原始代码..."
          />
        </div>
        <div class="code-column">
          <label>优化后代码</label>
          <CodeEditor
            v-model="afterOptimizationCode"
            language="javascript"
            height="250px"
            placeholder="粘贴优化后的代码..."
          />
        </div>
      </div>
      <div class="business-rules-section">
        <label>校对的业务规则</label>
        <textarea
          v-model="businessRules"
          class="text-area"
          placeholder="输入代码校对需要遵循的业务规则和约束条件..."
          rows="4"
        ></textarea>
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

    <div class="node-section">
      <div class="node-header">
        <h2>校对结果分析</h2>
      </div>
      <div class="analysis-results">
        <div class="analysis-item">
          <h3>功能一致性检查</h3>
          <div class="result-status success">✓ 通过</div>
          <p class="result-desc">优化前后代码功能保持一致</p>
        </div>
        <div class="analysis-item">
          <h3>性能改进验证</h3>
          <div class="result-status warning">⚠️ 部分改进</div>
          <p class="result-desc">时间复杂度从O(n²)优化到O(n log n)</p>
        </div>
        <div class="analysis-item">
          <h3>代码规范检查</h3>
          <div class="result-status error">✗ 未通过</div>
          <p class="result-desc">存在未处理的异常情况</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// 代码校对任务类型组件 - 实现代码校对相关的节点功能
import { ref } from 'vue'
import CodeEditor from '../Common/CodeEditor.vue'

const beforeOptimizationCode = ref('')
const afterOptimizationCode = ref('')
const businessRules = ref('')
const generatedContext = ref('')

const handleGenerateContext = () => {
  // 生成校对上下文逻辑
  generatedContext.value = `代码校对上下文:

  优化前代码摘要:
  ${beforeOptimizationCode.value.substring(0, 100)}...

  优化后代码摘要:
  ${afterOptimizationCode.value.substring(0, 100)}...

  业务规则:
  ${businessRules.value}

  校对重点:
  - 功能等价性验证
  - 性能改进评估
  - 代码质量检查
  - 业务规则符合性`
}

const handleCopyContext = () => {
  navigator.clipboard.writeText(generatedContext.value)
  // 显示成功反馈
}
</script>

<style scoped>
.code-proofread {
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

.dual-column-code-layout {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
}

.code-column {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.code-column label {
  font-size: 14px;
  color: #d1d5db;
}

.business-rules-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.business-rules-section label {
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

.generate-context-btn {
  padding: 10px 20px;
  background: #3b82f6;
  border: none;
  border-radius: 4px;
  color: white;
  cursor: pointer;
  transition: background-color 0.2s;
}

.generate-context-btn:hover {
  background: #2563eb;
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

.copy-btn:hover {
  background: #4b5563;
}

.analysis-results {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.analysis-item {
  background: #2d3748;
  padding: 16px;
  border-radius: 6px;
  border-left: 4px solid #4b5563;
}

.analysis-item h3 {
  font-size: 14px;
  color: #f3f4f6;
  margin-bottom: 8px;
}

.result-status {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: bold;
  margin-bottom: 8px;
}

.result-status.success {
  background: #10b981;
  color: white;
}

.result-status.warning {
  background: #f59e0b;
  color: white;
}

.result-status.error {
  background: #ef4444;
  color: white;
}

.result-desc {
  font-size: 12px;
  color: #9ca3af;
  margin: 0;
}
</style>