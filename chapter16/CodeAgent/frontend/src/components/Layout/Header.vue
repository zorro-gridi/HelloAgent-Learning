<template>
  <header class="header">
    <div class="header-left">
      <div class="logo">
        <span class="logo-text">GRIDi BugKiller</span>
      </div>
      <div class="task-type-switcher">
        <button
          v-for="type in taskTypes"
          :key="type.value"
          :class="['type-tab', { active: currentTaskType === type.value }]"
          @click="switchTaskType(type.value)"
        >
          {{ type.label }}
        </button>
      </div>
    </div>
    <div class="header-right">
      <button class="icon-button" title="帮助文档">
        <span>?</span>
      </button>
      <button class="icon-button" title="设置">
        <span>⚙️</span>
      </button>
      <button class="icon-button" title="用户中心">
        <span>👤</span>
      </button>
      <button class="reset-button" @click="handleReset">
        <span>🔄</span>
        <span>重置当前任务</span>
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
// 顶部导航栏组件 - 包含Logo、任务类型切换和功能按钮
import { ref } from 'vue'
import type { TaskType } from '../../types'

const taskTypes = [
  { label: '代码调试', value: 'debug' },
  { label: '代码优化', value: 'optimize' },
  { label: '代码审查', value: 'review' },
  { label: '代码校对', value: 'proofread' }
] as const

const currentTaskType = ref<TaskType>('debug')

const switchTaskType = (type: TaskType) => {
  currentTaskType.value = type
}

const handleReset = () => {
  if (confirm('确定重置所有节点状态？')) {
    // 重置逻辑
    console.log('重置任务')
  }
}
</script>

<style scoped>
.header {
  height: 60px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  background-color: #1f2937;
  border-bottom: 1px solid #374151;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 40px;
}

.logo-text {
  font-size: 20px;
  font-weight: 600;
  color: #f3f4f6;
}

.task-type-switcher {
  display: flex;
  gap: 0;
}

.type-tab {
  padding: 8px 16px;
  background: transparent;
  border: none;
  color: #9ca3af;
  cursor: pointer;
  transition: color 0.3s;
}

.type-tab.active {
  color: #3b82f6;
  border-bottom: 2px solid #3b82f6;
}

.type-tab:hover {
  color: #3b82f6;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.icon-button {
  width: 40px;
  height: 40px;
  border: none;
  background: transparent;
  color: #d1d5db;
  cursor: pointer;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s;
}

.icon-button:hover {
  background-color: #374151;
  color: #3b82f6;
}

.reset-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: transparent;
  border: 1px dashed #6b7280;
  color: #6b7280;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.reset-button:hover {
  border-color: #3b82f6;
  color: #3b82f6;
}
</style>