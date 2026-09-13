import { useEffect, useState } from 'react'
import { Alert, Button, Card, Layout, Space, Table, Tag, Typography, Upload, message } from 'antd'
import type { UploadProps } from 'antd'
import { getMarkdown, getParseStatus, listDocuments, parseDocument, retryParse, uploadDocument } from '../api/documents'
import type { Document, ParseTask } from '../types/document'

const color = (status: string) => ({ PARSED: 'green', FAILED: 'red', PARSING: 'blue', QUEUED: 'gold', UPLOADED: 'default' }[status] ?? 'default')

export function DocumentsPage() {
  // 当前详情与列表分离：上传或点击列表项后切换当前操作对象。
  const [document, setDocument] = useState<Document>()
  const [task, setTask] = useState<ParseTask>()
  const [markdown, setMarkdown] = useState('')
  const [documents, setDocuments] = useState<Document[]>([])
  // 页面首次进入加载文档；解析状态刷新由用户主动触发，避免无意义轮询。
  const refreshDocuments = () => listDocuments().then(setDocuments).catch(() => message.error('无法获取文档列表'))
  useEffect(() => { refreshDocuments() }, [])
  // 返回 false 阻止 Upload 组件自行提交，确保请求走统一的业务 API。
  const action: UploadProps['beforeUpload'] = async file => {
    try { const item = await uploadDocument(file); setDocument(item); setDocuments([item, ...documents]); setTask(undefined); setMarkdown(''); message.success('文件已上传') } catch (e) { message.error(String(e)) }
    return false
  }
  const startParse = async () => { if (!document) return; try { setTask(await parseDocument(document.id)); message.success('解析任务已进入队列') } catch (e) { message.error(String(e)) } }
  const refresh = async () => { if (!document) return; try { const next = await getParseStatus(document.id); setTask(next); if (next.status === 'PARSED') setMarkdown(await getMarkdown(document.id)) } catch (e) { message.error(String(e)) } }
  const retry = async () => { if (!document) return; try { setTask(await retryParse(document.id)); setMarkdown('') } catch (e) { message.error(String(e)) } }
  return <Layout style={{ minHeight: '100vh', background: '#f5f7fa' }}><Layout.Content style={{ maxWidth: 960, width: '100%', margin: '48px auto' }}>
    <Typography.Title level={2}>知识库文档</Typography.Title><Typography.Paragraph>第一阶段：上传、异步解析与标准化预览。</Typography.Paragraph>
    <Card title="上传文档"><Upload maxCount={1} beforeUpload={action} showUploadList={false}><Button>选择文件</Button></Upload>{document && <Space direction="vertical" style={{ marginTop: 20 }}><Typography.Text>{document.filename}</Typography.Text><Tag color={color(task?.status ?? document.status)}>{task?.status ?? document.status}</Tag><Space><Button type="primary" onClick={startParse} disabled={!!task}>开始解析</Button><Button onClick={refresh} disabled={!task}>刷新状态</Button>{task?.status === 'FAILED' && <Button danger onClick={retry}>重新解析</Button>}</Space>{task?.error_message && <Alert type="error" message="解析失败" description={task.error_message} />}</Space>}</Card>
    <Card title="文档列表" style={{ marginTop: 24 }}><Table size="small" rowKey="id" dataSource={documents} pagination={false} columns={[{ title: '文件名', dataIndex: 'filename' }, { title: '状态', dataIndex: 'status', render: (value: string) => <Tag color={color(value)}>{value}</Tag> }, { title: '操作', render: (_, row: Document) => <Button type="link" onClick={() => { setDocument(row); setTask(undefined); setMarkdown('') }}>查看</Button> }]} /></Card>
    {markdown && <Card title="Markdown 预览" style={{ marginTop: 24 }}><pre style={{ whiteSpace: 'pre-wrap' }}>{markdown}</pre></Card>}
  </Layout.Content></Layout>
}
