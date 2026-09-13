import React from 'react'
import ReactDOM from 'react-dom/client'
import 'antd/dist/reset.css'
import { DocumentsPage } from './pages/DocumentsPage'

// StrictMode 帮助开发期发现副作用；生产环境不会引入额外 UI。
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><DocumentsPage /></React.StrictMode>)
