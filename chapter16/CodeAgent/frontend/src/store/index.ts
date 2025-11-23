// 状态管理文件 - 使用Pinia管理应用全局状态
import { defineStore } from 'pinia'
import type { TaskState, TaskType } from '../types'

export const useAppStore = defineStore('app', {
  state: (): TaskState => ({
    currentTaskType: 'debug',
    currentProcessNode: 'node1',
    processNodes: [
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
      }
    ],
    taskData: {}
  }),

  actions: {
    setCurrentTaskType(type: TaskType) {
      this.currentTaskType = type
    },

    setCurrentProcessNode(nodeId: string) {
      this.currentProcessNode = nodeId
    },

    updateProcessNode(nodeId: string, updates: Partial<ProcessNode>) {
      const node = this.processNodes.find(n => n.id === nodeId)
      if (node) {
        Object.assign(node, updates)
      }
    },

    resetTask() {
      this.processNodes.forEach(node => {
        node.executed = false
      })
      this.taskData = {}
    }
  }
})