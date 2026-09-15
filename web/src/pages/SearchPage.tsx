import { useEffect, useState } from 'react'
import { Alert, Button, Card, Empty, Input, Select, Space, Table, Tag, Typography, message } from 'antd'
import { getSourceUrl, listKnowledgeBases, listTags, searchDocuments } from '../api/documents'
import type { KnowledgeBase, SearchResponse, SearchResult, Tag as DocumentTag } from '../types/document'


const pageLabel = (item: SearchResult) => item.page_start ? item.page_start === item.page_end ? `第 ${item.page_start} 页` : `第 ${item.page_start}-${item.page_end} 页` : '页码未知'

function Highlight({ content, keyword }: { content: string; keyword: string }) {
  if (!keyword) return <>{content}</>
  const escaped = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return <>{content.split(new RegExp(`(${escaped})`, 'gi')).map((part, index) => part.toLowerCase() === keyword.toLowerCase() ? <mark key={index}>{part}</mark> : part)}</>
}

export function SearchPage() {
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([])
  const [tags, setTags] = useState<DocumentTag[]>([])
  const [knowledgeBaseId, setKnowledgeBaseId] = useState<string>()
  const [tagIds, setTagIds] = useState<string[]>([])
  const [query, setQuery] = useState('')
  const [result, setResult] = useState<SearchResponse>()
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    void Promise.all([listKnowledgeBases(), listTags()]).then(([nextBases, nextTags]) => { setKnowledgeBases(nextBases); setTags(nextTags) }).catch(() => message.error('无法获取知识库和标签'))
  }, [])

  const search = async (page = 1, pageSize = result?.page_size ?? 20) => {
    if (!knowledgeBaseId) { message.warning('请先选择知识库'); return }
    if (!query.trim()) { message.warning('请输入搜索关键词'); return }
    setLoading(true)
    try { setResult(await searchDocuments({ knowledgeBaseId, query: query.trim(), page, pageSize, tagIds })) } catch (error) { message.error(`搜索失败：${String(error)}`) } finally { setLoading(false) }
  }

  return <Card title="知识库检索测试">
    <Typography.Paragraph type="secondary">仅搜索所选知识库中已解析文档的最新版本，并返回版本、标题路径和页码引用。</Typography.Paragraph>
    <Space wrap style={{ marginBottom: 18 }}>
      <Select placeholder="选择知识库" style={{ width: 220 }} value={knowledgeBaseId} onChange={value => { setKnowledgeBaseId(value); setResult(undefined) }} options={knowledgeBases.map(item => ({ value: item.id, label: item.name }))} />
      <Select mode="multiple" allowClear placeholder="标签过滤（可选）" style={{ minWidth: 220 }} value={tagIds} onChange={setTagIds} options={tags.map(item => ({ value: item.id, label: item.name }))} />
      <Input.Search value={query} onChange={event => setQuery(event.target.value)} onSearch={() => void search(1)} enterButton="搜索" placeholder="输入关键词，例如：请假制度" style={{ width: 360 }} />
      <Button onClick={() => { setQuery(''); setTagIds([]); setResult(undefined) }}>清空</Button>
    </Space>
    {!knowledgeBaseId && <Alert type="info" showIcon message="请选择一个知识库作为检索边界" />}
    {result && result.total === 0 && <Empty description={`没有找到与“${result.query}”相关的内容`} />}
    {result && result.total > 0 && <Table loading={loading} rowKey="chunk_id" dataSource={result.items} pagination={{ current: result.page, pageSize: result.page_size, total: result.total, showSizeChanger: true, showTotal: total => `共 ${total} 个片段` }} onChange={pagination => void search(pagination.current ?? 1, pagination.pageSize ?? 20)} columns={[
      { title: '来源', width: 210, render: (_, item: SearchResult) => <Space direction="vertical" size={2}><Typography.Text strong>{item.filename}</Typography.Text><span><Tag>v{item.version}</Tag><Tag>{pageLabel(item)}</Tag></span><a href={`${getSourceUrl(item.document_id)}${item.page_start ? `#page=${item.page_start}` : ''}`} target="_blank" rel="noreferrer">查看原文</a></Space> },
      { title: '标题路径', dataIndex: 'heading_path', width: 210, render: (value?: string) => value ?? '—' },
      { title: '命中内容', dataIndex: 'content', render: (value: string) => <Typography.Paragraph ellipsis={{ rows: 5, expandable: true, symbol: '展开' }} style={{ margin: 0 }}><Highlight content={value} keyword={result.query} /></Typography.Paragraph> },
      { title: '得分', dataIndex: 'score', width: 85, render: (value: number) => value.toFixed(2) },
    ]} />}
    {!result && knowledgeBaseId && <Empty description="输入关键词开始检索" />}
  </Card>
}
