# AI 小说转剧本工具 — 开发进度追踪

> 最后更新: 2026-06-06 | 原则: 每个 PR 只做一件事

---

## 状态图例

| 标记 | 含义 |
|:---:|------|
| ⬜ 待开发 | 尚未开始 |
| 🔧 开发中 | 分支已创建, 正在开发 |
| 👀 待审查 | PR 已提交, 等待 Code Review |
| ✅ 已合并 | PR 已合并到 master |
| ⚠️ 已阻塞 | 等待其他 PR 合并或依赖就绪 |

---

## Phase 1: 项目基础设施

| PR | 分支名 | 目标 | 状态 | 依赖 |
|:---|--------|------|:---:|------|
| PR-1 | `pr-01-project-scaffold` | 初始化后端项目骨架 (FastAPI 空应用可启动) | ✅ | — |
| PR-2 | `pr-02-config` | 添加配置模块 (LLM + App 配置, 环境变量读取) | ✅ | PR-1 |
| PR-3 | `pr-03-input-models` | 定义输入数据模型 (NovelChapter, NovelText) | ✅ | PR-1 |
| PR-4 | `pr-04-analysis-models` | 定义分析阶段数据模型 (ChapterAnalysis 等) | ✅ | PR-1 |
| PR-5 | `pr-05-script-models` | 定义汇总与剧本数据模型 (Consolidated, Script) | ✅ | PR-1 |
| PR-6 | `pr-06-prompt-templates` | 添加 5 个 Jinja2 Prompt 模板文件 | ✅ | PR-1 |

---

## Phase 2: 文本预处理

| PR | 分支名 | 目标 | 状态 | 依赖 |
|:---|--------|------|:---:|------|
| PR-7 | `pr-07-txt-parser` | 实现 .txt 章节解析器 (正则 + 降级) | ✅ | PR-3 |
| PR-8 | `pr-08-docx-parser` | 实现 .docx 章节解析器 | ✅ | PR-3, PR-7 |
| PR-9 | `pr-09-token-estimator` | 实现段落归一化与 Token 估算 | ✅ | PR-3 |
| PR-10 | `pr-10-chapter-chunker` | 实现超长章节按段落边界分片 | ✅ | PR-3, PR-9 |

---

## Phase 3: LLM 基础设施

| PR | 分支名 | 目标 | 状态 | 依赖 |
|:---|--------|------|:---:|------|
| PR-11 | `pr-11-llm-client` | 实现 LLM 客户端抽象层 (多 Provider) | 🔧 | PR-2 |
| PR-12 | `pr-12-structured-output` | 实现结构化输出 + Pydantic 校验 + 重试降级 | ⬜ | PR-2, PR-11 |
| PR-13 | `pr-13-prompt-renderer` | 实现 Jinja2 模板渲染封装 | ⬜ | PR-6, PR-11 |

---

## Phase 4: AI 逐章提取 (Stage 2)

| PR | 分支名 | 目标 | 状态 | 依赖 |
|:---|--------|------|:---:|------|
| PR-14 | `pr-14-character-extractor` | 实现角色提取服务 | ⬜ | PR-3, PR-4, PR-13 |
| PR-15 | `pr-15-scene-detector` | 实现场景边界检测服务 | ⬜ | PR-3, PR-4, PR-13 |
| PR-16 | `pr-16-dialogue-extractor` | 实现对白提取服务 | ⬜ | PR-3, PR-4, PR-13 |
| PR-17 | `pr-17-chapter-orchestrator` | 实现逐章分析编排器 (并行提取 + 聚合) | ⬜ | PR-14, PR-15, PR-16 |

---

## Phase 5: AI 汇总去重 (Stage 3)

| PR | 分支名 | 目标 | 状态 | 依赖 |
|:---|--------|------|:---:|------|
| PR-18 | `pr-18-character-merge` | 实现跨章角色去重与别名合并 | ⬜ | PR-4, PR-5, PR-17 |
| PR-19 | `pr-19-relationship-timeline` | 实现角色关系图构建与时间线排序 | ⬜ | PR-5, PR-17, PR-18 |

---

## Phase 6: 剧本生成 (Stage 4)

| PR | 分支名 | 目标 | 状态 | 依赖 |
|:---|--------|------|:---:|------|
| PR-20 | `pr-20-scene-generator` | 实现单场剧本生成 (叙事→剧本格式) | ⬜ | PR-5, PR-19 |
| PR-21 | `pr-21-yaml-writer` | 实现剧本组织与 YAML 序列化输出 | ⬜ | PR-5, PR-20 |

---

## Phase 7: API 接口与任务管理

| PR | 分支名 | 目标 | 状态 | 依赖 |
|:---|--------|------|:---:|------|
| PR-22 | `pr-22-task-manager` | 实现异步任务管理器 (生命周期 + 进度) | ⬜ | PR-1, PR-21 |
| PR-23 | `pr-23-conversion-pipeline` | 实现转换主流程编排 (串联全部阶段) | ⬜ | PR-22, PR-10, PR-17, PR-19, PR-21 |
| PR-24 | `pr-24-post-convert` | 实现 POST /api/convert 上传端点 | ⬜ | PR-23 |
| PR-25 | `pr-25-get-status-download` | 实现 GET 状态查询与 YAML 下载端点 | ⬜ | PR-24 |
| PR-26 | `pr-26-middleware` | 添加全局异常处理、CORS、日志中间件 | ⬜ | PR-24, PR-25 |

---

## Phase 8: CLI 入口

| PR | 分支名 | 目标 | 状态 | 依赖 |
|:---|--------|------|:---:|------|
| PR-27 | `pr-27-cli` | 实现命令行入口 (argparse, 进度显示) | ⬜ | PR-23 |

---

## Phase 9: 测试

| PR | 分支名 | 目标 | 状态 | 依赖 |
|:---|--------|------|:---:|------|
| PR-28 | `pr-28-test-fixtures` | 添加测试夹具 (多规格样本小说) | ⬜ | — |
| PR-29 | `pr-29-parser-chunker-tests` | 添加解析器与分片器单元测试 | ⬜ | PR-7, PR-8, PR-9, PR-10, PR-28 |
| PR-30 | `pr-30-extractor-tests` | 添加提取器与汇总器测试 (Mock LLM) | ⬜ | PR-14~17, PR-28 |
| PR-31 | `pr-31-api-tests` | 添加 API 集成测试 (TestClient) | ⬜ | PR-24~26, PR-28 |

---

## Phase 10: 部署

| PR | 分支名 | 目标 | 状态 | 依赖 |
|:---|--------|------|:---:|------|
| PR-32 | `pr-32-dockerfile` | 实现 Dockerfile (python:3.12-slim) | ⬜ | PR-26 |
| PR-33 | `pr-33-docker-compose` | 实现 docker-compose.yml (一键启动) | ⬜ | PR-32 |

---

## 进度总览

| Phase | PR 范围 | 合计 | 已完成 | 进度 |
|-------|:---:|:---:|:---:|:---:|
| Phase 1 — 项目基础设施 | PR-1 ~ PR-6 | 6 | 6 | 100% |
| Phase 2 — 文本预处理 | PR-7 ~ PR-10 | 4 | 4 | 100% |
| Phase 3 — LLM 基础设施 | PR-11 ~ PR-13 | 3 | 0 | 0% |
| Phase 4 — AI 逐章提取 | PR-14 ~ PR-17 | 4 | 0 | 0% |
| Phase 5 — AI 汇总去重 | PR-18 ~ PR-19 | 2 | 0 | 0% |
| Phase 6 — 剧本生成 | PR-20 ~ PR-21 | 2 | 0 | 0% |
| Phase 7 — API 与任务管理 | PR-22 ~ PR-26 | 5 | 0 | 0% |
| Phase 8 — CLI 入口 | PR-27 | 1 | 0 | 0% |
| Phase 9 — 测试 | PR-28 ~ PR-31 | 4 | 0 | 0% |
| Phase 10 — 部署 | PR-32 ~ PR-33 | 2 | 0 | 0% |
| **V1 小计** | | **33** | **10** | **30%** |

---

---

# ⬇️ 以下为 V2 规划 — V1 全部完成且测试通过后再启动

---

## V2 Phase 11: 存储与持久化

| PR | 分支名 | 目标 | 状态 | 依赖 |
|:---|--------|------|:---:|------|
| PR-34 | `pr-34-sqlite-init` | 初始化 SQLite 数据库 (schema + 连接管理) | ⬜ | V1 完成 |
| PR-35 | `pr-35-project-crud` | 实现项目 CRUD 持久化 | ⬜ | PR-34 |
| PR-36 | `pr-36-task-history` | 实现任务与转换历史持久化 (取代内存 dict) | ⬜ | PR-34, PR-35 |

---

## V2 Phase 12: 输入格式扩展

| PR | 分支名 | 目标 | 状态 | 依赖 |
|:---|--------|------|:---:|------|
| PR-37 | `pr-37-epub-parser` | 实现 EPUB 输入支持 (TOC + 正文提取) | ⬜ | V1 完成 |
| PR-38 | `pr-38-manual-chapter-markers` | 实现手动章节标注 API | ⬜ | V1 完成 |

---

## V2 Phase 13: 质量体系

| PR | 分支名 | 目标 | 状态 | 依赖 |
|:---|--------|------|:---:|------|
| PR-39 | `pr-39-qa-agent` | 实现质检 Agent (格式/角色一致性检查) | ⬜ | V1 完成 |
| PR-40 | `pr-40-quality-report` | 实现转换质量评估报告 | ⬜ | PR-39 |

---

## V2 Phase 14: 动态分片优化

| PR | 分支名 | 目标 | 状态 | 依赖 |
|:---|--------|------|:---:|------|
| PR-41 | `pr-41-semantic-chunker` | 实现动态语义分片优化 | ⬜ | V1 完成 |

---

## V2 Phase 15: 前端基础

| PR | 分支名 | 目标 | 状态 | 依赖 |
|:---|--------|------|:---:|------|
| PR-42 | `pr-42-frontend-init` | 初始化前端项目 (React 18 + TS + Vite + Tailwind) | ⬜ | V1 完成 |
| PR-43 | `pr-43-frontend-types-api` | 定义 TypeScript 类型 + API 调用封装层 | ⬜ | PR-42 |
| PR-44 | `pr-44-upload-progress-page` | 实现文件上传 + 转换进度页面 | ⬜ | PR-43 |
| PR-45 | `pr-45-yaml-preview` | 实现 YAML 在线预览 (Monaco Editor + 大纲导航) | ⬜ | PR-43 |

---

## V2 Phase 16: 前端交互编辑

| PR | 分支名 | 目标 | 状态 | 依赖 |
|:---|--------|------|:---:|------|
| PR-46 | `pr-46-character-graph` | 实现角色列表 + 关系图可视化 | ⬜ | PR-45 |
| PR-47 | `pr-47-script-editor` | 实现剧本结构化在线编辑 + 保存 | ⬜ | PR-45 |
| PR-48 | `pr-48-project-history` | 实现项目列表与历史页面 | ⬜ | PR-45 |

---

## V2 Phase 17: 部署与导出增强

| PR | 分支名 | 目标 | 状态 | 依赖 |
|:---|--------|------|:---:|------|
| PR-49 | `pr-49-frontend-docker` | 实现前端 Docker 集成 (docker-compose 全栈) | ⬜ | PR-48 |
| PR-50 | `pr-50-fountain-export` | 实现导出 Fountain 格式 | ⬜ | V1 完成 |
| PR-51 | `pr-51-fdx-export` | 实现导出 FDX 格式 (Final Draft XML) | ⬜ | PR-50 |

---

## 进度总览

| Phase | PR 范围 | 合计 | 已完成 | 进度 |
|-------|:---:|:---:|:---:|:---:|
| Phase 1 — 项目基础设施 | PR-1 ~ PR-6 | 6 | 0 | 0% |
| Phase 2 — 文本预处理 | PR-7 ~ PR-10 | 4 | 4 | 100% |
| Phase 3 — LLM 基础设施 | PR-11 ~ PR-13 | 3 | 0 | 0% |
| Phase 4 — AI 逐章提取 | PR-14 ~ PR-17 | 4 | 0 | 0% |
| Phase 5 — AI 汇总去重 | PR-18 ~ PR-19 | 2 | 0 | 0% |
| Phase 6 — 剧本生成 | PR-20 ~ PR-21 | 2 | 0 | 0% |
| Phase 7 — API 与任务管理 | PR-22 ~ PR-26 | 5 | 0 | 0% |
| Phase 8 — CLI 入口 | PR-27 | 1 | 0 | 0% |
| Phase 9 — 测试 | PR-28 ~ PR-31 | 4 | 0 | 0% |
| Phase 10 — 部署 | PR-32 ~ PR-33 | 2 | 0 | 0% |
| **V1 小计** | | **33** | **10** | **30%** |
| | | | | |
| Phase 11 — 存储与持久化 | PR-34 ~ PR-36 | 3 | 0 | 0% |
| Phase 12 — 输入格式扩展 | PR-37 ~ PR-38 | 2 | 0 | 0% |
| Phase 13 — 质量体系 | PR-39 ~ PR-40 | 2 | 0 | 0% |
| Phase 14 — 动态分片优化 | PR-41 | 1 | 0 | 0% |
| Phase 15 — 前端基础 | PR-42 ~ PR-45 | 4 | 0 | 0% |
| Phase 16 — 前端交互编辑 | PR-46 ~ PR-48 | 3 | 0 | 0% |
| Phase 17 — 部署与导出增强 | PR-49 ~ PR-51 | 3 | 0 | 0% |
| **V2 小计** | | **18** | **0** | **0%** |
| **总计** | | **51** | **10** | **20%** |

---

## 变更记录

| 日期 | 变更内容 |
|------|----------|
| 2026-06-05 | 初始化进度追踪, V1 规划 33 个 PR, 全部状态为「待开发」 |
| 2026-06-05 | 追加 V2 规划 (Phase 11~17, 共 18 个 PR), V2 待 V1 测试通过后启动 |
| 2026-06-05 | 精简 V2: 移除英文支持、模型扩展(GL M-4.7)、剧本类型参数 |
| 2026-06-06 | PR-5 (汇总与剧本数据模型) 已合并 |
| 2026-06-06 | PR-6 (Jinja2 Prompt 模板) 已合并 |
| 2026-06-06 | PR-7 (.txt 章节解析器) 已合并 |
| 2026-06-06 | PR-8 (.docx 章节解析器) 已合并 |
| 2026-06-06 | PR-9 (段落归一化与 Token 估算) 已合并 |
| 2026-06-06 | PR-10 (超长章节分片) 已合并 |
