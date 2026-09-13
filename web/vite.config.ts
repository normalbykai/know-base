import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 固定本地端口，便于后端 CORS 白名单和开发文档保持一致。
export default defineConfig({ plugins: [react()], server: { port: 5173 } })
