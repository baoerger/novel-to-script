# AI 小说转剧本工具 — 开发计划

> 版本: 1.0 | 日期: 2026-06-05 | 原则: 每个 PR 只做一件事

---

## 分支命名规范

- 所有开发分支从 `master` 切出
- 命名格式: `pr-{序号}-{简短描述}`, 如 `pr-01-project-scaffold`
- 每个分支对应一个独立 PR, 合并后删除分支
git commit  →  git push（上传分支）→  gh pr create（创建 PR）→  网页点 Merge  →  git pull
        ↑                                                     ↑
   本地 → GitHub                                          GitHub 服务器上操作
再给出提交命令时要保证这个流程
---

## Phase 1: 项目基础设施 (无依赖)

### PR-1: 初始化后端项目骨架

- **目标**: 搭建 FastAPI 项目目录结构, 可启动的空应用
- **内容**:
  - 创建 `backend/` 目录及所有子目录 (`app/`, `app/models/`, `app/services/`, `app/prompts/`, `tests/`, `tests/fixtures/`, `projects/`)
  - 创建 `backend/app/__init__.py` 和所有子包的 `__init__.py`
  - 创建 `backend/app/main.py` — FastAPI 最小应用 (仅 health check 端点)
  - 创建 `backend/requirements.txt` (FastAPI, uvicorn, pydantic, openai, python-docx, jinja2, pyyaml, python-multipart)
  - 创建 `backend/.env.example` (API Key 模板)
  - 创建 `samples/` 目录占位
  - 确保 `uvicorn main:app --reload` 可启动

### PR-2: 添加配置模块

- **目标**: 集中的配置管理, 支持环境变量覆盖
- **内容**:
  - 创建 `backend/app/config.py`
  - 定义 `LLMConfig` (provider, model, fallback_model, max_retries, temperature, base_url 映射)
  - 定义 `AppConfig` (projects_dir, max_chapters, max_tokens_per_chapter, supported_extensions)
  - 从 `.env` 和环境变量读取 API Key
  - 单例配置访问

### PR-3: 定义输入数据模型

- **目标**: 小说输入层的 Pydantic 模型定义
- **内容**:
  - 创建 `backend/app/models/__init__.py`
  - 创建 `backend/app/models/input.py`
  - 定义 `NovelChapter` (chapter_index, chapter_title, raw_text, paragraph_count, token_estimate)
  - 定义 `NovelText` (title, chapters, total_paragraphs, total_tokens_estimate)

### PR-4: 定义分析阶段数据模型

- **目标**: AI 逐章提取产物的 Pydantic 模型
- **内容**:
  - 创建 `backend/app/models/analysis.py`
  - 定义 `ExtractedCharacter` (name, aliases, role_hint, description, first_appearance_chapter)
  - 定义 `SceneBoundary` (scene_index, summary, location, time_hint, characters_present, start_paragraph, end_paragraph)
  - 定义 `DialogueEntry` (paragraph_index, speaker, raw_text, cleaned_dialogue, stage_direction)
  - 定义 `ChapterAnalysis` (chapter_index, characters, scenes, dialogues, props, locations)

### PR-5: 定义汇总与剧本数据模型

- **目标**: 跨章汇总产物 + 输出剧本的 Pydantic 模型
- **内容**:
  - 创建 `backend/app/models/consolidated.py`
  - 定义 `ConsolidatedCharacter` (id, name, aliases, role, archetype, description, appears_in_chapters, related_props)
  - 定义 `CharacterRelationship` (from_char, to_char, relation, description)
  - 定义 `TimelineScene` (scene_id, source_chapter, location, time_hint, summary, characters)
  - 定义 `ConsolidatedAnalysis` (characters, relationships, timeline, global_locations, global_props)
  - 创建 `backend/app/models/script.py`
  - 定义 `ScriptMeta`, `ScriptCharacter`, `CharacterRelation`, `Setting`, `ContentElement` (type: stage_direction|dialogue|voiceover|transition), `ScriptScene`, `ScriptAct`, `SourceMapping`, `AdaptationNote`, `Script`

### PR-6: 添加 Prompt 模板文件

- **目标**: 所有 LLM Prompt 模板与代码解耦
- **内容**:
  - 创建 `backend/app/prompts/extract_characters.j2`
  - 创建 `backend/app/prompts/extract_scenes.j2`
  - 创建 `backend/app/prompts/extract_dialogues.j2`
  - 创建 `backend/app/prompts/consolidate.j2`
  - 创建 `backend/app/prompts/generate_scene.j2`
  - 每个模板包含角色设定 (系统 Prompt)、输入变量占位、期望输出格式说明

---

## Phase 2: 文本预处理 (依赖 Phase 1 模型)

### PR-7: 实现 .txt 章节解析器

- **目标**: 从 .txt 文件中识别章节边界并分割
- **内容**:
  - 创建 `backend/app/services/parser.py`
  - 实现 `parse_txt(file_path: str) -> NovelText`
  - 正则匹配: `第[零一二三四五六七八九十百千万\d]+章`
  - 降级策略: 匹配到 ≥3 个章节标题则采用, 否则全文作为单章
  - 章节标题提取 + 正文分离
  - 输出 `NovelText` 实例

### PR-8: 实现 .docx 章节解析器

- **目标**: 从 .docx 文件中提取章节文本
- **内容**:
  - 扩展 `backend/app/services/parser.py` 添加 `parse_docx(file_path: str) -> NovelText`
  - 使用 `python-docx` 读取段落
  - 利用 Word 标题样式辅助章节识别
  - 正则降级兜底 (与 .txt 相同)
  - 统一解析入口 `parse_file(file_path: str) -> NovelText` (根据扩展名分发)

### PR-9: 实现段落归一化与 Token 估算

- **目标**: 文本清洗 + Token 数量粗略估算
- **内容**:
  - 创建 `backend/app/services/chunker.py`
  - 实现段落归一化: 多余空行合并, 首尾空白去除, 全角半角统一
  - 实现 `estimate_tokens(text: str) -> int` (中文: 字符数 × 1.5)
  - 补充 `NovelChapter` 的 `paragraph_count` 和 `token_estimate` 字段

### PR-10: 实现超长章节分片

- **目标**: 单章超过 15K tokens 时按段落边界二次切分
- **内容**:
  - 扩展 `backend/app/services/chunker.py`
  - 实现 `split_long_chapter(chapter: NovelChapter, max_tokens: int) -> list[NovelChapter]`
  - 保证不在段落中间切断
  - 分片后子章保留原始章节索引 + 子序号标记
  - 分片摘要记录 (原章 → 子章映射)

---

## Phase 3: LLM 基础设施 (依赖 Phase 1 配置)

### PR-11: 实现 LLM 客户端抽象层

- **目标**: 统一的多 Provider LLM 调用接口
- **内容**:
  - 创建 `backend/app/services/llm.py`
  - 实现 `LLMClient` 类:
    - 支持 DeepSeek / Qwen 两个 Provider (通过 OpenAI SDK 兼容接口)
    - `base_url` 根据 provider 自动切换
    - 统一 `chat(messages, model, temperature, response_format) -> dict` 接口
  - 实现 `get_client(provider: str) -> LLMClient` 工厂方法
  - 从 `LLMConfig` 读取所有参数

### PR-12: 实现结构化输出与重试降级

- **目标**: JSON mode + Pydantic 校验 + 失败重试 + 模型降级
- **内容**:
  - 扩展 `backend/app/services/llm.py`
  - 实现 `structured_call(prompt_template, variables, pydantic_model, max_retries=3) -> BaseModel`:
    1. 渲染 Jinja2 模板
    2. 调用 LLM (JSON mode)
    3. Pydantic 校验输出
    4. 失败 → 将校验错误注入 Prompt → 重试 (最多 3 次)
    5. 3 次均失败 → 切换到 fallback_model → 重试 1 次
    6. 仍失败 → 抛异常 (上层标记本章失败)
  - 记录降级事件到日志

### PR-13: 实现 Prompt 渲染工具

- **目标**: Jinja2 模板加载与渲染封装
- **内容**:
  - 扩展 `backend/app/services/llm.py`
  - 实现 `render_prompt(template_name: str, variables: dict) -> list[dict]`
  - 自动加载 `prompts/` 目录下的 `.j2` 文件
  - 渲染为 OpenAI 兼容的 messages 格式 (system + user)
  - Jinja2 环境缓存 (避免每次读取文件)

---

## Phase 4: AI 逐章提取 — Stage 2 (依赖 Phase 1-3)

### PR-14: 实现角色提取服务

- **目标**: 从单章文本中提取角色信息
- **内容**:
  - 创建 `backend/app/services/extractor.py`
  - 实现 `extract_characters(chapter: NovelChapter) -> list[ExtractedCharacter]`
  - 使用 `extract_characters.j2` 模板
  - 调用 `structured_call` → 返回 `list[ExtractedCharacter]`
  - 失败时记录错误并返回空列表 (不阻塞流程)

### PR-15: 实现场景边界检测服务

- **目标**: 从单章文本中识别场景切换点
- **内容**:
  - 扩展 `backend/app/services/extractor.py`
  - 实现 `extract_scenes(chapter: NovelChapter) -> list[SceneBoundary]`
  - 使用 `extract_scenes.j2` 模板
  - 调用 `structured_call` → 返回 `list[SceneBoundary]`
  - 验证 `start_paragraph` / `end_paragraph` 不超出章节范围

### PR-16: 实现对白提取服务

- **目标**: 从单章文本中识别对白及其归属
- **内容**:
  - 扩展 `backend/app/services/extractor.py`
  - 实现 `extract_dialogues(chapter: NovelChapter) -> list[DialogueEntry]`
  - 使用 `extract_dialogues.j2` 模板
  - 调用 `structured_call` → 返回 `list[DialogueEntry]`

### PR-17: 实现逐章分析编排器

- **目标**: 协调三个提取服务, 单章并行执行, 聚合结果
- **内容**:
  - 扩展 `backend/app/services/extractor.py`
  - 实现 `analyze_chapter(chapter: NovelChapter) -> ChapterAnalysis`
  - 三个提取服务并行调用 (asyncio.gather)
  - 聚合为 `ChapterAnalysis` 实例
  - 单章分析失败不阻塞后续章节
  - 实现 `analyze_all_chapters(novel: NovelText) -> list[ChapterAnalysis]`
  - 记录每章分析状态 (成功/失败/降级)

---

## Phase 5: AI 汇总去重 — Stage 3 (依赖 Phase 4)

### PR-18: 实现跨章角色去重与别名合并

- **目标**: 跨章节合并同一角色的不同出现
- **内容**:
  - 创建 `backend/app/services/consolidator.py`
  - 实现 `merge_characters(analyses: list[ChapterAnalysis]) -> list[ConsolidatedCharacter]`
  - AI 辅助判断: 将全部 `ExtractedCharacter` 汇总, 调用 `consolidate.j2` 模板
  - 生成唯一 ID (`CHAR_001` 格式)
  - 别名归并 + 跨章描述综合
  - 角色分类 (protagonist/antagonist/supporting/minor)
  - 记录每个角色出现在哪些章节

### PR-19: 实现关系图构建与时间线排序

- **目标**: 角色关系网络 + 场景时间线
- **内容**:
  - 扩展 `backend/app/services/consolidator.py`
  - 实现 `build_relationships(characters, analyses) -> list[CharacterRelationship]`
  - 实现 `build_timeline(analyses) -> list[TimelineScene]`
  - AI 从汇总的角色和场景中推断关系类型
  - 场景按时间/逻辑顺序排序
  - 聚合全局地点和道具列表
  - 实现 `consolidate(analyses: list[ChapterAnalysis]) -> ConsolidatedAnalysis` 总入口

---

## Phase 6: 剧本生成 — Stage 4 (依赖 Phase 5)

### PR-20: 实现单场剧本生成

- **目标**: 将场景摘要 + 对白转换为剧本格式内容
- **内容**:
  - 创建 `backend/app/services/generator.py`
  - 实现 `generate_scene_content(timeline_scene, characters, chapter_text) -> list[ContentElement]`
  - 使用 `generate_scene.j2` 模板
  - AI 将叙事性描述 → 舞台说明 (stage_direction)
  - AI 将对白 → 标准对白格式 (dialogue + character + delivery)
  - 识别内心独白 → voiceover 类型
  - 场间衔接 → transition 类型
  - 实现 `generate_all_scenes(timeline, characters, chapters) -> list[list[ContentElement]]`
  - 逐场调用 AI, 单场失败不阻塞其余场次

### PR-21: 实现剧本组织与 YAML 序列化

- **目标**: 将生成的场景组装为 Act→Scene 结构并输出 YAML
- **内容**:
  - 扩展 `backend/app/services/generator.py`
  - 实现 `organize_acts(scene_contents, timeline, characters, relationships) -> list[ScriptAct]`
  - 场景按 timeline 顺序归入 Act (简单策略: 每 5-8 场一幕)
  - 创建 `backend/app/services/yaml_writer.py`
  - 实现 `script_to_yaml(script: Script) -> str`
  - 实现 `write_yaml_file(script: Script, output_path: str)`
  - YAML 输出包含 `meta`, `characters`, `character_relationships`, `acts`, `source_mapping`, `adaptation_notes`
  - 使用 `ruamel.yaml` 保证中文兼容 + 美观格式

---

## Phase 7: API 接口与任务管理 (依赖 Phase 6)

### PR-22: 实现异步任务管理器

- **目标**: 管理转换任务的全生命周期状态
- **内容**:
  - 创建 `backend/app/tasks.py`
  - 实现 `TaskManager` 类:
    - `create_task(file_path, title) -> task_id` (生成 UUID)
    - `get_task(task_id) -> TaskStatus`
    - 状态机: `pending → preprocessing → extracting → consolidating → generating → completed | failed`
  - 进度追踪: `{stage, chapter_done, chapter_total, percent}`
  - 任务结果存储 (内存 dict, V1 无持久化)

### PR-23: 实现转换主流程编排

- **目标**: 串联全部处理阶段的后台任务
- **内容**:
  - 扩展 `backend/app/tasks.py`
  - 实现 `run_conversion(task_id, file_path, title)`:
    1. 预处理: 解析文件 → 分章 → Token 估算 → 超长分片
    2. 提取: 逐章 AI 分析 (并行)
    3. 汇总: 角色去重 + 关系 + 时间线
    4. 生成: 逐场剧本生成
    5. 序列化: YAML 写入 → 结果存入 TaskManager
  - 每个阶段完成后更新 task 进度
  - 使用 FastAPI `BackgroundTasks` 异步执行

### PR-24: 实现 POST /api/convert 端点

- **目标**: 文件上传 → 触发转换
- **内容**:
  - 扩展 `backend/app/main.py`
  - `POST /api/convert`:
    - 接收 `multipart/form-data` (file + title)
    - 校验文件扩展名 (.txt / .docx)
    - 校验文件大小 (上限 10MB)
    - 保存到 `projects/{task_id}/` 目录
    - 创建任务 → 投递 BackgroundTasks
    - 返回 `{task_id, status: "pending"}`

### PR-25: 实现 GET 查询与下载端点

- **目标**: 查询转换进度 + 下载 YAML
- **内容**:
  - 扩展 `backend/app/main.py`
  - `GET /api/convert/{task_id}`:
    - 返回任务状态、进度百分比、当前阶段
    - 任务不存在 → 404
  - `GET /api/convert/{task_id}/download`:
    - 任务未完成 → 409
    - 任务完成 → 返回 YAML 文件 (Content-Disposition: attachment)
    - 设置正确的 MIME type (`application/x-yaml`)

### PR-26: 添加 FastAPI 全局中间件与错误处理

- **目标**: 统一的异常处理、CORS、日志
- **内容**:
  - 添加全局异常处理器 (500 → JSON)
  - 添加 CORS 中间件 (V1 允许所有来源, V2 收紧)
  - 添加请求日志中间件
  - 添加文件大小限制验证

---

## Phase 8: CLI 入口 (依赖 Phase 7)

### PR-27: 实现命令行入口

- **目标**: 终端一行命令完成转换
- **内容**:
  - 创建 `backend/app/cli.py`
  - 使用 `argparse`:
    - `--input` / `-i`: 输入文件路径 (必填)
    - `--output` / `-o`: 输出 YAML 路径 (可选, 默认 `./output.yaml`)
    - `--title`: 书名 (可选, 默认从文件名推断)
    - `--verbose` / `-v`: 显示详细进度
  - 内部调用 `run_conversion()` 同步等待完成
  - 进度条显示 (tqdm 或简单文本进度)
  - 转换报告: 角色数 / 场次数 / 耗时 / Token 用量

---

## Phase 9: 测试 (贯穿全流程)

### PR-28: 添加测试夹具 (Fixtures)

- **目标**: 提供可复用的测试数据
- **内容**:
  - 创建 `tests/fixtures/sample_short.txt` (3 章, 每章 ~500 字)
  - 创建 `tests/fixtures/sample_medium.txt` (10 章, 每章 ~1000 字)
  - 创建 `tests/fixtures/sample_long_chapter.txt` (单章 >15K tokens)
  - 创建 `tests/fixtures/sample_no_chapters.txt` (无章节标题, 测试降级)
  - 创建 `tests/fixtures/sample.docx` (3 章 Word 文档)
  - 创建 `conftest.py` (共享 fixtures: Mock LLM client, 示例 NovelText)

### PR-29: 添加解析器与分片器测试

- **目标**: 验证文本预处理正确性
- **内容**:
  - 创建 `tests/test_parser.py`
  - 测试: 标准章节目录识别 / 中文数字章节 / 无章节降级 / 空文件 / .docx 解析
  - 创建 `tests/test_chunker.py`
  - 测试: 段落归一化 / Token 估算 / 短章不分片 / 超长章正确切分 / 段落边界不切断

### PR-30: 添加提取器与汇总器测试

- **目标**: 验证 AI 服务层逻辑 (Mock LLM)
- **内容**:
  - 创建 `tests/test_extractor.py`
  - 测试: Mock LLM 返回 → Pydantic 校验通过 / 校验失败重试 / 降级触发 / 空角色列表
  - 创建 `tests/test_consolidator.py` (如适用)

### PR-31: 添加 API 集成测试

- **目标**: 端到端验证 API 接口
- **内容**:
  - 使用 `fastapi.testclient.TestClient`
  - 测试: POST 上传文件 → 200 + task_id / 无效格式 → 400
  - 测试: GET 状态查询 → 正确返回进度 / 不存在 task_id → 404
  - 测试: GET 下载 → 未完成 → 409 / 完成 → YAML 文件
  - 测试: 最小化端到端 (上传 sample_short.txt → 等待完成 → 下载验证)

---

## Phase 10: 部署 (依赖 Phase 7)

### PR-32: 实现 Dockerfile

- **目标**: 后端可单容器运行
- **内容**:
  - 创建 `backend/Dockerfile`
  - 基于 `python:3.12-slim`
  - 安装依赖 → 复制源码 → 暴露 8000 端口
  - CMD: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
  - `.dockerignore` 排除 `projects/`, `tests/`, `__pycache__/`

### PR-33: 实现 docker-compose.yml

- **目标**: 一键启动完整环境
- **内容**:
  - 创建 `docker-compose.yml` (项目根目录)
  - 定义 `backend` 服务 (build + ports + env_file + volumes)
  - 挂载 `projects/` 目录到宿主机 (持久化输出)
  - 可选: 添加 `frontend` 服务占位 (V2)

---

## 依赖关系总览

```
Phase 1 (PR-1~6): 基础设施 ─────────────────────────┐
        │                                            │
        ├── PR-1 项目骨架 (最先)                     │
        ├── PR-2 配置     (独立)                     │
        ├── PR-3 输入模型 (独立)                     │
        ├── PR-4 分析模型 (独立)                     │
        ├── PR-5 剧本模型 (独立)                     │
        └── PR-6 Prompt  (独立)                     │
                                                     │
Phase 2 (PR-7~10): 文本处理 ────────────────────────┤
        ├── PR-7  .txt 解析  (依赖 PR-3)            │
        ├── PR-8  .docx 解析 (依赖 PR-3, PR-7)      │
        ├── PR-9  Token 估算 (依赖 PR-3)            │
        └── PR-10 超长分片  (依赖 PR-3, PR-9)       │
                                                     │
Phase 3 (PR-11~13): LLM 层 ─────────────────────────┤
        ├── PR-11 LLM 客户端   (依赖 PR-2)          │
        ├── PR-12 结构化输出   (依赖 PR-2, PR-11)   │
        └── PR-13 Prompt 渲染  (依赖 PR-6, PR-11)   │
                                                     │
Phase 4 (PR-14~17): AI 提取 ────────────────────────┤
        ├── PR-14 角色提取    (依赖 PR-3,4, PR-13)  │
        ├── PR-15 场景检测    (依赖 PR-3,4, PR-13)  │
        ├── PR-16 对白提取    (依赖 PR-3,4, PR-13)  │
        └── PR-17 编排器      (依赖 PR-14~16)       │
                                                     │
Phase 5 (PR-18~19): 汇总 ───────────────────────────┤
        ├── PR-18 角色去重    (依赖 PR-4,5, PR-17)  │
        └── PR-19 关系/时间线 (依赖 PR-5, PR-17,18) │
                                                     │
Phase 6 (PR-20~21): 剧本生成 ───────────────────────┤
        ├── PR-20 场景生成    (依赖 PR-5, PR-19)    │
        └── PR-21 YAML 输出   (依赖 PR-5, PR-20)    │
                                                     │
Phase 7 (PR-22~26): API ────────────────────────────┤
        ├── PR-22 任务管理    (依赖 PR-1, PR-21)    │
        ├── PR-23 转换编排    (依赖 PR-22, PR-21)   │
        ├── PR-24 POST 端点   (依赖 PR-23)          │
        ├── PR-25 GET 端点    (依赖 PR-24)          │
        └── PR-26 中间件      (依赖 PR-24,25)       │
                                                     │
Phase 8 (PR-27): CLI ───────────────────────────────┤
        └── PR-27 CLI 入口    (依赖 PR-23)          │
                                                     │
Phase 9 (PR-28~31): 测试 ───────────────────────────┤
        ├── PR-28 Fixtures    (独立, 尽早做)        │
        ├── PR-29 Parser/Chunker 测试 (依赖 PR-7~10)│
        ├── PR-30 Extractor 测试    (依赖 PR-14~17) │
        └── PR-31 API 测试          (依赖 PR-24~26) │
                                                     │
Phase 10 (PR-32~33): 部署 ──────────────────────────┘
        ├── PR-32 Dockerfile    (依赖 PR-26)        │
        └── PR-33 Docker Compose (依赖 PR-32)       │
```

---

## 建议开发顺序

1. **第一轮 (并行)**: PR-1 (骨架) → PR-2, PR-3, PR-4, PR-5, PR-6 可并行
2. **第二轮**: PR-7 → PR-8, PR-9 → PR-10
3. **第三轮**: PR-11 → PR-12, PR-13
4. **第四轮**: PR-14, PR-15, PR-16 可并行 → PR-17
5. **第五轮**: PR-18 → PR-19
6. **第六轮**: PR-20 → PR-21
7. **第七轮**: PR-22 → PR-23 → PR-24 → PR-25 → PR-26
8. **第八轮**: PR-27
9. **第九轮**: PR-28 尽早 → PR-29, PR-30, PR-31 (跟随对应模块)
10. **第十轮**: PR-32 → PR-33

预计 V1 PR 数: **33 个**, 预计总开发周期: **3-5 天** (部分 PR 极微, 可一天多合)

---

---

# ⬇️ 以下为 V2 规划 — V1 全部完成且测试通过后再启动

> V2 不设时间线, V1 跑通后根据实际情况决定取舍和优先级。

---

## V2 Phase 11: 存储与持久化 (依赖 V1 Phase 7)

### PR-34: 初始化 SQLite 数据库

- **目标**: 引入本地持久化, 替代 V1 的内存存储
- **内容**:
  - 添加 `sqlite3` / `aiosqlite` 依赖
  - 创建 `backend/app/db.py` — 数据库连接管理
  - 定义 Schema: `projects`, `tasks`, `conversion_history` 三张表
  - 数据库初始化 + 迁移脚本 (简单的 `schema.sql`)
  - 数据库文件路径: `./data/app.db` (可配置)

### PR-35: 实现项目 CRUD 持久化

- **目标**: 用户可以查看和管理历史转换项目
- **内容**:
  - 创建 `backend/app/services/project_store.py`
  - 项目模型: `id`, `title`, `source_file`, `status`, `created_at`, `updated_at`
  - CRUD 操作: 创建项目 / 列表查询 / 单个查询 / 删除 (级联删除任务和文件)
  - 替换 V1 内存 dict 存储

### PR-36: 实现任务与转换历史持久化

- **目标**: 转换任务重启后不丢失
- **内容**:
  - 创建 `backend/app/services/task_store.py`
  - 任务模型: `id`, `project_id`, `status`, `progress`, `result_path`, `error_message`, `created_at`
  - 历史记录: 每次转换的时间、耗时、Token 用量、成功/失败
  - 重构 `TaskManager` — 从内存 dict 切换到 SQLite

---

## V2 Phase 12: 输入格式扩展 (依赖 V1 Phase 2)

### PR-37: 实现 EPUB 输入支持

- **目标**: 支持 .epub 电子书格式上传
- **内容**:
  - 添加 `ebooklib` 或 `epub2text` 依赖
  - 扩展 `backend/app/services/parser.py` 添加 `parse_epub()`
  - 利用 EPUB 内置 TOC/NCX 提取章节结构
  - 正文 HTML → 纯文本转换
  - 无 TOC 时降级到正则章节识别
  - 更新 `POST /api/convert` 接受 `.epub` 扩展名

### PR-38: 实现手动章节标注 API

- **目标**: 正则识别失败时, 允许用户手动指定章节边界
- **内容**:
  - 扩展 `POST /api/convert` 接受可选 `chapter_markers` 参数
  - 两种标注方式: (a) 分隔符字符串列表, (b) 行号范围 JSON
  - API 返回章节预览供确认: `GET /api/convert/{task_id}/chapters`
  - 确认后继续转换流程

---

## V2 Phase 13: 质量体系 (依赖 V1 Phase 6)

### PR-39: 实现质检 Agent

- **目标**: 自动检查生成剧本的格式规范性和内容一致性
- **内容**:
  - 创建 `backend/app/services/qa_agent.py`
  - 检查项:
    - 格式规范: 每场必须有至少一个 content 元素 / 对话必须有 speaker
    - 角色一致性: 出场角色都在 character 清单中 / 对白角色无幽灵角色
    - 结构完整性: source_mapping 覆盖所有场景
  - 输出 `QAResult` (errors, warnings, suggestions)
  - 质检不通过 → 在 `adaptation_notes` 中标注
  - 不影响剧本输出 (仅标注, 不阻塞)

### PR-40: 实现转换质量评估报告

- **目标**: 每次转换生成可读的质量报告
- **内容**:
  - 创建 `backend/app/services/reporter.py`
  - 报告内容:
    - 转换概览: 章节数 / 角色数 / 场次数 / 对白数 / 总耗时 / Token 用量 / API 成本
    - 质量指标: 质检通过率 / 角色覆盖率 / 场景粒度分布
    - 降级事件记录: 哪些章/场触发了模型降级
    - 建议: 基于质检结果给出修改建议
  - 输出 Markdown 格式报告文件
  - API: `GET /api/convert/{task_id}/report` 返回报告

---

## V2 Phase 14: 动态分片优化 (依赖 V1 Phase 2)

### PR-41: 实现动态语义分片

- **目标**: 优化超长章节的分片质量, 避免语义断裂
- **内容**:
  - 扩展 `backend/app/services/chunker.py`
  - 添加 `semantic_split()` 方法:
    - 计算相邻段落的语义相似度 (可选轻量嵌入模型或启发式)
    - 在相似度最低的段落边界切分 (即主题切换点)
  - 降级: 嵌入模型不可用时回退到 V1 的固定阈值分片
  - 仅对 >15K tokens 的章启用, 小章不变

---

## V2 Phase 15: 前端基础 (依赖 V1 Phase 7 全部 API)

### PR-42: 初始化前端项目

- **目标**: 搭建 React 前端骨架, 可启动的开发环境
- **内容**:
  - 使用 Vite 创建 React 18 + TypeScript 项目
  - 安装依赖: `react-router-dom`, `axios`, `@monaco-editor/react`, `tailwindcss`
  - 配置 Tailwind CSS + PostCSS
  - 目录结构: `components/`, `pages/`, `services/`, `types/`, `hooks/`
  - 基础布局组件: Header, Footer, Layout
  - 前端开发服务器可启动 (端口 5173)

### PR-43: 定义 TypeScript 类型 + API 调用层

- **目标**: 前端类型与后端 Pydantic 模型对齐
- **内容**:
  - 创建 `frontend/src/types/` — 所有 TS 接口 (与 backend models 对齐)
    - `NovelChapter`, `NovelText`, `ChapterAnalysis`, `ConsolidatedAnalysis`
    - `Script`, `ScriptScene`, `ScriptAct`, `ContentElement`
  - 创建 `frontend/src/services/api.ts`
    - `uploadFile(file, title) → task_id`
    - `getTaskStatus(task_id) → TaskStatus`
    - `downloadScript(task_id) → Blob`
  - Axios 实例配置 (baseURL, 超时, 错误拦截)

### PR-44: 实现文件上传 + 转换进度页面

- **目标**: 核心交互: 上传小说 → 看进度 → 下载
- **内容**:
  - 创建 `frontend/src/pages/ConvertPage.tsx`
  - 拖拽/点击上传区域 (支持 .txt / .docx)
  - 上传后自动触发转换, 显示进度条
  - 轮询 `GET /api/convert/{task_id}` 更新进度
  - 阶段中文映射: `extracting` → "正在分析角色与场景..."
  - 完成后显示 "下载 YAML" 按钮
  - 错误状态展示 + 重试按钮

### PR-45: 实现 YAML 在线预览

- **目标**: 在浏览器中预览生成的 YAML 剧本
- **内容**:
  - 创建 `frontend/src/pages/PreviewPage.tsx`
  - 集成 Monaco Editor (只读模式, YAML 语法高亮)
  - 从 API 获取 YAML 内容并加载到编辑器
  - 大纲视图: 左侧目录树 (Act → Scene 导航)
  - 点击目录项跳转到对应 YAML 位置
  - 复制 / 下载按钮

---

## V2 Phase 16: 前端交互编辑 (依赖 Phase 15)

### PR-46: 实现角色列表与关系图

- **目标**: 可视化角色管理
- **内容**:
  - 创建 `frontend/src/pages/CharactersPage.tsx`
  - 角色卡片列表: 头像占位 / 名称 / 别名 / 角色定位 / 出场章节
  - 角色搜索 + 筛选 (按 role 类型: protagonist/antagonist/supporting/minor)
  - 简单关系图: 力导向图 (d3-force 或 vis-network) — 节点=角色, 边=关系
  - 点击角色高亮其关系和出场场景

### PR-47: 实现剧本结构化编辑 + 保存

- **目标**: 在 Web 端直接编辑剧本
- **内容**:
  - 创建 `frontend/src/pages/EditorPage.tsx`
  - 场景卡片视图: 每场一个卡片, 展开显示 content 列表
  - 拖拽排序: 场景可拖拽调整顺序
  - 内联编辑: 点击文本进入编辑模式, 失焦自动保存
  - 角色选择器: 对白的 character 字段下拉选择
  - "保存" 按钮 → 写回 YAML → 触发下载
  - "新建场景" / "删除场景" 按钮

### PR-48: 实现项目列表与历史页面

- **目标**: 用户可查看和管理所有历史转换
- **内容**:
  - 创建 `frontend/src/pages/ProjectsPage.tsx`
  - 项目卡片网格: 书名 / 转换时间 / 状态 / 角色数+场次数摘要
  - 排序: 按时间 / 按书名
  - 搜索: 按书名模糊搜索
  - 点击进入 → 预览页 / 编辑页
  - 删除确认弹窗

---

## V2 Phase 17: 部署与导出增强 (依赖 Phase 16)

### PR-49: 实现前端 Docker 集成

- **目标**: 前后端一键 docker-compose 启动
- **内容**:
  - 创建 `frontend/Dockerfile` (多阶段构建: build → nginx)
  - 创建 `frontend/nginx.conf` (反向代理 API 到 backend:8000)
  - 更新 `docker-compose.yml`:
    - `backend` 服务 (已有)
    - `frontend` 服务 (新增, 端口 80)
  - 开发模式: docker-compose 挂载源码卷, 支持热重载
  - 生产模式: 多阶段构建, nginx 静态托管

### PR-50: 实现导出 Fountain 格式

- **目标**: 与行业标准剧本格式互通
- **内容**:
  - 创建 `backend/app/services/fountain_writer.py`
  - Script → Fountain 文本转换规则:
    - Scene heading → `INT./EXT. LOCATION - TIME`
    - Character → 居左大写
    - Dialogue → 紧随角色行
    - Stage direction → 普通段落
    - Transition → 右对齐, 如 `CUT TO:`
  - API: `GET /api/convert/{task_id}/download?format=fountain`
  - 新增 `POST /api/export` — 任意 YAML 剧本 → Fountain (不上传小说)

### PR-51: 实现导出 FDX 格式

- **目标**: 与 Final Draft 行业标准互通
- **内容**:
  - 创建 `backend/app/services/fdx_writer.py`
  - Script → FDX XML 转换:
    - 遵循 Final Draft XML 规范 (Paragraph, SceneProperties, etc.)
  - API: `GET /api/convert/{task_id}/download?format=fdx`
  - `POST /api/export` 支持 FDX

---

## V2 依赖关系总览

```
V1 全部完成 (PR-1~33)
        │
        ├── V2 Phase 11 (PR-34~36): 存储持久化 ────── 可独立启动
        │
        ├── V2 Phase 12 (PR-37~38): 输入格式扩展 ──── 依赖 V1 Phase 2
        │
        ├── V2 Phase 13 (PR-39~40): 质量体系 ──────── 依赖 V1 Phase 6
        │
        ├── V2 Phase 14 (PR-41): 动态分片 ─────────── 依赖 V1 Phase 2
        │
        ├── V2 Phase 15 (PR-42~45): 前端基础 ──────── 依赖 V1 Phase 7
        │
        ├── V2 Phase 16 (PR-46~48): 前端交互 ──────── 依赖 V2 Phase 15
        │
        └── V2 Phase 17 (PR-49~51): 部署导出 ──────── 依赖 V2 Phase 15, 16
```

---

## 总体统计

| 版本 | Phase 范围 | PR 数 |
|------|-----------|:---:|
| V1 | Phase 1 ~ 10 | 33 |
| V2 | Phase 11 ~ 17 | 18 |
| **合计** | | **51** |
