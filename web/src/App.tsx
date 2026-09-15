import { Layout, Tabs, Typography } from 'antd'
import { DocumentsPage } from './pages/DocumentsPage'
import { SearchPage } from './pages/SearchPage'


export function App() {
  return <Layout style={{ minHeight: '100vh', background: '#f5f7fa' }}><Layout.Content style={{ maxWidth: 1180, width: '100%', margin: '32px auto', padding: '0 20px' }}>
    <Typography.Title level={2} style={{ marginBottom: 4 }}>Senkey Knowledge</Typography.Title>
    <Typography.Paragraph type="secondary">企业文档管理与可追溯知识检索。</Typography.Paragraph>
    <Tabs items={[{ key: 'documents', label: '文档管理', children: <DocumentsPage embedded /> }, { key: 'search', label: '检索测试', children: <SearchPage /> }]} />
  </Layout.Content></Layout>
}
