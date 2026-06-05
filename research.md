# AI 小说转剧本工具 — 市场与技术调研报告

> 调研时间：2026-06-05
> 调研范围：现有产品、技术方案、行业标准、工具链

---

## 目录

1. [现有产品与竞品分析](#1-现有产品与竞品分析)
2. [剧本格式标准对比](#2-剧本格式标准对比)
3. [核心技术方案参考](#3-核心技术方案参考)
4. [长文本处理策略（论文级）](#4-长文本处理策略)
5. [中文 NLP 工具链](#5-中文-nlp-工具链)
6. [LLM 结构化输出方案](#6-llm-结构化输出方案)
7. [小说文件解析库](#7-小说文件解析库)
8. [综合对比与推荐](#8-综合对比与推荐)
9. [市场空白与我们的定位](#9-市场空白与我们的定位)

---

## 1. 现有产品与竞品分析

### 1.1 开源工具

| 工具 | 语言/框架 | 核心能力 | 输出格式 | Star/活跃度 |
|------|----------|----------|----------|-------------|
| **[InfinityCN](https://github.com/Pushyanth02/InfinityCN)** | React 19 + TypeScript | 小说→电影化阅读体验，SFX/Pause/Cut 标注，情感追踪，7 种 AI Provider | 自定义 JSON | 活跃开发中 (v15.0.0) |
| **[Dramatron](https://github.com/google-deepmind/dramatron)** | Python | DeepMind 出品，分层级剧本生成（Log Line → Title → Characters → Plot → Dialogue），人机协同 | Fountain 格式 | ⭐ 1k+ |
| **[Toonflow](https://github.com/JamStrak/Toonflow-app-jam)** | Python + React | 小说→剧本→分镜→视频全流程，三 Agent 协作，支持短剧/漫剧 | 内部格式 → 视频 | 活跃 |
| **[S-Drama](https://github.com/feirate/S-Drama)** | Python | 短剧引擎，Markdown/Word 剧本解析→动画生成，风格自动识别 | JSON 动画数据 | 活跃 |
| **[Openframe](https://github.com/murongg/openframe)** | TypeScript | AI 漫剧创作工作台，人物关系图，导出 FCPXML/EDL | FCPXML/EDL | 2026.3 更新 |
| **[AI-Shotlive](https://github.com/sorker/ai-shotlive)** | Python (前后端分离) | 小说→剧本→分镜→视频全流程，多模型支持（DeepSeek/豆包/通义/可灵） | 集成格式 | 活跃 |
| **[Seedance2-Storyboard](https://github.com/liangdabiao/Seedance2-Storyboard-Generator)** | Claude Code Skill | 基于 Claude Agent SDK，小说→四幕剧本→分镜脚本 | 分镜脚本 | 新增 |

### 1.2 商业产品

| 产品 | 开发方 | 定位 | 特色 |
|------|--------|------|------|
| **LivingWriter** | LivingWriter Inc. | 在线写作平台 | 内置 AI Convert to Screenplay 功能，一键转换章/全书 |
| **中文逍遥** | 中文在线集团 | 网文创作大模型 | 2025 年接入 DeepSeek，已用于短剧剧本量产，2026 出海至 FlareFlow |
| **橙星梦工厂** | 风行在线 × 阿里云 | AI 漫剧平台 | 40 万+分镜模板，编剧-导演-分镜-视频智能体协作，AI 漫剧播放量超 10 亿 |
| **纳逗 Pro** | 爱奇艺 | AI 全流程影视平台 | 近 70 个 AI Agent，一键小说转剧本 + 剧本评估 |
| **AI小说写作专家** | 苏州热风科技 | 手机 App | 小说转剧本、改写/扩写/仿写，2026.5 更新 |
| **量子探险** | 南京海豚元沣 | 创作工具 App | 小说/漫剧/短剧/剧本杀一站式，AI 消痕技术 |
| **墨客大模型** | 浙江博采传媒 | 大模型平台 | 浙江省"人工智能+文化"重点模型，聚焦影视剧本/网络小说 |

### 1.3 npm/PyPI 小工具

| 工具 | 平台 | 特色 |
|------|------|------|
| **[ai-scriptify](https://www.npmjs.com/package/ai-scriptify)** | npm | CLI 工具，8 步工作流 (/spec→/idea→/outline→/characters→/scene→/script→/polish→/export)，4 种漫剧风格，6 维质量检查 |
| **[dramatts](https://pypi.org/project/dramatts/)** | PyPI | Python 剧本处理库 |
| **FilmBuff** | npm | 60+ 电影风格模板，18+ 类型模块，镜头列表生成 |

### 1.4 竞品关键发现

1. **YAML 方案几乎无人采用** — 所有已调研的开源和商业工具都没有使用 YAML 作为剧本输出格式。ScreenJSON 用的是 JSON，Dramatron 用的是 Fountain，商业工具多为私有格式。我们的 YAML Schema 方案是有差异化的。
2. **全流程化是趋势** — 主流工具都在做"小说→剧本→分镜→视频"的完整链路，纯粹的"小说→剧本"转换工具反而稀缺。
3. **短剧/漫剧是最大需求场景** — 2025-2026 年，AI 短剧和 AI 漫剧是中英文市场最大的剧本消费场景。
4. **多模型支持成标配** — 优质开源项目普遍支持 5+ 个 AI Provider。

---

## 2. 剧本格式标准对比

### 2.1 现有工业标准

| 标准 | 格式 | 设计目的 | 人类可读 | 机器可处理 | YAML 可兼容 |
|------|------|----------|:---:|:---:|:---:|
| **Fountain** | 纯文本标记 | 剧本写作中的快速输入 | ✅ | ⚠️ 需解析器 | ❌ |
| **Final Draft (FDX)** | XML | 行业标准剧本编辑 | ❌ | ✅ | ❌ |
| **ScreenJSON** | JSON | 剧本数据分析与交换 | ⚠️ | ✅ | ✅ 可等价 |
| **YAML (本方案)** | YAML | 剧本转换+编辑 | ✅ | ✅ | ✅ |

### 2.2 ScreenJSON 核心结构（最接近我们目标的工业标准）

```
Container → Document → Scene → Element
                           ├── action
                           ├── character (说话人标识)
                           ├── dialogue (对白)
                           ├── parenthetical (表演提示)
                           ├── transition (转场)
                           ├── shot (镜头)
                           └── general (通用)
```

ScreenJSON 的 Scene→Element 设计很好地抽象了剧本元素的多样性，我们的 YAML Schema 在 `content` 数组中采用了类似的多态设计（stage_direction / dialogue / voiceover / transition）。

### 2.3 为什么选 YAML 而非 JSON/Fountain/FDX

| 对比维度 | YAML | JSON (ScreenJSON) | Fountain | FDX |
|----------|------|-------------------|----------|-----|
| 人类直接编辑 | ★★★★★ | ★★★ | ★★★★ | ★ |
| 程序解析 | ★★★★ | ★★★★★ | ★★ | ★★★★ |
| 中文友好 | ★★★★★ | ★★★★★ | ★★★ | ★★★ |
| 行业接受度 | 低（新） | 低（新） | 中 | 高 |
| 嵌套可读性 | ★★★★★ | ★★★ | ★ | ★★ |
| 可注释 | ★★★★★ | ☆ | ★★★★ | ★★ |

**结论**：YAML 的"人类可编辑+机器可处理+可注释"三点组合是剧本编辑场景的最佳匹配。工业标准（Fountain/FDX）偏重排版而非数据结构，ScreenJSON 虽有结构但 JSON 格式对人类编辑不友好。

---

## 3. 核心技术方案参考

### 3.1 Dramatron 分层生成架构（DeepMind）

Dramatron 是该领域最权威的学术参考（NeurIPS 2022），其核心理念是**层级化生成**：

```
Log Line → Title → Characters → Plot/Scenes → Location Descriptions → Dialogue
```

**关键设计**：
- 每层输出作为下一层的 prompt 上下文（prompt chaining）
- 每个 NamedTuple 有 `to_string()` / `from_string()` 方法保证可序列化
- 人类可在任一层介入编辑，修改向下传播
- 用 `<end>` 标记防止 LLM 无限生成

**对我们的参考价值**：我们的三阶段策略（逐章提取 → 汇总去重 → 逐场生成）与 Dramatron 的层级生成思路一致，可以在阶段三中引入更细粒度的层级生成。

### 3.2 InfinityCN 阶段化 Pipeline

```
Cleaning → Reconstruction → Analysis → Cinematification → Enrichment
```

**关键设计**：
- 纯离线可运行：IndexedDB + PWA + 本地算法（无需 API Key）
- Semantic embeddings（all-MiniLM-L6-v2）用于跨章节上下文连续性
- 情感/张力实时追踪（joy/fear/sadness/suspense/anger/surprise）
- 7 种 AI Provider 自由切换

**对我们的参考价值**：Pipeline 模式是处理长文本的标准方案。嵌入模型用于"跨章关联"的思路值得借鉴。

### 3.3 Toonflow 三 Agent 协作

```
决策 Agent → 执行 Agent → 监督 Agent
```

每个 Agent 有专门职责，监督 Agent 验证结果质量。这比单一 Agent 的可靠性更高。

**对我们的参考价值**：可以在剧本生成后增加一个"质检 Agent"，检查格式规范性、角色一致性等。

### 3.4 ai-scriptify 的 8 步工作流

```
/spec → /idea → /outline → /characters → /scene → /script → /polish → /export
```

**对我们的参考价值**：这种"分步交互"模式适合 Web 界面设计——允许用户在每一步审核和修改 AI 的输出。

---

## 4. 长文本处理策略（论文级）

小说文本通常远超 LLM 单次上下文窗口，以下是 2025 年学术界的主流方案：

| 策略 | 核心思想 | 需要训练 | 适用场景 |
|------|----------|:---:|----------|
| **LLM×MapReduce** (ACL 2025) | 分块独立处理 + 结构化协议聚合 | ❌ | 通用长文本 |
| **ToM 树形 MapReduce** (EMNLP 2025) | 利用文档层级结构自底向上聚合 | ❌ | 有明确层级结构的文档（小说天然有章-节-段结构） |
| **FocusLLM** (ACL 2025) | 动态凝缩关键信息 + 并行解码 | ✅ | 超长文本（400K tokens） |
| **DCS 动态分块** (ACL 2025) | 基于语义相似度自适应变长分块 | ✅ | 阅读理解 |

### 对小说场景的启示

1. **按 "章→场景→段落" 三层分块**是最自然的选择：章是顶层，场景是中层，段落是原子单元。
2. **ToM 树形聚合**天然适合小说处理——先在段落级提取角色/事件，再在章节级汇总，最后全书级去重合并。
3. **放弃固定 Token 数分块**：应按语义边界（段落/场景）切分，避免切断对白或关键情节。

我们的三阶段设计（逐章提取 → 汇总去重 → 逐场生成）本质上就是 LLM×MapReduce 的一个具体实现。

---

## 5. 中文 NLP 工具链

对于"中文小说章节识别与文本预处理"：

| 库 | 功能 | 推荐场景 |
|----|------|----------|
| **Jieba** | 分词、词性标注、关键词 | ⭐ 最轻量，章节标题正则匹配 + 分词 |
| **HanLP** | 全栈 NLP（分词/NER/句法/摘要） | 需要全面 NLP 能力时首选 |
| **Jiagu** | 深度学习 NLP + 知识图谱 | 需要关系抽取时 |
| **SnowNLP** | 中文情感分析、断句 | 轻量情感分析 |

### 章节识别方案

中文小说章节标题的常见模式：

```python
# 模式 1："第X章 标题"（阿拉伯数字）
pattern1 = r'第\d+章[^\n]*'

# 模式 2："第一章 标题"（中文数字）
pattern2 = r'第[一二三四五六七八九十百千万]+章[^\n]*'

# 模式 3："Chapter X: Title"（英文）
pattern3 = r'Chapter\s+\d+[:\s][^\n]*'
```

**推荐**：Jieba + 正则表达式即可满足章节分割需求。HanLP 的 `ChineseDocumentSplitter` 是备选方案。

---

## 6. LLM 结构化输出方案

获取结构化剧本数据（以便序列化为 YAML）的核心挑战。2025 年主流方案：

| 方案 | 原理 | 优点 | 缺点 |
|------|------|------|------|
| **OpenAI `response_format` (json_schema)** | 传入 Pydantic/JSON Schema，API 层约束输出 | 最简单 | 仅 OpenAI 支持 |
| **Claude Structured Output** | 类似，通过 tool_use 或 response_format 约束 | 直接可用 | 需 Anthropic SDK |
| **instructor 库** | Prompt + Pydantic 校验 + 失败重试 | 跨模型通用 | 重试消耗 Token |
| **Constrained Decoding** (Outlines/llguidance) | DFA/文法约束 token 生成 | 100% 格式正确 | 需本地部署模型 |
| **Prompt 工程 + 后处理** | Markdown/分隔符约定 + 正则解析 | 最简单，零依赖 | 不够可靠 |

### 推荐：Claude Tool Use + Pydantic

Claude 的 tool_use 模式可以强制输出符合特定 JSON Schema 的数据。流程：

1. 定义 Pydantic 模型描述期望的 JSON 结构
2. 将 Pydantic 模型转为 JSON Schema 传给 Claude 的 tool_use
3. Claude 返回的工具调用参数即为结构化数据
4. Pydantic 校验 → 成功则继续，失败则重试（最多 3 次）

这种方式的出错率显著低于纯 prompt 工程方式。

---

## 7. 小说文件解析库

| 库 | 输入格式 | 输出 | 适用 |
|----|----------|------|------|
| **web-novel-scraper** | 网页爬取 | EPUB | 在线小说 |
| **xsget** | 网页 HTML | TXT | 网页→文本 |
| **Distill** | EPUB | TXT + 章节摘要 | 电子书 |
| **epub2text** | EPUB | TXT（按章） | 最轻量 EPUB 解析 |
| **pdfjs-dist** | PDF | Text | PDF 提取 |
| **python-docx** | DOCX | Text | Word 文档 |
| **Tesseract.js** | 扫描件图片 | Text (OCR) | 扫描件 |

**覆盖策略**：
- V1 先支持 `.txt` 纯文本（最小可行版本）
- V2 扩展 `.epub` 和 `.docx`
- PDF 放在最后（排版复杂，需要 OCR 备选）

---

## 8. 综合对比与推荐

### 8.1 技术选型对照表

| 决策点 | A 选项 | B 选项 | 推荐 | 理由 |
|--------|--------|--------|:---:|------|
| 后端语言 | Python | Node.js | **Python** | LLM/文本处理生态最强 |
| 后端框架 | FastAPI | Flask/Django | **FastAPI** | 高性能 + 原生 async + Pydantic 集成 |
| AI 引擎 | Claude API | OpenAI API | **Claude API** | 长上下文更强，tool_use 结构化输出更可靠 |
| 结构化输出 | instructor | Claude tool_use | **Claude tool_use** | 原生支持，无需额外库 |
| 前端 | React + Vite | 纯 HTML/JS | **React + Vite** | 丰富的编辑器组件生态 |
| 存储 | SQLite | PostgreSQL | **SQLite** | 单机部署，零运维 |
| 异步任务 | FastAPI BackgroundTasks | Celery + Redis | **BackgroundTasks（V1）** | V1 无需 Redis 依赖 |
| 输出格式 | YAML | JSON / Fountain | **YAML** | 差异化，人类可编辑 |

### 8.2 推荐的最小 MVP 功能集

基于调研，建议 V1 聚焦以下功能（而非全流程）：

| 优先级 | 功能 | 理由 |
|:---:|------|------|
| P0 | TXT 文件上传 + 章节自动识别 | 入口功能 |
| P0 | AI 角色提取（逐章） | 核心转换 |
| P0 | AI 剧本生成 + YAML 输出 | 核心输出 |
| P0 | YAML 文件下载 | 最小可用闭环 |
| P1 | Web 端剧本预览 | 用户体验 |
| P1 | 角色列表查看与手动编辑 | 人机协同 |
| P1 | 转换进度展示 | 长任务反馈 |
| P2 | EPUB/DOCX 支持 | 扩大用户群 |
| P2 | 在线剧本编辑 + 保存 | 完整编辑闭环 |
| P3 | 导出 Fountain/FDX 格式 | 与行业工具互通 |

---

## 9. 市场空白与我们的定位

### 竞品的共同缺陷

1. **没有 YAML 格式输出** — 所有竞品要么输出私有格式，要么输出 Fountain/JSON。YAML 兼顾"人类可编辑"和"程序可处理"，是剧本协作场景下的独特价值点。
2. **缺乏可编辑的中间格式** — 大多数工具输出最终文本而非结构化数据，作者难以在保留结构的前提下高效修改。
3. **短剧/漫剧导向过强** — 现有国产工具几乎全部绑定"分镜→视频"流程，纯剧本创作工具反而被忽视。
4. **缺乏可追溯性** — 没有工具建立剧本与原著之间的段落级映射关系，作者无法快速回溯原文验证改编质量。

### 我们的差异化定位

| 维度 | 竞品普遍做法 | 我们的方案 |
|------|-------------|-----------|
| 输出格式 | Fountain / JSON / 私有 | **YAML**（可编辑 + 可处理） |
| 溯源能力 | 无 | 剧本-原著段落级映射（source_mapping） |
| 编辑友好性 | 最终文本输出 | 结构化剧本，支持字段级编辑 |
| 流程定位 | 小说→剧本→视频 | 聚焦"小说→剧本"，做深做透 |
| 适配备注 | 无 | 内置 adaptation_notes（警告/建议/信息） |

### 建议的目标场景

- **独立作者 / 网文创作者**：想把作品改编为剧本，但缺少专业编剧经验
- **短剧团队编剧**：需要快速出剧本初稿，后续人工打磨
- **剧本评估 / 版权评估**：快速将小说转为结构化剧本以评估改编潜力

---

> **下一步**：请根据以上调研结果，确认以下决策后进入开发：
> 1. 输入格式优先支持哪些？（建议 V1 仅 TXT，V2 加 EPUB/DOCX）
> 2. 目标剧本类型？（建议先做通用舞台/电影剧本格式）
> 3. AI 引擎选择？（建议 Claude API，长上下文 + 结构化输出能力强）
> 4. 是否需要 Web 界面？（建议有，但 V1 可先从 CLI/API 入手）
