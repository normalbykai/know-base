import { useEffect, useState } from 'react'
import { Alert, Button, Card, Descriptions, Empty, Input, Layout, Popconfirm, Select, Space, Spin, Table, Tabs, Tag, Timeline, Typography, Upload, message } from 'antd'
import type { TablePaginationConfig, UploadProps } from 'antd'
import { assignKnowledgeBase, batchDelete, batchParse, batchRetry, createKnowledgeBase, createTag, deleteDocument, getContent, getDocumentTags, getMarkdown, getParseStatus, getSourceUrl, listDocuments, listKnowledgeBases, listParseTasks, listTags, listVersions, parseDocument, replaceDocumentTags, retryParse, uploadDocument } from '../api/documents'
import type { Document, DocumentContent, DocumentVersion, KnowledgeBase, ParseTask, Tag as DocumentTag } from '../types/document'

const color = (status: string) => ({ PARSED: 'green', FAILED: 'red', PARSING: 'blue', QUEUED: 'gold', UPLOADED: 'default' }[status] ?? 'default')
const isProcessing = (status?: string) => status === 'QUEUED' || status === 'PARSING'
const formatTime = (value?: string) => value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '—'

export function DocumentsPage() {
  const [document, setDocument] = useState<Document>()
  const [task, setTask] = useState<ParseTask>()
  const [tasks, setTasks] = useState<ParseTask[]>([])
  const [markdown, setMarkdown] = useState('')
  const [content, setContent] = useState<DocumentContent>()
  const [versions, setVersions] = useState<DocumentVersion[]>([])
  const [selectedVersion, setSelectedVersion] = useState<number>()
  const [documents, setDocuments] = useState<Document[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [keyword, setKeyword] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>()
  const [selectedIds, setSelectedIds] = useState<React.Key[]>([])
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([])
  const [tags, setTags] = useState<DocumentTag[]>([])
  const [documentTags, setDocumentTags] = useState<DocumentTag[]>([])
  const [knowledgeBaseFilter, setKnowledgeBaseFilter] = useState<string>()
  const [uploadKnowledgeBaseId, setUploadKnowledgeBaseId] = useState<string>()
  const [newKnowledgeBaseName, setNewKnowledgeBaseName] = useState('')
  const [newTagName, setNewTagName] = useState('')
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [loadingList, setLoadingList] = useState(false)

  const refreshDocuments = async (nextPage = page, nextPageSize = pageSize) => {
    setLoadingList(true)
    try {
      const result = await listDocuments({ page: nextPage, pageSize: nextPageSize, keyword: keyword.trim() || undefined, status: statusFilter, knowledgeBaseId: knowledgeBaseFilter })
      setDocuments(result.items); setTotal(result.total); setPage(result.page); setPageSize(result.page_size)
    } catch { message.error('无法获取文档列表') } finally { setLoadingList(false) }
  }
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
      const [nextTasks, nextDocumentTags] = await Promise.all([listParseTasks(item.id), getDocumentTags(item.id)])
      setTasks(nextTasks); setDocumentTags(nextDocumentTags)
      if (next.status === 'PARSED') {
        const nextVersions = await listVersions(item.id)
        setVersions(nextVersions)
        const version = selectedVersion && nextVersions.some(versionItem => versionItem.version === selectedVersion) ? selectedVersion : nextVersions[0]?.version
        setSelectedVersion(version)
        await loadParsedContent(item.id, version)
      }
    } catch (error) { if (!silent) message.error(`无法读取文档详情：${String(error)}`) }
  }
  const selectDocument = async (item: Document) => {
    setDocument(item); setTask(undefined); setTasks([]); setDocumentTags([]); setMarkdown(''); setContent(undefined); setVersions([]); setSelectedVersion(undefined)
    if (item.status === 'UPLOADED') return
    setLoadingDetail(true)
    try { await loadStatus(item) } finally { setLoadingDetail(false) }
  }
  const refresh = async (silent = false) => { if (document) await loadStatus(document, silent) }

  useEffect(() => {
    void refreshDocuments(1)
    void Promise.all([listKnowledgeBases(), listTags()]).then(([nextKnowledgeBases, nextTags]) => { setKnowledgeBases(nextKnowledgeBases); setTags(nextTags) }).catch(() => message.error('无法获取知识库或标签'))
  }, [])
  useEffect(() => {
    if (!document || !isProcessing(task?.status ?? document.status)) return
    const timer = window.setInterval(() => { void refresh(true) }, 2500)
    return () => window.clearInterval(timer)
  }, [document?.id, document?.status, task?.status])

  const action: UploadProps['beforeUpload'] = async file => {
    try { await uploadDocument(file, uploadKnowledgeBaseId); await refreshDocuments(1); message.success(`${file.name} 已上传，可开始解析`) } catch (error) { message.error(String(error)) }
    return false
  }
  const startParse = async () => {
    if (!document) return
    try { const next = await parseDocument(document.id); setTask(next); updateDocumentStatus(document.id, next.status); await refreshDocuments(); message.success('解析任务已进入队列，将自动刷新状态') } catch (error) { message.error(String(error)) }
  }
  const retry = async () => {
    if (!document) return
    try { const next = await retryParse(document.id); setTask(next); setMarkdown(''); setContent(undefined); updateDocumentStatus(document.id, next.status); await refreshDocuments(); message.success('已重新进入解析队列') } catch (error) { message.error(String(error)) }
  }
  const changeVersion = async (version: number) => {
    if (!document) return
    setSelectedVersion(version); setLoadingDetail(true)
    try { await loadParsedContent(document.id, version) } catch (error) { message.error(`无法加载历史版本：${String(error)}`) } finally { setLoadingDetail(false) }
  }
  const runBatch = async (actionName: 'parse' | 'retry' | 'delete') => {
    const ids = selectedIds.map(String)
    if (!ids.length) return
    try {
      const result = actionName === 'parse' ? await batchParse(ids) : actionName === 'retry' ? await batchRetry(ids) : await batchDelete(ids)
      setSelectedIds([])
      if (document && result.processed_ids.includes(document.id)) setDocument(undefined)
      await refreshDocuments()
      message.success(`已处理 ${result.processed_ids.length} 份文档${Object.keys(result.skipped).length ? `，跳过 ${Object.keys(result.skipped).length} 份` : ''}`)
    } catch (error) { message.error(`批量操作失败：${String(error)}`) }
  }
  const removeDocument = async () => {
    if (!document) return
    try { await deleteDocument(document.id); setDocument(undefined); setTask(undefined); setTasks([]); await refreshDocuments(); message.success('文档及其解析产物已删除') } catch (error) { message.error(`删除失败：${String(error)}`) }
  }
  const addKnowledgeBase = async () => {
    if (!newKnowledgeBaseName.trim()) return
    try { const knowledgeBase = await createKnowledgeBase(newKnowledgeBaseName.trim()); setKnowledgeBases(items => [knowledgeBase, ...items]); setNewKnowledgeBaseName(''); message.success('知识库已创建') } catch (error) { message.error(`创建知识库失败：${String(error)}`) }
  }
  const addTag = async () => {
    if (!newTagName.trim()) return
    try { const tag = await createTag(newTagName.trim()); setTags(items => [...items, tag].sort((a, b) => a.name.localeCompare(b.name))); setNewTagName(''); message.success('标签已创建') } catch (error) { message.error(`创建标签失败：${String(error)}`) }
  }
  const changeDocumentKnowledgeBase = async (knowledgeBaseId?: string) => {
    if (!document) return
    try { const updated = await assignKnowledgeBase(document.id, knowledgeBaseId); setDocument(updated); setDocuments(items => items.map(item => item.id === updated.id ? updated : item)); message.success('文档归属已更新') } catch (error) { message.error(`更新归属失败：${String(error)}`) }
  }
  const changeDocumentTags = async (tagIds: string[]) => {
    if (!document) return
    try { setDocumentTags(await replaceDocumentTags(document.id, tagIds)); message.success('文档标签已更新') } catch (error) { message.error(`更新标签失败：${String(error)}`) }
  }
  const changePage = (pagination: TablePaginationConfig) => { void refreshDocuments(pagination.current ?? 1, pagination.pageSize ?? pageSize) }
  const status = task?.status ?? document?.status ?? 'UPLOADED'

  return <Layout style={{ minHeight: '100vh', background: '#f5f7fa' }}><Layout.Content style={{ maxWidth: 1180, width: '100%', margin: '40px auto', padding: '0 20px' }}>
    <Typography.Title level={2} style={{ marginBottom: 4 }}>知识库文档</Typography.Title>
    <Typography.Paragraph type="secondary">支持批量上传、解析、失败重试、筛选和版本追溯。</Typography.Paragraph>
    <Card title="知识库与标签"><Space wrap><Input.Search placeholder="新知识库名称" style={{ width: 210 }} value={newKnowledgeBaseName} onChange={event => setNewKnowledgeBaseName(event.target.value)} onSearch={() => void addKnowledgeBase()} enterButton="创建知识库" /><Input.Search placeholder="新标签名称" style={{ width: 190 }} value={newTagName} onChange={event => setNewTagName(event.target.value)} onSearch={() => void addTag()} enterButton="创建标签" /></Space></Card>
    <Card title="上传文档" style={{ marginTop: 20 }}><Space wrap><Select allowClear placeholder="上传到知识库（可选）" style={{ width: 230 }} value={uploadKnowledgeBaseId} onChange={setUploadKnowledgeBaseId} options={knowledgeBases.map(item => ({ value: item.id, label: item.name }))} /><Upload multiple accept=".pdf,.png,.jpg,.jpeg,.webp" beforeUpload={action} showUploadList={false}><Button type="primary">选择文件并上传</Button></Upload></Space><Typography.Text type="secondary" style={{ marginLeft: 12 }}>支持 PDF、PNG、JPG/JPEG、WEBP，单文件不超过 50 MB。</Typography.Text></Card>
    <Card title="文档列表" style={{ marginTop: 20 }} extra={<Space><Input.Search allowClear placeholder="按文件名筛选" style={{ width: 180 }} value={keyword} onChange={event => setKeyword(event.target.value)} onSearch={() => void refreshDocuments(1)} /><Select allowClear placeholder="全部状态" style={{ width: 120 }} value={statusFilter} onChange={value => { setStatusFilter(value); window.setTimeout(() => void refreshDocuments(1), 0) }} options={['UPLOADED', 'QUEUED', 'PARSING', 'PARSED', 'FAILED'].map(value => ({ value, label: value }))} /><Select allowClear placeholder="全部知识库" style={{ width: 160 }} value={knowledgeBaseFilter} onChange={value => { setKnowledgeBaseFilter(value); window.setTimeout(() => void refreshDocuments(1), 0) }} options={knowledgeBases.map(item => ({ value: item.id, label: item.name }))} /></Space>}>
      <Space style={{ marginBottom: 12 }}><Button disabled={!selectedIds.length} onClick={() => void runBatch('parse')}>批量开始解析</Button><Button disabled={!selectedIds.length} onClick={() => void runBatch('retry')}>批量重试</Button><Popconfirm title={`确认删除选中的 ${selectedIds.length} 份文档及全部解析产物？`} onConfirm={() => void runBatch('delete')} disabled={!selectedIds.length}><Button danger disabled={!selectedIds.length}>批量删除</Button></Popconfirm></Space>
      <Table loading={loadingList} size="middle" rowKey="id" dataSource={documents} rowSelection={{ selectedRowKeys: selectedIds, onChange: setSelectedIds }} pagination={{ current: page, pageSize, total, showSizeChanger: true, showTotal: count => `共 ${count} 份文档` }} onChange={changePage} rowClassName={row => row.id === document?.id ? 'ant-table-row-selected' : ''} columns={[
        { title: '文件名', dataIndex: 'filename', ellipsis: true }, { title: '类型', dataIndex: 'content_type', width: 150, ellipsis: true },
        { title: '状态', dataIndex: 'status', width: 110, render: (value: string) => <Tag color={color(value)}>{value}</Tag> }, { title: '上传时间', dataIndex: 'created_at', width: 175, render: (value: string) => formatTime(value) },
        { title: '操作', width: 90, render: (_, row: Document) => <Button type="link" onClick={() => void selectDocument(row)}>查看</Button> },
      ]} />
    </Card>
    <Card title="文档详情" style={{ marginTop: 20 }} extra={document && <Tag color={color(status)}>{status}</Tag>}>
      {!document ? <Empty description="从文档列表选择一份文档查看详情" /> : <Spin spinning={loadingDetail}>
        <Descriptions size="small" column={{ xs: 1, sm: 2 }} items={[
          { key: 'filename', label: '文件名', children: document.filename }, { key: 'type', label: '文件类型', children: document.content_type },
          { key: 'size', label: '文件大小', children: `${(document.file_size / 1024).toFixed(1)} KB` }, { key: 'retry', label: '重试次数', children: task?.retry_count ?? 0 },
          { key: 'parser', label: '解析器', children: task?.parser ?? '—' }, { key: 'duration', label: '处理耗时', children: task?.started_at && task?.finished_at ? `${Math.max(0, Math.round((new Date(task.finished_at).getTime() - new Date(task.started_at).getTime()) / 1000))} 秒` : '—' },
          { key: 'knowledge-base', label: '所属知识库', children: <Select allowClear placeholder="未归档" value={document.knowledge_base_id} style={{ minWidth: 180 }} onChange={value => void changeDocumentKnowledgeBase(value)} options={knowledgeBases.map(item => ({ value: item.id, label: item.name }))} /> }, { key: 'tags', label: '文档标签', children: <Select mode="multiple" placeholder="选择标签" value={documentTags.map(item => item.id)} style={{ minWidth: 220 }} onChange={value => void changeDocumentTags(value)} options={tags.map(item => ({ value: item.id, label: item.name }))} /> },
        ]} />
        <Space style={{ marginTop: 16 }} wrap><Button type="primary" onClick={() => void startParse()} disabled={isProcessing(status) || status === 'PARSED'}>开始解析</Button><Button onClick={() => void refresh()} disabled={status === 'UPLOADED'}>刷新状态</Button>{status === 'FAILED' && <Button danger onClick={() => void retry()}>重新解析</Button>}<Popconfirm title="确认删除此文档及其全部解析产物？" onConfirm={() => void removeDocument()}><Button danger disabled={isProcessing(status)}>删除文档</Button></Popconfirm></Space>
        {isProcessing(status) && <Alert style={{ marginTop: 16 }} type="info" showIcon message="正在解析" description="页面会每 2.5 秒自动刷新一次解析状态。" />}
        {task?.error_message && <Alert style={{ marginTop: 16 }} type="error" message={`解析失败${task.error_code ? `（${task.error_code}）` : ''}`} description={task.error_message} />}
        {tasks.length > 0 && <Card size="small" title="任务时间线" style={{ marginTop: 16 }}><Timeline items={tasks.map(item => ({ color: color(item.status), children: <span>{formatTime(item.created_at)} · <Tag color={color(item.status)}>{item.status}</Tag> · {item.parser ?? '—'} · 重试 {item.retry_count}{item.error_code ? ` · ${item.error_code}` : ''}</span> }))} /></Card>}
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
