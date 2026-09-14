# Senkey Knowledge

企业知识库平台。当前交付第一阶段的文档基础设施：上传、对象存储、异步解析、标准化 `DocumentModel`、Markdown/JSON 预览、失败重试和版本记录。

## 技术栈与版本

### 前端

| 框架 / 组件 | 当前版本或要求 | 用途 |
|---|---|---|
| React | 18.3 | 管理界面渲染 |
| TypeScript | 5.6 | 前端类型检查 |
| Vite | 5.4 | 本地开发服务器与生产构建 |
| Ant Design | 5.22 | 企业后台 UI 组件 |

### 后端

| 框架 / 组件 | 当前版本或要求 | 用途 |
|---|---|---|
| Python | 3.11+（容器使用 3.12） | 文档服务运行时 |
| FastAPI | 0.115+ | REST API 与 OpenAPI 文档 |
| Uvicorn | 0.30+ | ASGI Web 服务器，用于运行 FastAPI 应用 |
| SQLAlchemy | 2.x | PostgreSQL ORM |
| Pydantic Settings | 2.x | `.env` 配置加载与校验 |
| Alembic | 1.14+ | 数据库迁移与表结构版本管理 |
| Dramatiq | 1.17+ | 文档解析异步 Worker |

### 基础设施与文档解析

| 组件 | 当前版本或要求 | 用途 |
|---|---|---|
| PostgreSQL | 16 | 文档、任务及版本元数据 |
| Redis | 7 | Dramatiq 任务队列 |
| MinIO | S3 兼容 | 原文件与解析产物存储 |
| MinerU | 独立部署，按发行版确定 | PDF、OCR 与版面解析 |
| Docker Compose | Compose v2 | 本地基础设施与完整链路编排 |

> `uvicorn` 是 Web 服务器，不是 `uv`。`uv` 是可选的 Python 包与环境管理工具；本项目当前以 `.venv + pip` 管理本地 Python 环境，并由 Uvicorn 启动 FastAPI。

精确的 Python 依赖范围定义在 [`knowledge-document-service/pyproject.toml`](knowledge-document-service/pyproject.toml)，前端依赖定义在 [`web/package.json`](web/package.json)。升级基础设施镜像或核心框架版本时，应同步验证上传、异步解析、重试和版本预览链路。

## 目录

- `knowledge-document-service/`：FastAPI 文档服务及 Dramatiq worker
- `web/`：React + TypeScript + Vite 管理界面
- `docs/architecture/`：已归档的架构设计稿
- `docs/DEVELOPMENT.md`：本地运行、接口与开发规范

## 开发启动

日常开发不需要将整个项目放入 Docker。推荐只用 Docker 运行 PostgreSQL、Redis 和 MinIO，后端、Worker 与前端在本机启动，以获得热更新和便捷调试。

### 1. 启动基础依赖

在仓库根目录执行：

```powershell
docker compose up postgres redis minio
```

这会启动 PostgreSQL、Redis 和 MinIO。首次拉取镜像需要一些时间；保持该终端运行即可。

### 2. 启动后端 API

另开一个终端：

```powershell
cd knowledge-document-service
if (!(Test-Path .env)) { Copy-Item .env.example .env }
if (!(Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app
```

启动入口读取当前目录的 `.env`，默认端口为 `8000`，`API_RELOAD=true` 会在修改 Python 代码后自动重启 API。必须使用 `.venv` 中的 Python 启动，否则可能缺少 `sqlalchemy` 等项目依赖。默认 API 文档地址为 `http://localhost:8000/docs`。

### 3. 启动异步解析 Worker

再开一个终端，并激活同一个虚拟环境：

```powershell
cd knowledge-document-service
.\.venv\Scripts\dramatiq.exe app.workers.parse_worker
```

Worker 负责消费 Redis 中的解析任务；没有它，上传和创建任务仍可成功，但任务不会进入解析状态。

### 4. 启动前端

再开一个终端：

```powershell
cd web
if (!(Test-Path .env)) { Copy-Item .env.example .env }
npm install
npm run dev
```

前端地址为 `http://localhost:5173`，MinIO 控制台为 `http://localhost:9001`。

### 自定义前后端端口

例如后端使用 `8100`、前端使用 `5200`，修改以下配置后，分别重新执行上面的后端和前端启动命令。

`knowledge-document-service/.env`：

```dotenv
API_HOST=127.0.0.1
API_PORT=8100
API_RELOAD=true
CORS_ORIGINS=["http://localhost:5200"]
```

`web/.env`：

```dotenv
VITE_PORT=5200
VITE_DOCUMENT_API=http://localhost:8100/api/v1
```

此时前端访问 `http://localhost:5200`，API 文档访问 `http://localhost:8100/docs`。`CORS_ORIGINS` 使用 JSON 数组；如果通过 `127.0.0.1` 访问前端，也需添加对应来源（例如 `http://127.0.0.1:5200`）。端口范围为 `1–65535`；前端端口被占用时会报错，不会自动切换。系统环境变量优先于 `.env`。后端必须通过 `python -m app` 启动才会使用 `API_HOST`、`API_PORT` 和 `API_RELOAD`。

Docker Compose 的 API 容器内部仍监听 `8000`，宿主机端口可在仓库根目录 `.env` 设置 `API_PORT=8100`，或在执行 Compose 前设置 `$env:API_PORT="8100"`。Compose 默认加载后端 `.env.example`，自定义前端端口时可在 `document-api.environment` 中设置 `CORS_ORIGINS: '["http://localhost:5200"]'`。

### DeepSeek Vision 与 MinerU 解析服务

默认解析器为云端 `DeepSeekVisionParser`：PDF 会在 Worker 中逐页转为图片，再通过 OpenAI 兼容的视觉接口请求 Markdown 和结构化 blocks。将 `DEEPSEEK_API_KEY`、`DEEPSEEK_VISION_MODEL` 设置在未提交的 `.env`（本地运行）或终端环境变量（Compose 运行）中；模型名必须是你的供应商实际提供的视觉模型名。

MinerU 仍作为可选的本地 GPU 备用解析服务保留。需要使用它时，把 `DOCUMENT_PARSER=mineru`，并使用 Compose GPU profile：

```powershell
docker compose --profile gpu up --build
```

DeepSeek Key、模型名未设置，或云端接口不可用时，任务会按预期标记为 `FAILED`，并可通过重试接口重新入队。

### 完整容器联调

如需验证完整容器化链路，可在仓库根目录执行：

```powershell
docker compose --profile gpu up --build
```

这会启动 API、Worker、PostgreSQL、Redis、MinIO 和 MinerU profile。默认 DeepSeek 解析不要求启动这个 profile；首次构建 MinerU 时才会下载 GPU 基础镜像和模型，因此耗时及磁盘占用都会明显增加。

两种解析器都通过统一 `Parser` 接口接入。切换解析器不会影响上传、异步任务、标准化、版本和预览流程。
