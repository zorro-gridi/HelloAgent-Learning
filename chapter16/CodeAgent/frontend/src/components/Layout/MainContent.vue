<template>
  <main class="main-content">
    <div class="content-wrapper">
      <div class="left-panel">
        <component :is="currentTaskComponent" />
      </div>
      <div class="right-panel">
        <div class="assistant-panel">
          <h3>辅助功能区</h3>
          <div class="assistant-content">
            <!-- 辅助功能内容 -->
            <p>当前任务类型: {{ currentTaskType }}</p>
          </div>
        </div>
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
// 主内容区组件 - 根据任务类型动态加载对应组件
import { computed } from 'vue'
import { useAppStore } from '../../store'
import CodeDebug from '../TaskTypes/CodeDebug.vue'
import CodeOptimize from '../TaskTypes/CodeOptimize.vue'
import CodeReview from '../TaskTypes/CodeReview.vue'
import CodeProofread from '../TaskTypes/CodeProofread.vue'

const appStore = useAppStore()
const currentTaskType = computed(() => appStore.currentTaskType)

const taskComponents = {
  debug: CodeDebug,
  optimize: CodeOptimize,
  review: CodeReview,
  proofread: CodeProofread
}

const currentTaskComponent = computed(() => {
  return taskComponents[currentTaskType.value]
})
</script>

<style scoped>
.main-content {
  flex: 1;
  background-color: #111827;
  overflow-y: auto;
}

.content-wrapper {
  display: flex;
  height: 100%;
  gap: 20px;
  padding: 20px;
}

.left-panel {
  flex: 7;
  background-color: #1f2937;
  border-radius: 8px;
  border: 1px solid #374151;
  overflow-y: auto;
}

.right-panel {
  flex: 3;
}

.assistant-panel {
  background-color: #1f2937;
  border: 1px solid #374151;
  border-radius: 8px;
  padding: 20px;
  color: #f3f4f6;
}

.assistant-panel h3 {
  margin-bottom: 16px;
  font-size: 16px;
  color: #d1d5db;
}
</style>