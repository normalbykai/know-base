import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// 使用 Vite 的环境文件加载规则，支持 .env、.env.local 和模式配置。
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', 'VITE_')
  const port = Number(env.VITE_PORT ?? '5173')
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error('VITE_PORT 必须是 1–65535 之间的整数')
  }

  return {
    plugins: [react()],
    // 端口占用时直接报错，防止自动换端口导致跨域白名单失效。
    server: { port, strictPort: true },
  }
})
