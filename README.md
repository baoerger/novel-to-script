# Novel2Script — AI 小说转剧本工具

> A full-stack LLM application that converts Chinese novels into editable, structured screenplays with traceable intermediate results and quality checks.

Novel2Script 把长篇小说处理拆成一条可恢复、可观察的工程流水线：文本解析与分片、逐章提取、跨章角色去重、关系图谱、场景生成、剧本组装和三维质检。YAML 作为中间数据格式，既便于机器生成，也便于人工审阅和二次编辑；React 前端提供进度、角色、场景和剧本结构的可视化入口。

## 适合展示的工程能力

- 中文长文本的章节识别、段落边界感知和断点续跑；
- LLM 与启发式规则结合的角色归并和关系构建；
- FastAPI + React + Docker 的全栈交付；
- 结构化 YAML 输出、质量报告和可定位的问题记录；
- Mock LLM 测试覆盖解析器、分片器、提取器、汇总器和 API。

基于大语言模型（LLM）的智能小说到剧本转换工具，支持 `.txt` / `.docx` 输入，自动分章、提取角色与场景、汇总去重、生成结构化 YAML 剧本，并提供 Web 前端进行可视化交互。

---

## 创新亮点

> **不只是一个"调用 GPT 总结小说"的玩具** —— 本项目设计了一套完整的工程化转换流水线，从文本预处理到输出质检，每个环节都有针对性优化。

| 维度 | 创新点 | 说明 |
|------|--------|------|
| **流水线架构** | 7 阶段断点续跑 | 分片 → 逐章提取 → 跨章汇总去重 → 关系图谱 → 场景生成 → 组装 → 质检，任意阶段中断可恢复，不等同于单次 LLM 调用 |
| **中文文本分片** | 段落边界感知 + CJK 感知 Token 估算 | 三层正则降级识别章节 + 子章节来源追溯（`chapter_index × 1000 + sub_index`），汉字权重 1.5× vs 英文 1.3× |
| **跨章角色去重** | LLM + 启发式双层混合 | 先 LLM 别名合并，再启发式过滤（出场次数、描述长度、跨章跨度三重阈值），解决同一角色在不同章节有不同称呼的问题 |
| **关系图谱** | 共现矩阵驱动 | 不从零猜测人物关系，先基于场景共现数据计算共现矩阵，再喂给 LLM 定向提取 12 类关系（师徒/敌对/恋人/朋友/主仆/同门/仇敌/君臣/亲属/同僚/结拜/利用/陌路），自动补全反向边 |
| **质检系统** | 格式 + 一致性 + 结构三维检查 | 非阻塞式后置质检：空字段检测、幽灵角色（场景中出现但不在角色表）、对白缺失统计、场景来源可追溯性 |
| **中文 Prompt 体系** | 6 个独立设计的 Jinja2 模板 | 针对中文小说特点独立调优：7 类角色原型（导师/盟友/阴影/骗徒/边界守卫/信使/变形者）、4 种剧本元素（舞台指示/对白/画外音/转场）、结构化 JSON 输出约束 |
| **YAML 即数据格式** | 机器生成 + 人类可编辑 | YAML 作为转换物格式，前端用 Monaco Editor 直接编辑，无需导入导出专用格式，附带场景大纲导航 |
| **可观测性** | Markdown 质检报告 + Token 成本估算 | 按 DeepSeek 定价（¥0.28/百万 Token）实时估算费用，场景对白覆盖率统计，问题定位到具体场景 |

---

## Demo 视频

> **视频链接**: [【小说转剧本demo】 https://www.bilibili.com/video/BV1fqEt6xEbV/?share_source=copy_web&vd_source=d75f0b47ea0edbf92c0dcd3c09f0ec89]（请在此处放入 Bilibili / 云盘 / YouTube 等外部链接）

- 完整操作流程演示
- 小说上传 → 实时进度 → YAML 在线预览 → 角色表格 → 剧本编辑
- 转换结果示例展示

---

## 目录结构

```
novel-to-script/
├── backend/                  # 后端 (FastAPI + 转换引擎)
│   ├── app/
│   │   ├── main.py           # API 路由与全局中间件
│   │   ├── config.py         # 应用与 LLM 配置
│   │   ├── cli.py            # 命令行入口
│   │   ├── models/           # Pydantic 数据模型
│   │   │   ├── input.py      # 输入: NovelText, NovelChapter
│   │   │   ├── analysis.py   # 分析: ExtractedCharacter, SceneBoundary
│   │   │   ├── consolidated.py # 汇总: ConsolidatedAnalysis
│   │   │   ├── script.py     # 剧本: Script, ScriptScene, ScriptAct
│   │   │   └── task.py       # 任务: TaskInfo, TaskStatus
│   │   ├── prompts/          # Jinja2 Prompt 模板 (6 个)
│   │   └── services/         # 核心服务层
│   │       ├── pipeline.py           # 转换主流程编排
│   │       ├── parser.py             # .txt / .docx 解析器
│   │       ├── chunker.py            # 超长章节分片
│   │       ├── llm.py               # LLM 客户端抽象层
│   │       ├── orchestrator.py       # 逐章分析编排器
│   │       ├── extractor.py          # 角色提取
│   │       ├── scene_detector.py     # 场景检测
│   │       ├── dialogue_extractor.py # 对白提取
│   │       ├── consolidate.py        # 跨章汇总去重
│   │       ├── relationship_timeline.py # 关系时间线构建
│   │       ├── scene_generator.py    # 单场剧本生成
│   │       ├── yaml_writer.py        # YAML 序列化输出
│   │       ├── qa_agent.py           # 质检 Agent
│   │       ├── reporter.py           # 质量报告生成
│   │       ├── checkpoint.py         # 断点续跑
│   │       └── task_manager.py       # 异步任务生命周期管理
│   └── tests/                # 单元测试 + 集成测试
│       ├── fixtures/         # 测试用样本小说
│       ├── test_parser.py
│       ├── test_chunker.py
│       ├── test_extractor.py
│       ├── test_consolidator.py
│       └── test_api.py
├── frontend/                 # 前端 (React 18 + TypeScript + Vite)
│   ├── src/
│   │   ├── components/       # 通用组件
│   │   │   ├── Layout.tsx    # 页面布局壳
│   │   │   ├── Header.tsx    # 导航栏
│   │   │   ├── Footer.tsx    # 版权栏
│   │   │   ├── FileUpload.tsx # 拖拽上传组件
│   │   │   └── ProgressBar.tsx # 进度条组件
│   │   ├── pages/            # 页面
│   │   │   ├── ConvertPage.tsx      # 上传 + 转换进度
│   │   │   ├── YamlPreviewPage.tsx  # YAML 在线预览 (Monaco Editor)
│   │   │   ├── CharactersPage.tsx   # 角色表格 (搜索/排序)
│   │   │   └── ScriptEditorPage.tsx # 剧本结构化编辑器
│   │   ├── services/         # API 调用封装层
│   │   └── types/            # TypeScript 类型定义
│   ├── Dockerfile            # 前端多阶段构建 (Node → Nginx)
│   └── nginx.conf            # Nginx SPA + API 代理配置
├── projects/                 # 运行时生成的项目输出 (Persistence volume)
├── samples/                  # 示例小说
├── docker-compose.yml        # 一键全栈启动
├── progress.md               # 开发进度追踪
├── plan.md                   # 架构设计文档
├── design.md                 # 需求设计文档
└── research.md               # 技术调研笔记
```

---

## 本地启动指南

### 环境要求

| 依赖 | 版本要求 |
|------|----------|
| Python | ≥ 3.12 |
| Node.js | ≥ 22 |
| Docker (可选) | Docker Desktop / Docker Engine |
| LLM API Key | DeepSeek 或 Qwen API 密钥 |

### 方式一：Docker Compose 一键启动（推荐）

```bash
# 1. 配置 API Key
cp backend/.env.example backend/.env
# 编辑 backend/.env，填入 DEEPSEEK_API_KEY 或 QWEN_API_KEY

# 2. 启动全栈服务
docker compose up -d

# 3. 访问
# 前端: http://localhost
# 后端 API 文档: http://localhost:8000/docs
```

### 方式二：手动分别启动

#### 后端

```bash
cd backend

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Key

# 启动
uvicorn app.main:app --reload --port 8000
```

#### 前端

```bash
cd frontend

# 安装依赖
npm install

# 开发模式启动 (默认 http://localhost:5173)
npm run dev
```

> 开发模式下 Vite 自动代理 `/api` 到 `http://localhost:8000`，无需额外配置。

### 命令行使用 (无需前端)

```bash
cd backend
python -m app.cli input.txt -o output.yaml
```

---

## 第三方依赖与原创性声明

### 后端依赖 (Python)

| 库名 | 版本 | 用途 | 许可证 |
|------|------|------|--------|
| [FastAPI](https://fastapi.tiangolo.com/) | ≥ 0.115.0 | Web API 框架 | MIT |
| [Uvicorn](https://www.uvicorn.org/) | ≥ 0.34.0 | ASGI 服务器 | BSD |
| [Pydantic](https://docs.pydantic.dev/) | ≥ 2.10.0 | 数据校验与序列化 | MIT |
| [OpenAI Python SDK](https://github.com/openai/openai-python) | ≥ 1.68.0 | LLM 多 Provider 调用（DeepSeek / Qwen） | Apache 2.0 |
| [python-docx](https://python-docx.readthedocs.io/) | ≥ 1.1.0 | .docx 文件解析 | MIT |
| [Jinja2](https://jinja.palletsprojects.com/) | ≥ 3.1.0 | Prompt 模板渲染 | BSD |
| [PyYAML](https://pyyaml.org/) | ≥ 6.0.0 | YAML 解析 | MIT |
| [ruamel.yaml](https://yaml.readthedocs.io/) | ≥ 0.18.0 | YAML 格式化输出 | MIT |
| [python-multipart](https://github.com/andrew-d/python-multipart) | ≥ 0.0.18 | multipart/form-data 解析 | Apache 2.0 |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | ≥ 1.0.0 | 环境变量加载 | BSD |

### 前端依赖 (Node.js)

| 库名 | 版本 | 用途 | 许可证 |
|------|------|------|--------|
| [React](https://react.dev/) | ^19.2 | UI 框架 | MIT |
| [Vite](https://vite.dev/) | ^8.0 | 构建工具 | MIT |
| [TypeScript](https://www.typescriptlang.org/) | ~6.0 | 类型系统 | Apache 2.0 |
| [Tailwind CSS](https://tailwindcss.com/) | ^4.3 | 原子化 CSS 框架 | MIT |
| [React Router](https://reactrouter.com/) | ^7.17 | 客户端路由 | MIT |
| [Axios](https://axios-http.com/) | ^1.17 | HTTP 请求库 | MIT |
| [Monaco Editor](https://microsoft.github.io/monaco-editor/) | ^4.7 (React wrapper) | YAML 代码编辑器 | MIT |
| [js-yaml](https://github.com/nodeca/js-yaml) | ^4.2 | YAML 解析与序列化 | MIT |

### 原创性声明

以下为本项目团队自主设计与实现的核心模块，不依赖任何第三方 AI 转换引擎或 SaaS 服务：

| 模块 | 原创内容说明 |
|------|-------------|
| **转换流程引擎** | `pipeline.py` — 从小说解析到剧本生成的 7 阶段完整流水线（分片→逐章分析→跨章汇总→关系提取→场景生成→组装→输出），包含断点续跑机制 |
| **AI Prompt 体系** | `prompts/` 目录下 6 个 Jinja2 模板 — 角色提取、场景检测、对白提取、跨章汇总、关系提取、场景生成，所有 Prompt 均由团队针对中文小说特点独立设计调优 |
| **文本预处理** | `parser.py` / `chunker.py` — 三层正则降级的章节检测、手动章节标注、基于语义的段落边界分片 |
| **跨章去重与关系构建** | `consolidate.py` / `relationship_timeline.py` — 跨章角色别名合并、基于共现数据的关系图构建、时间线排序 |
| **质检系统** | `qa_agent.py` / `reporter.py` — 格式规范性、角色一致性、结构完整性三项检查 + Markdown 质量报告生成 |
| **前端全栈** | 所有 `.tsx` 页面与组件 — 文件上传、进度轮询、Monaco YAML 预览（场景大纲导航）、角色表格（搜索/排序）、剧本结构化编辑器（手风琴表单） |
| **全栈 Docker 部署** | `Dockerfile` × 2 + `docker-compose.yml` + Nginx 配置 — 多阶段构建、SPA 路由、API 反向代理 |

本项目所调用的大语言模型能力（OpenAI 兼容 API）为通用 AI 基础设施，不属于特定第三方产品。项目未使用任何现成的"小说转剧本"商业 SDK 或 SaaS 平台。

---

## API 接口一览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/convert` | 上传小说文件，开始转换 |
| GET | `/api/convert/{task_id}` | 查询任务状态与进度 |
| GET | `/api/convert/{task_id}/download` | 下载转换完成的 YAML 剧本 |
| GET | `/api/convert/{task_id}/report` | 下载转换质量报告 (Markdown) |
| GET | `/api/convert/{task_id}/chapters` | 查看章节识别结果 |
| GET | `/health` | 健康检查 |

---

## License

本项目的原创代码部分遵循 MIT License。引用的第三方库各自遵循其原始许可证。
