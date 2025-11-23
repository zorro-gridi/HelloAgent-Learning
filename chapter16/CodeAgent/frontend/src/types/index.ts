// 类型定义文件 - 定义整个项目使用的TypeScript类型

export type TaskType = 'debug' | 'optimize' | 'review' | 'proofread'

export interface ProcessNode {
  id: string
  name: string
  guidance: string
  executed: boolean
  data?: any
}

export interface TaskState {
  currentTaskType: TaskType
  currentProcessNode: string
  processNodes: ProcessNode[]
  taskData: Record<string, any>
}

export interface CodeEditorProps {
  modelValue: string
  language?: string
  height?: string
  readonly?: boolean
  placeholder?: string
}

export interface UserSettings {
  autoScroll: boolean
  showLineNumbers: boolean
  theme: 'dark' | 'light'
  fontSize: number
}