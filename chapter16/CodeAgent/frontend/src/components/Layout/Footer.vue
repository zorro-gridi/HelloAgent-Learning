<template>
  <footer class="footer">
    <div class="footer-left">
      <span class="status-text">代码调试 - 节点3已执行</span>
    </div>
    <div class="footer-center">
      <span class="version-text">v1.0.0 | {{ currentTime }}</span>
    </div>
    <div class="footer-right">
      <button class="help-button">?</button>
      <button class="feedback-button">反馈问题</button>
    </div>
  </footer>
</template>

<script setup lang="ts">
// 底部状态栏组件 - 显示任务状态、版本信息和帮助入口
import { ref, onMounted, onUnmounted } from 'vue'

const currentTime = ref('')

const updateTime = () => {
  const now = new Date()
  currentTime.value = now.toISOString().split('T')[0]
}

let timer: number

onMounted(() => {
  updateTime()
  timer = setInterval(updateTime, 60000) // 每分钟更新一次
})

onUnmounted(() => {
  clearInterval(timer)
})
</script>

<style scoped>
.footer {
  height: 40px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  background-color: #1f2937;
  border-top: 1px solid #374151;
  color: #9ca3af;
  font-size: 14px;
}

.footer-left,
.footer-center,
.footer-right {
  flex: 1;
}

.footer-center {
  text-align: center;
}

.footer-right {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 16px;
}

.help-button {
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  color: #9ca3af;
  cursor: pointer;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.feedback-button {
  background: transparent;
  border: none;
  color: #9ca3af;
  cursor: pointer;
  transition: color 0.2s;
}

.feedback-button:hover {
  color: #3b82f6;
}
</style>