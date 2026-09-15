import { useEffect, useState } from 'react'
import { Alert, Button, Card, Descriptions, Empty, Layout, Select, Space, Spin, Table, Tabs, Tag, Typography, Upload, message } from 'antd'
import type { UploadProps } from 'antd'
import { getContent, getMarkdown, getParseStatus, getSourceUrl, listDocuments, listVersions, parseDocument, retryParse, uploadDocument } from '../api/documents'
import type { Document, DocumentContent, DocumentVersion, ParseTask } from '../types/document'

const color = (status: string) => ({ PARSED: 'green', FAILED: 'red', PARSING: 'blue', QUEUED: 'gold', UPLOADED: 'default' }[status] ?? 'default')
const isProcessing = (status?: string) => status === 'QUEUED' || status === 'PARSING'

export function DocumentsPage() {
  const [document, setDocument] = useState<Document>()
  const [task, setTask] = useState<ParseTask>()
  const [markdown, setMarkdown] = useState('')
  const [content, setContent] = useState<DocumentContent>()
  const [versions, setVersions] = useState<DocumentVersion[]>([])
  const [selectedVersion, setSelectedVersion] = useState<number>()
  const [documents, setDocuments] = useState<Document[]>([])
  const [loadingDetail, setLoadingDetail] = useState(false)

  const refreshDocuments = async () => { try { setDocuments(await listDocuments()) } catch { message.error('无法获取文档列表') } }
  const updateDocumentStatus = (id: string, status: string) => {
    setDocuments(items => items.map(item => item.id === id ? { ...item, status } : item))
    setDocument(item => item?.id === id ? { ...item, status } : item)
  }
  const loadParsedContent = async (id: string, version?: number) => {
    const [nextMarkdown, nextContent] = await Promise.all([getMarkdown(id, version), getContent(id, version)])
    setMarkdown(nextMarkdown); setContent(nextContent)
  }
  const loadStatus = async (item: Document, silent = false) => {
    try {
      const next = await getParseStatus(item.id)
      setTask(next); updateDocumentStatus(item.id, next.status)
      if (next.status === 'PARSED') {
        const nextVersions = await listVersions(item.id)
        setVersions(nextVersions)
        const version = selectedVersion && nextVersions.some(item => item.version === selectedVersion) ? selectedVersion : nextVersions[0]?.version
        setSelectedVersion(version)
        await loadParsedContent(item.id, version)
      }
    } catch (error) { if (!silent) message.error(`无法读取文档详情：${String(error)}`) }
  }
  const selectDocument = async (item: Document) => {
    setDocument(item); setTask(undefined); setMarkdown(''); setContent(undefined); setVersions([]); setSelectedVersion(undefined)
    if (item.status === 'UPLOADED') return
    setLoadingDetail(true)
    try { await loadStatus(item) } finally { setLoadingDetail(false) }
  }
  const refresh = async (silent = false) => { if (document) await loadStatus(document, silent) }

  useEffect(() => { void refreshDocuments() }, [])
  useEffect(() => {
    if (!document || !isProcessing(task?.status ?? document.status)) return
    const timer = window.setInterval(() => { void refresh(true) }, 2500)
    return () => window.clearInterval(timer)
  }, [document?.id, document?.status, task?.status])

  const action: UploadProps['beforeUpload'] = async file => {
    try { const item = await uploadDocument(file); setDocuments(items => [item, ...items]); await selectDocument(item); message.success('文件已上传，可开始解析') } catch (error) { message.error(String(error)) }
    return false
  }
  const startParse = async () => {
    if (!document) return
    try { const next = await parseDocument(document.id); setTask(next); updateDocumentStatus(document.id, next.status); message.success('解析任务已进入队列，将自动刷新状态') } catch (error) { message.error(String(error)) }
  }
  const retry = async () => {
    if (!document) return
    try { const next = await retryParse(document.id); setTask(next); setMarkdown(''); setContent(undefined); updateDocumentStatus(document.id, next.status); message.success('已重新进入解析队列') } catch (error) { message.error(String(error)) }
  }
  const changeVersion = async (version: number) => {
    if (!document) return
    setSelectedVersion(version); setLoadingDetail(true)
    try { await loadParsedContent(document.id, version) } catch (error) { message.error(`无法加载历史版本：${String(error)}`) } finally { setLoadingDetail(false) }
  }

  const status = task?.status ?? document?.status ?? 'UPLOADED'
  return <Layout style={{ minHeight: '100vh', background: '#f5f7fa' }}><Layout.Content style={{ maxWidth: 1180, width: '100%', margin: '40px auto', padding: '0 20px' }}>
    <Typography.Title level={2} style={{ marginBottom: 4 }}>知识库文档</Typography.Title>
    <Typography.Paragraph type="secondary">上传、异步解析、原文与结构化结果预览。</Typography.Paragraph>
    <Card title="上传文档"><Upload maxCount={1} accept=".pdf,.png,.jpg,.jpeg,.webp" beforeUpload={action} showUploadList={false}><Button type="primary">选择文件并上传</Button></Upload><Typography.Text type="secondary" style={{ marginLeft: 12 }}>支持 PDF、PNG、JPG/JPEG、WEBP，单文件不超过 50 MB。</Typography.Text></Card>
    <Card title="文档列表" style={{ marginTop: 20 }}><Table size="middle" rowKey="id" dataSource={documents} pagination={{ pageSize: 8 }} rowClassName={row => row.id === document?.id ? 'ant-table-row-selected' : ''} columns={[
      { title: '文件名', dataIndex: 'filename', ellipsis: true }, { title: '类型', dataIndex: 'content_type', width: 180, ellipsis: true },
      { title: '状态', dataIndex: 'status', width: 120, render: (value: string) => <Tag color={color(value)}>{value}</Tag> },
      { title: '操作', width: 100, render: (_, row: Document) => <Button type="link" onClick={() => void selectDocument(row)}>查看</Button> },
    ]} /></Card>
    <Card title="文档详情" style={{ marginTop: 20 }} extra={document && <Tag color={color(status)}>{status}</Tag>}>
      {!document ? <Empty description="从文档列表选择一份文档查看详情" /> : <Spin spinning={loadingDetail}>
        <Descriptions size="small" column={{ xs: 1, sm: 2 }} items={[
          { key: 'filename', label: '文件名', children: document.filename }, { key: 'type', label: '文件类型', children: document.content_type },
          { key: 'size', label: '文件大小', children: `${(document.file_size / 1024).toFixed(1)} KB` }, { key: 'retry', label: '重试次数', children: task?.retry_count ?? 0 },
        ]} />
        <Space style={{ marginTop: 16 }} wrap><Button type="primary" onClick={() => void startParse()} disabled={isProcessing(status) || status === 'PARSED'}>开始解析</Button><Button onClick={() => void refresh()} disabled={status === 'UPLOADED'}>刷新状态</Button>{status === 'FAILED' && <Button danger onClick={() => void retry()}>重新解析</Button>}</Space>
        {isProcessing(status) && <Alert style={{ marginTop: 16 }} type="info" showIcon message="正在解析" description="页面会每 2.5 秒自动刷新一次解析状态。" />}
        {task?.error_message && <Alert style={{ marginTop: 16 }} type="error" message={`解析失败${task.error_code ? `（${task.error_code}）` : ''}`} description={task.error_message} />}
        {status === 'PARSED' && versions.length > 0 && <Space style={{ marginTop: 16 }}><Typography.Text>解析版本</Typography.Text><Select value={selectedVersion} style={{ width: 260 }} onChange={value => void changeVersion(value)} options={versions.map(item => ({ value: item.version, label: `v${item.version} · ${item.parser}${item.parser_version ? ` (${item.parser_version})` : ''}` }))} /></Space>}
        {status === 'PARSED' && <Tabs style={{ marginTop: 22 }} items={[
          { key: 'source', label: '原始文件', children: <iframe title="原始文档预览" src={getSourceUrl(document.id)} style={{ width: '100%', height: 680, border: '1px solid #f0f0f0', borderRadius: 6 }} /> },
          { key: 'markdown', label: 'Markdown 预览', children: markdown ? <pre style={{ maxHeight: 680, overflow: 'auto', margin: 0, padding: 18, whiteSpace: 'pre-wrap', background: '#fafafa', borderRadius: 6 }}>{markdown}</pre> : <Empty description="正在加载 Markdown" /> },
          { key: 'structure', label: `结构化内容 (${content?.blocks.length ?? 0})`, children: content ? <pre style={{ maxHeight: 680, overflow: 'auto', margin: 0, padding: 18, background: '#fafafa', borderRadius: 6 }}>{JSON.stringify(content, null, 2)}</pre> : <Empty description="正在加载结构化内容" /> },
        ]} />}
      </Spin>}
    </Card>
  </Layout.Content></Layout>
}
