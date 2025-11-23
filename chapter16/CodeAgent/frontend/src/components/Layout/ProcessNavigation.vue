<template>
  <div class="process-navigation">
    <div class="progress-text">当前进度</div>
    <div class="nodes-container">
      <div
        v-for="(node, index) in processNodes"
        :key="node.id"
        class="node-item"
        @click="handleNodeClick(node.id)"
      >
        <div class="node-content">
          <div :class="['node-index', { executed: node.executed }]">
            {{ index + 1 }}
          </div>
          <div class="node-info">
            <div :class="['node-name', { executed: node.executed }]">
              {{ node.name }}
            </div>
            <div class="node-guidance">{{ node.guidance }}</div>
          </div>
          <button
            v-if="node.executed"
            class="node-reset-btn"
            @click.stop="handleNodeReset(node.id)"
          >
            🔄 重置
          </button>
        </div>
        <div
          v-if="index < processNodes.length - 1"
          :class="['node-connector', { executed: node.executed }]"
        ></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// 流程导航组件 - 显示当前任务进度和节点状态
import { ref, computed } from 'vue'
import type { ProcessNode } from '../../types'

const processNodes = ref<ProcessNode[]>([
  {
    id: 'node1',
    name: '提取异常堆栈',
    guidance: '复制异常堆栈',
    executed: true
  },
  {
    id: 'node2',
    name: '堆栈分析',
    guidance: '等待Agent分析',
    executed: true
  },
  {
    id: 'node3',
    name: '获取分析结果',
    guidance: '查看分析结果',
    executed: false
  },
  {
    id: 'node4',
    name: '生成上下文',
    guidance: '生成调试上下文',
    executed: false
  }
])

const handleNodeClick = (nodeId: string) => {
  // 滚动到对应节点
  console.log('跳转到节点:', nodeId)
}

const handleNodeReset = (nodeId: string) => {
  const nodeIndex = processNodes.value.findIndex(node => node.id === nodeId)
  if (nodeIndex !== -1) {
    // 重置当前及后续节点
    processNodes.value.forEach((node, index) => {
      if (index >= nodeIndex) {
        node.executed = false
      }
    })
  }
}
</script>

<style scoped>
.process-navigation {
  height: 80px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  background-color: #111827;
  border-bottom: 1px solid #374151;
}

.progress-text {
  font-size: 16px;
  color: #f3f4f6;
  margin-right: 40px;
}

.nodes-container {
  display: flex;
  align-items: center;
  flex: 1;
  gap: 20px;
}

.node-item {
  display: flex;
  align-items: center;
  flex: 1;
  cursor: pointer;
}

.node-content {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px;
  border-radius: 6px;
  transition: all 0.2s;
  position: relative;
}

.node-content:hover {
  background-color: #1f2937;
}

.node-content:hover .node-reset-btn {
  display: block;
}

.node-index {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 1px solid #6b7280;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: bold;
  color: #9ca3af;
  transition: all 0.3s;
}

.node-index.executed {
  background: linear-gradient(135deg, #3b82f6, #10b981);
  border: none;
  color: white;
}

.node-info {
  flex: 1;
}

.node-name {
  font-size: 14px;
  color: #9ca3af;
  transition: color 0.3s;
}

.node-name.executed {
  color: #f3f4f6;
}

.node-guidance {
  font-size: 12px;
  color: #9ca3af;
}

.node-reset-btn {
  display: none;
  background: transparent;
  border: none;
  color: #ef4444;
  font-size: 12px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
}

.node-reset-btn:hover {
  background-color: #374151;
}

.node-connector {
  flex: 1;
  height: 2px;
  background-color: #4b5563;
  margin: 0 10px;
  transition: background-color 0.3s;
}

.node-connector.executed {
  background: linear-gradient(90deg, #3b82f6, #10b981);
}
</style>