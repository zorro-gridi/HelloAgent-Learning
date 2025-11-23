import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Vite配置文件 - 配置Vue和开发服务器
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    open: true
  },
  build: {
    outDir: 'dist',
    sourcemap: true
  }
})