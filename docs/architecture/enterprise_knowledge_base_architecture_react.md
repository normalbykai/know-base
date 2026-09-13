# 企业级知识库平台技术设计与框架选型

## 1. 项目目标

本项目目标不是搭建一个简单的 RAG Demo，而是构建一套可以长期演进、支持企业真实业务场景的知识库平台。

第一阶段重点不是大模型问答，而是先建立可靠的文档基础设施：

- 文档上传
- 原始文件存储
- 文档解析
- 解析任务管理
- 文档标准化
- Markdown / JSON 输出
- 文档预览
- 解析失败重试
- 文档版本管理

在文档底座稳定后，再逐步建设：

- Chunk 切分
- BM25 全文检索
- Embedding 向量检索
- Hybrid Search
- Reranker
- LLM 问答
- 引用来源
- ACL 权限检索
- Agent / 工作流

---

# 2. 总体设计原则

## 2.1 不把整个系统绑定到某一个开源产品

Dify、FastGPT、RAGFlow 都可以作为参考、验证或部分能力来源，但不建议把整个企业知识库业务层完全绑定到某一个现成平台。

正式产品建议采用：

```text
自研业务平台
+
成熟文档解析组件
+
成熟 RAG 框架
+
可替换模型能力
```

这样可以避免未来被：

- 数据结构
- UI
- 技术栈
- License
- 模型厂商
- 向量数据库

锁死。

---

## 2.2 文档解析、检索、生成必须分层

整个知识库链路建议拆分为：

```text
文件
 ↓
文档解析
 ↓
统一 DocumentModel
 ↓
Chunk
 ↓
索引
 ↓
检索
 ↓
Rerank
 ↓
LLM
 ↓
答案 + 来源引用
```

这些能力不要混在一个模块中。

---

# 3. 总体技术架构

建议整体技术栈如下：

```text
前端：
React + TypeScript + Vite

前端推荐配套：
- React Router：路由管理
- TanStack Query：服务端状态 / API 数据缓存
- Ant Design：企业级 UI 组件库
- Zustand：轻量全局状态（按需）
- Axios / Fetch：HTTP 请求
- Monaco Editor：后续如需 JSON / Markdown / Prompt 编辑能力时可引入

业务后端：
Spring Boot 3

AI / 文档 / RAG 服务：
Python + FastAPI

关系数据库：
PostgreSQL

全文检索：
Elasticsearch / OpenSearch

向量数据库：
Qdrant

对象存储：
MinIO / S3

缓存 / 任务队列：
Redis

文档解析：
MinerU
Docling（后续可选）

RAG 框架：
LlamaIndex

复杂 Agent / 工作流：
LangGraph（后续按需引入）

Embedding：
独立模型服务

Reranker：
独立模型服务

LLM：
统一 LLM Gateway
```

---

# 3.1 前端框架选型

当前项目已经使用 React，建议继续沿用现有前端技术体系，不需要为了知识库项目切换到 Vue。

推荐前端栈：

```text
React
+
TypeScript
+
Vite
+
React Router
+
TanStack Query
+
Ant Design
+
Zustand（按需）
```

各组件职责：

| 组件 | 作用 |
|---|---|
| React | 前端核心框架 |
| TypeScript | 类型安全 |
| Vite | 构建工具与开发服务器 |
| React Router | 页面路由 |
| TanStack Query | API 请求、缓存、刷新、请求状态管理 |
| Ant Design | 企业级后台 UI |
| Zustand | 少量跨页面全局状态 |
| Axios / Fetch | HTTP 请求 |

前端第一阶段重点页面建议包括：

```text
知识库列表
文档列表
文档上传
解析任务状态
文档详情
Markdown 预览
结构化 JSON 预览
解析失败信息
重新解析
文档版本
```

推荐前端模块划分：

```text
src/
├── api/
├── components/
├── features/
│   ├── knowledge-base/
│   ├── documents/
│   ├── parse-tasks/
│   └── document-preview/
├── hooks/
├── layouts/
├── pages/
├── router/
├── store/
├── types/
└── utils/
```

建议前端不要直接理解 MinerU 的数据结构，而只消费后端定义好的 `DocumentModel`、`DocumentDTO` 与 `ParseTaskDTO`。

# 4. 推荐系统架构

```text
                    企业知识库平台
                           │
          ┌────────────────┴────────────────┐
          │                                 │
       React Web                          Open API
          │                                 │
          └──────────── Spring Boot ─────────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
         用户权限        知识空间        文档管理
         RBAC/ACL        Knowledge       Version
            │              │              │
            └──────────────┼──────────────┘
                           │
                    Document Service
                      FastAPI
                           │
                    Parser Router
                           │
              ┌────────────┴────────────┐
              │                         │
           MinerU                    Docling
       复杂 PDF / OCR            通用 Office / PDF
              │                         │
              └────────────┬────────────┘
                           ↓
                    DocumentModel
                           │
                           ↓
                    Index Service
                           │
             ┌─────────────┼─────────────┐
             ↓             ↓             ↓
          BM25          Vector        Metadata
      Elasticsearch     Qdrant         Filter
             └─────────────┼─────────────┘
                           ↓
                     Hybrid Search
                           ↓
                        Rerank
                           ↓
                     ACL 权限过滤
                           ↓
                      Context Builder
                           ↓
                          LLM
                           ↓
                    答案 + 来源引用
```

---

# 5. 第一阶段范围

第一阶段建议只完成：

```text
上传文件
   ↓
MinIO
   ↓
创建解析任务
   ↓
Redis Queue
   ↓
Worker
   ↓
MinerU
   ↓
Normalizer
   ↓
DocumentModel
   ↓
Markdown + JSON
   ↓
解析结果预览
```

暂时不要加入：

- Embedding
- Qdrant
- Milvus
- LlamaIndex
- LangChain
- LangGraph
- Agent
- LLM 问答

第一阶段的目标是把“企业文件变成稳定、结构化的数据”。

---

# 6. 第一阶段核心服务

建议第一个正式服务命名为：

```text
knowledge-document-service
```

职责：

- 文件上传
- 文件存储
- 文档解析
- 解析任务管理
- 解析状态管理
- Markdown 生成
- JSON 生成
- 文档预览
- 解析失败重试
- 文档版本管理

---

# 7. Document Service 技术选型

推荐：

```text
语言：
Python 3.11 / 3.12

Web：
FastAPI

ORM：
SQLAlchemy 2

Migration：
Alembic

任务队列：
Dramatiq / Celery

缓存 / Queue：
Redis

数据库：
PostgreSQL 16+

对象存储：
MinIO

HTTP Client：
httpx

数据模型：
Pydantic 2

文档解析：
MinerU

后续增强：
Docling
```

---

# 8. MinerU 是什么

MinerU 是文档解析引擎。

它不是：

- 向量模型
- Embedding 模型
- 大语言模型
- RAG 框架
- 向量数据库

它负责把 PDF、扫描件、Office 文档等转换成结构化内容。

例如：

```text
PDF
 ↓
Layout Detection
 ↓
OCR
 ↓
Table Recognition
 ↓
Formula Recognition
 ↓
Reading Order
 ↓
Markdown / JSON
```

适合处理：

- PDF
- 扫描 PDF
- 图片
- Word
- PPT
- Excel
- 表格
- 公式
- 多栏文档
- 页眉页脚
- 复杂版面

---

# 9. 为什么 MinerU 要独立部署

不建议：

```text
FastAPI
 └── import MinerU
      └── 模型
          └── GPU
```

推荐：

```text
knowledge-document-service
        │
        │ HTTP
        ↓
   MinerU Service
        │
        ↓
       GPU
```

原因：

1. MinerU 较重
2. 涉及 OCR / VLM / GPU
3. 模型升级频繁
4. 业务服务不应该依赖具体解析引擎
5. 后续可以方便替换为 Docling 或其他 Parser
6. MinerU 可以独立扩容

---

# 10. 第一阶段部署结构

```text
docker compose

├── document-api
├── document-worker
├── postgres
├── redis
├── minio
└── mineru
```

服务关系：

```text
┌─────────────────────────────┐
│      document-api           │
│         FastAPI             │
└──────────────┬──────────────┘
               │
      ┌────────┼─────────┐
      ↓        ↓         ↓
 PostgreSQL   Redis     MinIO
               │
               ↓
       document-worker
               │
               ↓
            MinerU
               │
              GPU
```

---

# 11. 项目目录建议

```text
knowledge-document-service/
│
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   ├── documents.py
│   │   └── health.py
│   │
│   ├── models/
│   │   ├── document.py
│   │   └── parse_task.py
│   │
│   ├── schemas/
│   │   └── document.py
│   │
│   ├── services/
│   │   ├── document_service.py
│   │   ├── parser_service.py
│   │   ├── storage_service.py
│   │   └── mineru_client.py
│   │
│   ├── parsers/
│   │   ├── base.py
│   │   ├── mineru.py
│   │   └── router.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   └── database.py
│   │
│   └── workers/
│       └── parse_worker.py
│
├── migrations/
├── docker/
├── tests/
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── .env
```

---

# 12. Parser Router 设计

不要让业务代码直接依赖 MinerU。

定义统一 Parser 接口：

```text
Parser
├── MinerUParser
├── DoclingParser
├── ExcelParser
├── HtmlParser
└── EmailParser
```

路由逻辑：

```text
上传文件
   ↓
File Detector
   ↓
Parser Router
   │
   ├── PDF → MinerU
   ├── 扫描 PDF → MinerU + OCR
   ├── DOCX → MinerU / Docling
   ├── PPTX → MinerU / Docling
   ├── XLSX → Excel Parser
   ├── HTML → Html Parser
   └── Email → Email Parser
```

---

# 13. DocumentModel

DocumentModel 是整个知识库最重要的中间数据模型之一。

原则：

> 后续 Chunk、索引、Embedding、RAG 只依赖 DocumentModel，不依赖 MinerU。

示例：

```json
{
  "document_id": "doc_123",
  "title": "员工手册",
  "metadata": {
    "filename": "employee-handbook.pdf",
    "content_type": "application/pdf",
    "page_count": 53
  },
  "blocks": [
    {
      "id": "block_001",
      "type": "heading",
      "page": 1,
      "level": 1,
      "text": "第一章 公司介绍"
    },
    {
      "id": "block_002",
      "type": "paragraph",
      "page": 1,
      "text": "本公司成立于……"
    },
    {
      "id": "block_003",
      "type": "table",
      "page": 2,
      "content": "<table>...</table>"
    }
  ]
}
```

---

# 14. 为什么必须有 DocumentModel

未来解析链路可能变成：

```text
PDF ─────────────→ MinerU

DOCX ────────────→ Docling

Excel ───────────→ 自定义 Excel Parser

HTML ────────────→ HTML Parser

Email ───────────→ Email Parser

                      │
                      ↓
                DocumentModel
```

如果系统直接依赖 MinerU JSON：

- MinerU 升级会影响后续系统
- 无法灵活替换解析器
- 不同文件类型输出不统一
- Chunk 逻辑会变得混乱
- 测试成本增加

因此必须增加 Normalizer 层。

---

# 15. 文件存储结构

建议 MinIO 内按三层保存。

## 15.1 原始文件

```text
documents/
└── raw/
    └── doc_123/
        └── original.pdf
```

## 15.2 Parser 原始结果

```text
documents/
└── parsed/
    └── doc_123/
        ├── mineru.json
        ├── mineru.md
        └── images/
```

## 15.3 标准结果

```text
documents/
└── normalized/
    └── doc_123/
        ├── document.json
        └── document.md
```

---

# 16. 文档处理完整流程

```text
用户上传 PDF
      ↓
Document API
      ↓
生成 document_id
      ↓
MinIO 保存原始文件
      ↓
PostgreSQL 创建 Document
      ↓
创建 Parse Task
      ↓
Redis Queue
      ↓
Document Worker
      ↓
调用 MinerU
      ↓
MinerU Markdown / JSON
      ↓
Normalizer
      ↓
DocumentModel
      ↓
保存 Markdown / JSON
      ↓
更新 Document 状态
      ↓
前端查看解析结果
```

---

# 17. 为什么解析必须异步

不要设计成：

```text
POST /documents
      ↓
同步等待 MinerU
      ↓
几十秒 / 几分钟
      ↓
返回
```

应该设计成：

```text
上传
 ↓
创建任务
 ↓
立即返回 task_id
 ↓
后台 Worker 解析
 ↓
前端轮询 / WebSocket / SSE
 ↓
解析完成
```

---

# 18. 推荐 API

## 18.1 上传文档

```http
POST /api/v1/documents
```

返回：

```json
{
  "id": "doc_123",
  "filename": "employee-handbook.pdf",
  "status": "UPLOADED"
}
```

---

## 18.2 创建解析任务

```http
POST /api/v1/documents/{document_id}/parse
```

返回：

```json
{
  "task_id": "task_456",
  "document_id": "doc_123",
  "status": "QUEUED"
}
```

---

## 18.3 获取文档

```http
GET /api/v1/documents/{document_id}
```

---

## 18.4 获取解析状态

```http
GET /api/v1/documents/{document_id}/parse-status
```

---

## 18.5 获取标准化内容

```http
GET /api/v1/documents/{document_id}/content
```

---

## 18.6 获取 Markdown

```http
GET /api/v1/documents/{document_id}/markdown
```

---

# 19. 数据库设计

## 19.1 documents

```text
documents

id
knowledge_base_id

filename
content_type
file_size
storage_path

status

created_by
created_at
updated_at
```

状态建议：

```text
UPLOADED
QUEUED
PARSING
PARSED
FAILED
```

---

## 19.2 document_versions

```text
document_versions

id
document_id

version

source_path
markdown_path
json_path

parser
parser_version

created_at
```

例如：

```text
parser = mineru
parser_version = 3.x
```

这样未来 MinerU 升级后可以重新解析生成新的 Version。

---

## 19.3 parse_tasks

```text
parse_tasks

id
document_id

status

parser

started_at
finished_at

error_code
error_message

retry_count

created_at
updated_at
```

---

# 20. 第一阶段状态机

```text
UPLOADED
   ↓
QUEUED
   ↓
PARSING
   ↓
PARSED
```

失败：

```text
PARSING
   ↓
FAILED
   ↓
RETRY
   ↓
QUEUED
```

---

# 21. 为什么暂时不使用 LlamaIndex

第一阶段的核心问题是：

> 文件能不能被稳定、正确地转换成结构化内容？

LlamaIndex 更适合：

- Chunk
- Index
- Retriever
- Query Engine
- Metadata Filter
- RAG

因此建议在 Document Service 稳定后再引入。

---

# 22. 第二阶段：Chunk Engine

DocumentModel 完成后：

```text
DocumentModel
      ↓
Chunk Engine
      ↓
Chunk[]
```

Chunk 不应该只是固定字符数切分。

后续应该考虑：

- 标题层级
- 段落
- 页码
- 表格
- 章节
- Markdown 结构
- Token 数
- Overlap
- 语义边界

---

# 23. 第三阶段：BM25

第一版检索可以先不使用 Embedding。

```text
Document
   ↓
Chunk
   ↓
Elasticsearch / OpenSearch
   ↓
BM25
```

适合：

- 产品编号
- 合同编号
- 人名
- 术语
- 错误码
- 精确关键词

---

# 24. 第四阶段：Embedding

Embedding 的作用：

```text
Chunk
 ↓
Embedding Model
 ↓
Vector
 ↓
Qdrant
```

用户问题：

```text
Question
 ↓
Embedding
 ↓
Vector Search
 ↓
Relevant Chunks
```

Embedding 是一个独立能力，不应该绑死某一个供应商。

建议定义：

```text
EmbeddingProvider

├── OpenAI
├── BGE
├── Qwen
└── Private Model
```

---

# 25. 第五阶段：Hybrid Search

正式企业知识库建议最终使用：

```text
用户问题
   ↓
Query Rewrite
   ↓
┌─────────────────┐
│ Hybrid Search   │
├─────────────────┤
│ BM25            │
│ Vector Search   │
└─────────────────┘
   ↓
Reranker
   ↓
ACL Filter
   ↓
Top K
   ↓
LLM
   ↓
答案 + 引用
```

不建议最终只使用纯向量检索。

---

# 26. 第六阶段：RAG

推荐：

```text
FastAPI
+
LlamaIndex
```

LlamaIndex 负责：

- Chunk
- Metadata
- Index
- Retriever
- Query Engine
- RAG Pipeline

---

# 27. 第七阶段：Agent

只有出现以下场景时，再考虑 LangGraph：

```text
查知识库
   ↓
查数据库
   ↓
调用 ERP
   ↓
调用 CRM
   ↓
判断
   ↓
再次查询
   ↓
综合回答
```

此时：

```text
LlamaIndex
+
LangGraph
```

会比较合适。

---

# 28. 权限模型

企业知识库一定需要考虑：

```text
Tenant
 ↓
Knowledge Base
 ↓
Document
 ↓
Chunk
```

权限至少需要支持：

- 租户权限
- 部门权限
- 用户权限
- Knowledge Base 权限
- Document 权限
- ACL

特别注意：

> ACL 必须进入检索链路，而不是检索完成后仅在前端隐藏。

---

# 29. 第一阶段测试标准

建议准备至少 100 份真实企业文档。

类型包括：

- 普通 PDF
- 扫描 PDF
- Word
- Excel
- PPT
- 合同
- 制度文件
- 表格密集文件
- 图片密集文件
- 多栏 PDF
- 几十页文件
- 几百页文件

重点测试：

```text
是否能够解析

文字是否完整

阅读顺序是否正确

标题层级是否正确

表格是否丢失

图片是否保留

页码是否保留

扫描件 OCR 是否正常

失败是否可以重试

大文件是否稳定

Parser 升级是否支持重新解析
```

---

# 30. 开发阶段规划

## Phase 1

```text
文档上传
+
MinIO
+
解析任务
+
MinerU
+
DocumentModel
+
Markdown / JSON
```

## Phase 2

```text
Chunk Engine
```

## Phase 3

```text
BM25
+
Elasticsearch / OpenSearch
```

## Phase 4

```text
Embedding
+
Qdrant
```

## Phase 5

```text
Hybrid Search
+
Reranker
```

## Phase 6

```text
LLM
+
RAG
+
来源引用
```

## Phase 7

```text
ACL
+
多租户
+
部门权限
```

## Phase 8

```text
Agent
+
业务系统集成
+
ERP / CRM / Database
```

---

# 31. 第一阶段最终技术选型

当前建议确定为：

| 模块 | 技术 |
|---|---|
| 前端 | React + TypeScript + Vite |
| 企业业务服务 | Spring Boot 3 |
| Document Service | FastAPI |
| ORM | SQLAlchemy 2 |
| 数据模型 | Pydantic 2 |
| Migration | Alembic |
| 数据库 | PostgreSQL |
| 对象存储 | MinIO |
| 缓存 / Queue | Redis |
| Worker | Dramatiq / Celery |
| 文档解析 | MinerU |
| 后续通用 Parser | Docling |
| Excel 特殊处理 | openpyxl + 自定义 |
| HTTP Client | httpx |
| 容器化 | Docker / Docker Compose |

---

# 32. 中长期技术选型

| 模块 | 技术 |
|---|---|
| RAG Framework | LlamaIndex |
| Agent Framework | LangGraph |
| 全文搜索 | Elasticsearch / OpenSearch |
| 向量数据库 | Qdrant |
| Embedding | 独立 Embedding Provider |
| Reranker | 独立 Reranker Service |
| LLM | LLM Gateway |
| 权限 | Spring Boot RBAC + ACL |
| 文件存储 | MinIO / S3 |
| 数据库 | PostgreSQL |
| Cache | Redis |

---

# 33. 当前最推荐的实施方案

第一阶段不要同时引入过多组件。

先完成：

```text
knowledge-document-service
        │
        ├── FastAPI
        ├── PostgreSQL
        ├── Redis
        ├── MinIO
        ├── Worker
        └── MinerU Service
```

并完成：

```text
Upload
 ↓
Store
 ↓
Parse
 ↓
Normalize
 ↓
DocumentModel
 ↓
Markdown + JSON
 ↓
Preview
```

这就是整个企业知识库的第一块地基。

---

# 34. 最终结论

当前不建议从“大模型问答”开始。

真正可用的企业知识库，第一优先级应该是：

```text
文档基础设施
```

而不是：

```text
LLM
```

推荐第一阶段正式确定：

```text
FastAPI
+
PostgreSQL
+
Redis
+
MinIO
+
MinerU
+
自研 DocumentModel
```

然后再逐步演进到：

```text
DocumentModel
 ↓
Chunk
 ↓
BM25
 ↓
Embedding
 ↓
Hybrid Search
 ↓
Reranker
 ↓
ACL
 ↓
LLM
```

这样整体系统具备：

- 可替换
- 可扩展
- 可测试
- 可升级
- 可私有化
- 可多租户
- 可做真正企业级产品

而不是一个只能演示的 RAG Demo。
