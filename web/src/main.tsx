import React from 'react'
import ReactDOM from 'react-dom/client'
import 'antd/dist/reset.css'
import { App } from './App'

// StrictMode 帮助开发期发现副作用；生产环境不会引入额外 UI。
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>)
