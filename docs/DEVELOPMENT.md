# 开发规则

## 阶段边界

第一阶段仅处理“文件到稳定结构化文档”：上传、存储、解析任务、解析器适配、标准化结果、预览、重试与版本。不得在此阶段引入 Embedding、向量库、检索、LLM 或 Agent。

## 分层规则

- API 只处理鉴权、校验和 DTO；业务流程放在 `services/`。
- 任何解析器都实现 `parsers/base.py` 的统一接口；业务代码不得依赖 MinerU 响应格式。
- 后续能力仅消费标准 `DocumentModel`，不得消费解析器原始 JSON。
- 原始文件、解析器输出、标准化输出必须分别存入 `raw/`、`parsed/`、`normalized/` 路径。
- 耗时解析必须由 worker 异步执行，HTTP 请求不得等待解析完成。

## 数据与状态规则

- 文档状态只能是 `UPLOADED`、`QUEUED`、`PARSING`、`PARSED`、`FAILED`。
- 每次成功解析新建一个不可变版本；重试会增加任务 `retry_count`。
- 错误信息应对用户可读，同时保留足够的服务端日志上下文，不能暴露凭据。
- 所有 ID 使用 UUID；对象路径不得拼接未经校验的用户文件名。

## 工程规则

- Python 使用类型标注、Pydantic DTO 和 SQLAlchemy 2 风格。
- 业务代码的类、公开函数、异步任务和非直观的状态转换必须使用中文注释或中文 docstring；注释说明“为什么/约束是什么”，不机械重复代码。
- 新增或修改核心流程时，中文注释覆盖率应不低于 80%；DTO 的简单字段可通过所属类注释集中说明。
- 新 API 要同时提供成功、失败和任务状态的测试；新解析器要提供 Normalizer 测试样例。
- 配置只能来自环境变量，不提交 `.env`、密钥或真实文档。
- 修改数据模型时添加 Alembic migration；当前初始 migration 是基线。

## 数据库与数据字典规则

- 每张新表必须有中文表注释，说明该表保存的业务对象、边界和生命周期。
- 每个字段必须有中文列注释，至少说明业务含义、单位/格式、是否为外键或状态值；不能只依赖字段英文名猜测含义。
- 枚举、状态码和关键索引必须有中文含义说明。状态流转同时在代码和本文档中保持一致。
- ORM 模型的 `comment` 与 Alembic migration 中的表/列注释必须同步维护；只改 ORM 不算完成，因为已部署数据库不会自动获得注释。
- 新建数据库的初始 migration 必须包含注释；修改既有表注释、字段注释或枚举说明时，必须新建独立 migration 并执行验证。
- 提交前用数据库客户端或 `psql \d+ 表名` 抽查表和字段注释是否实际写入 PostgreSQL。

## 本地运行

```powershell
docker compose up --build
cd web
npm install
npm run dev
```

服务 API：`http://localhost:8000/docs`。前端开发服务器：`http://localhost:5173`。

本机 API 在 `knowledge-document-service/` 下使用 `.\.venv\Scripts\python.exe -m app` 启动，通过该目录 `.env` 的 `API_PORT` 配置端口（默认 `8000`）。前端在 `web/.env` 中设置 `VITE_PORT`（默认 `5173`），然后执行 `npm run dev`。改端口后同步调整前端 `VITE_DOCUMENT_API` 和后端 `CORS_ORIGINS`，并重新启动服务。完整示例见 [README 的自定义端口说明](../README.md#自定义前后端端口)。

默认 Compose 启动业务依赖。MinerU 需要 GPU，并按 profile 单独启动：`docker compose --profile gpu up --build`。部署前请确认所选 MinerU 镜像/适配器在 `http://mineru:8080/parse` 接受 multipart `file` 并返回 `markdown`、可选 `blocks`/`content_list` 和 `parser_version`；不同 MinerU 发布版的服务启动命令可能不同，因此该契约被隔离在 `MinerUParser` 中。
