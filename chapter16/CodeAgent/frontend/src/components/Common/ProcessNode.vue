<template>
  <div class="process-node" :class="{ 'external-execution': type === 'external', 'terminal': type === 'terminal' }">
    <div v-if="type === 'external'" class="external-execution-node">
      <div class="loading-animation">
        <div class="spinner"></div>
      </div>
      <div class="execution-content">
        <h3 class="node-title">{{ title }}</h3>
        <p class="execution-description">{{ description }}</p>
        <button class="cancel-btn" @click="handleCancel">
          取消
        </button>
      </div>
    </div>

    <div v-else-if="type === 'terminal'" class="terminal-node">
      <div class="terminal-icon" @click="handleReplay">
        <span class="replay-icon">↻</span>
      </div>
      <div class="terminal-content">
        <h3 class="terminal-title">任务已完成！</h3>
        <p class="terminal-description">是否重新进入当前调试流程？</p>
        <div class="terminal-actions">
          <button class="restart-btn" @click="handleRestart">
            重新开始
          </button>
          <button class="home-btn" @click="handleBackToHome">
            返回首页
          </button>
        </div>
      </div>
    </div>

    <div v-else class="standard-node">
      <div class="node-header">
        <div class="node-title-section">
          <span class="node-index">{{ index }}</span>
          <h2 class="node-title">{{ title }}</h2>
        </div>
        <p class="node-description">{{ description }}</p>
      </div>

      <div class="node-content">
        <slot name="content"></slot>
      </div>

      <div class="node-actions">
        <slot name="actions"></slot>
      </div>

      <div v-if="feedbackMessage" class="feedback-area" :class="feedbackType">
        {{ feedbackMessage }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// 通用流程节点组件 - 支持标准节点、外部执行节点和终端节点
import { ref } from 'vue'

interface Props {
  type?: 'standard' | 'external' | 'terminal'
  index?: string
  title?: string
  description?: string
  feedbackMessage?: string
  feedbackType?: 'success' | 'warning' | 'error'
}

withDefaults(defineProps<Props>(), {
  type: 'standard',
  index: '1',
  title: '节点标题',
  description: '节点描述',
  feedbackType: 'success'
})

const emit = defineEmits<{
  cancel: []
  replay: []
  restart: []
  backToHome: []
}>()

const handleCancel = () => {
  emit('cancel')
}

const handleReplay = () => {
  emit('replay')
}

const handleRestart = () => {
  emit('restart')
}

const handleBackToHome = () => {
  emit('backToHome')
}
</script>

<style scoped>
.process-node {
  padding: 20px;
}

.standard-node {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.node-header {
  border-bottom: 1px solid #374151;
  padding-bottom: 16px;
}

.node-title-section {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.node-index {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3b82f6, #10b981);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: bold;
  font-size: 14px;
}

.node-title {
  font-size: 18px;
  color: #f3f4f6;
  margin: 0;
}

.node-description {
  font-size: 14px;
  color: #9ca3af;
  margin: 0;
}

.node-content {
  flex: 1;
}

.node-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.feedback-area {
  padding: 12px 16px;
  border-radius: 6px;
  color: white;
  font-size: 14px;
  text-align: center;
  animation: fadeIn 0.3s ease-in;
}

.feedback-area.success {
  background: #10b981;
}

.feedback-area.warning {
  background: #f59e0b;
}

.feedback-area.error {
  background: #ef4444;
}

/* 外部执行节点样式 */
.external-execution-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  background: #1f2937;
  border: 1px solid #374151;
  border-radius: 8px;
  padding: 40px;
}

.loading-animation {
  margin-bottom: 20px;
}

.spinner {
  width: 60px;
  height: 60px;
  border: 4px solid #374151;
  border-top: 4px solid #3b82f6;
  border-right: 4px solid #10b981;
  border-radius: 50%;
  animation: spin 1.5s linear infinite;
}

.execution-content {
  text-align: center;
}

.node-title {
  font-size: 18px;
  color: #f3f4f6;
  margin-bottom: 8px;
}

.execution-description {
  font-size: 14px;
  color: #9ca3af;
  margin-bottom: 16px;
}

.cancel-btn {
  background: transparent;
  border: none;
  color: #ef4444;
  cursor: pointer;
  padding: 8px 16px;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.cancel-btn:hover {
  background: #374151;
}

/* 终端节点样式 */
.terminal-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  background: #1f2937;
  border: 1px solid #374151;
  border-radius: 8px;
  padding: 40px;
  text-align: center;
}

.terminal-icon {
  margin-bottom: 20px;
  cursor: pointer;
  transition: transform 0.5s ease;
}

.terminal-icon:hover {
  transform: rotate(180deg);
}

.replay-icon {
  font-size: 60px;
  color: #3b82f6;
}

.terminal-title {
  font-size: 18px;
  color: #f3f4f6;
  font-weight: bold;
  margin-bottom: 8px;
}

.terminal-description {
  font-size: 14px;
  color: #9ca3af;
  margin-bottom: 20px;
}

.terminal-actions {
  display: flex;
  gap: 16px;
}

.restart-btn {
  padding: 10px 24px;
  background: #3b82f6;
  border: none;
  border-radius: 4px;
  color: white;
  cursor: pointer;
  transition: background-color 0.2s;
}

.restart-btn:hover {
  background: #2563eb;
}

.home-btn {
  padding: 10px 24px;
  background: #6b7280;
  border: none;
  border-radius: 4px;
  color: white;
  cursor: pointer;
  transition: background-color 0.2s;
}

.home-btn:hover {
  background: #4b5563;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>