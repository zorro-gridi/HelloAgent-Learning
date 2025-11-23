<template>
  <div class="code-debug">
    <div class="node-section">
      <div class="node-header">
        <h2>节点1 - 提取异常堆栈信息</h2>
        <p class="node-description">复制并粘贴异常堆栈信息进行分析</p>
      </div>
      <div class="node-content">
        <div class="action-section">
          <button class="reproduce-btn" @click="handleReproduce">
            🔍 复现
          </button>
          <div v-if="stackTrace" class="stack-trace-section">
            <CodeEditor
              v-model="stackTrace"
              :readonly="true"
              language="text"
              height="160px"
            />
            <button class="copy-btn" @click="handleCopyStackTrace">
              📋 复制
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="node-section">
      <div class="node-header">
        <h2>节点6 - 获取分析结果</h2>
      </div>
      <div class="dual-column-layout">
        <div class="column">
          <label>异常依赖对象列表</label>
          <CodeEditor
            v-model="dependencyList"
            language="text"
            height="180px"
            placeholder="输入异常依赖对象列表..."
          />
          <button class="generate-btn" @click="handleGenerateDependencies">
            🚀 生成
          </button>
        </div>
        <div class="column">
          <label>异常根因分析结果</label>
          <CodeEditor
            v-model="rootCauseAnalysis"
            language="text"
            height="180px"
            placeholder="查看异常根因分析结果..."
          />
          <button class="submit-btn" @click="handleSubmitAnalysis">
            ✅ 提交
          </button>
        </div>
      </div>
    </div>

    <div class="node-section">
      <div class="node-header">
        <h2>节点7 - 生成Bug Solver Context</h2>
      </div>
      <div class="node-content">
        <div class="form-section">
          <label>用户异常补充描述</label>
          <textarea
            v-model="userDescription"
            class="text-area"
            placeholder="补充描述异常情况..."
            rows="4"
          ></textarea>
        </div>
        <button class="generate-context-btn" @click="handleGenerateContext">
          🚀 上下文生成
        </button>
        <div v-if="generatedContext" class="context-section">
          <CodeEditor
            v-model="generatedContext"
            :readonly="true"
            language="text"
            height="160px"
          />
          <button class="copy-context-btn" @click="handleCopyContext">
            📋 上下文复制
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// 代码调试任务类型组件 - 实现代码调试相关的所有节点功能
import { ref } from 'vue'
import CodeEditor from '../Common/CodeEditor.vue'

const stackTrace = ref('')
const dependencyList = ref('')
const rootCauseAnalysis = ref('')
const userDescription = ref('')
const generatedContext = ref('')

const handleReproduce = () => {
  // 模拟生成堆栈信息
  stackTrace.value = `Exception in thread "main" java.lang.NullPointerException
    at com.example.MyClass.myMethod(MyClass.java:25)
    at com.example.Main.main(Main.java:10)`
}

const handleCopyStackTrace = () => {
  navigator.clipboard.writeText(stackTrace.value)
  // 显示成功反馈
}

const handleGenerateDependencies = () => {
  // 生成依赖对象逻辑
  console.log('生成依赖对象')
}

const handleSubmitAnalysis = () => {
  // 提交分析结果逻辑
  console.log('提交分析结果')
}

const handleGenerateContext = () => {
  // 生成上下文逻辑
  generatedContext.value = `Bug Solver Context:
  Stack Trace: ${stackTrace.value}
  User Description: ${userDescription.value}
  Generated at: ${new Date().toISOString()}`
}

const handleCopyContext = () => {
  navigator.clipboard.writeText(generatedContext.value)
  // 显示成功反馈
}
</script>

<style scoped>
.code-debug {
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

.node-description {
  font-size: 14px;
  color: #9ca3af;
}

.action-section {
  text-align: center;
  padding: 20px 0;
}

.reproduce-btn {
  padding: 16px 32px;
  font-size: 16px;
  background: linear-gradient(135deg, #3b82f6, #10b981);
  border: none;
  border-radius: 8px;
  color: white;
  cursor: pointer;
  transition: transform 0.2s;
}

.reproduce-btn:hover {
  transform: scale(1.05);
}

.stack-trace-section {
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

.dual-column-layout {
  display: flex;
  gap: 20px;
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

.generate-btn,
.submit-btn,
.generate-context-btn {
  align-self: flex-start;
  padding: 10px 20px;
  background: #3b82f6;
  border: none;
  border-radius: 4px;
  color: white;
  cursor: pointer;
  transition: background-color 0.2s;
}

.generate-context-btn {
  margin-top: 16px;
}

.form-section {
  margin-bottom: 16px;
}

.text-area {
  width: 100%;
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

.context-section {
  margin-top: 20px;
  position: relative;
}

.copy-context-btn {
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