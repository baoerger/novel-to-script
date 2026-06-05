# AI 小说转剧本工具 — 系统设计文档

> 版本: 2.0 | 日期: 2026-06-05 | 状态: 设计已确认，待开发

---

## 1. 核心目标

将长篇小说文本（3 章以上）自动转换为结构化的 YAML 格式剧本，降低小说作者将作品改编为剧本的门槛。系统通过 AI 完成以下核心转换：

- **角色提取与归类**：从小说文本中自动识别所有角色、角色关系、角色对白归属。
- **场景切分与重组**：将小说的叙事段落切分为剧本场景（Scene），按时间/空间重排。
- **叙事 → 剧本格式转换**：将小说中的描写性语言转换为舞台说明（Stage Direction），将对白转换为标准剧本对白格式。
- **可编辑初稿输出**：输出结构化 YAML，作者可直接编辑、打磨，无需从空白开始。

### 差异化定位

基于市场调研（详见 [research.md](research.md)），现有工具的共同缺陷：

| 竞品缺口 | 本方案 |
|----------|--------|
| 无 YAML 格式输出（都是 Fountain/JSON/私有格式） | **YAML** — 人类可编辑 + 程序可处理 + 可注释 |
| 缺乏可编辑的中间格式 | 结构化字段级剧本，支持精确修改 |
| 无剧本-原著溯源 | `source_mapping` 段落级映射 |
| 过度绑定"分镜→视频"流程 | 聚焦"小说→剧本"，做深做透 |

---

## 2. 需求决策（已确认）

| # | 问题 | 决策 | 依据 |
|---|------|------|------|
| Q1 | 输入文件格式 | **.txt + .docx** | .txt 覆盖 MVP；.docx 是作者标配写作工具 |
| Q2 | 目标剧本类型 | **通用格式**（Act→Scene→Content，`type` 字段扩展） | 一套 Schema 适配多场景，通过可选字段区分 |
| Q3 | 小说语言 | **仅中文** | 中文短剧/网文改编是最大需求场景 |
| Q4 | 章节边界识别 | **正则匹配 + 降级兜底** | 匹配到 ≥3 个章节边界则采用，否则全文作为单章并提示用户 |
| Q5 | 用户界面 | **CLI + REST API**（V1），前端即插即上（V2） | 先聚焦转换质量，API 设计好后加前端只是时间问题 |
| Q6 | 长度上限与分片 | **按章分片**，单章 ≤15K tokens，超长章按段落边界二次切分。限定 3~100 章 | 以自然语义边界分块，符合 LLM×MapReduce 最佳实践 |
| Q7 | 用户认证与历史 | **V1 无用户系统**，V2 加 SQLite 本地持久化 | 用户认证是最晚加的功能 |
| Q8 | 在线编辑与导出 | **V1 下载 YAML 本地编辑**，V2 加 Web 在线编辑 | 最小可用闭环优先 |

---

## 3. 技术栈

| 层级 | 技术选型 | 理由 |
|------|----------|------|
| **语言** | Python 3.12+ | LLM/文本处理生态最强，OpenAI SDK 兼容所有国产模型 |
| **后端框架** | FastAPI | 高性能 async + Pydantic 深度集成 + 自动 OpenAPI 文档 |
| **AI 引擎（主）** | **DeepSeek V4 Flash** | 1M 上下文不加价，¥1.00/百万 input，长文本场景成本比 Claude 低 40 倍 |
| **AI 引擎（备）** | **Qwen3.7 Plus** | 结构化输出一次成功率最高，DeepSeek 重试 3 次均失败时兜底 |
| **LLM 调用层** | OpenAI SDK（兼容模式） | DeepSeek/Qwen/GLM 均兼容 OpenAI SDK，底层模型可热切换 |
| **结构化输出** | JSON mode + Pydantic 校验 + 重试降级 | 先 JSON mode 约束输出 → Pydantic 校验 → 失败则带错误信息重试（≤3 次）→ 全部失败降级到备选模型 |
| **Prompt 管理** | Jinja2 模板文件 | 轻量，Prompt 与代码解耦，方便调优 |
| **章节解析** | Python `re` + `python-docx` | 正则处理 .txt；python-docx 处理 Word 文档 |
| **YAML 序列化** | PyYAML 或 ruamel.yaml | 标准库级支持 |
| **异步任务** | FastAPI BackgroundTasks（V1），Celery + Redis（V2） | V1 无需额外中间件 |
| **文件存储** | 本地文件系统（`./projects/`） | V1 不引入数据库 |
| **部署** | Docker 单容器 | 一键启动 |
| **前端（V2）** | React 18 + TypeScript + Vite + Tailwind CSS | 见 research.md 市场做法对比 |

### 3.1 AI 模型选型与成本分析

**为什么不选 Claude API，选 DeepSeek：**

| 对比维度 | Claude Sonnet 4 | DeepSeek V4 Flash | 差距 |
|----------|:--:|:--:|:--:|
| 百万 input tokens | ~$3（≈¥21） | ¥1.00 | 21 倍 |
| 百万 output tokens | ~$15（≈¥107） | ¥2.00 | 53 倍 |
| 上下文窗口 | 200K | **1M** | 5 倍 |
| 长文本加价 | 无 | **无** | — |
| 缓存命中 input | — | **¥0.02**（98% off） | — |
| 结构化输出 | 原生 tool_use，极可靠 | JSON mode，约 30% 需重试 | 靠工程手段弥补 |
| 100 章小说单次成本 | ~¥86 | **~¥2.16**（含重试） | **40 倍** |
| 开发阶段日测 10 次 | ~¥860 | **~¥22** | 开发成本差距巨大 |

**模型可切换架构：**

```python
# config.py — 改一行即可切换模型
class LLMConfig:
    provider: str = "deepseek"          # deepseek | qwen | glm | claude
    model: str = "deepseek-v4-flash"    # 具体模型名
    fallback_model: str = "qwen3.7-plus"
    max_retries: int = 3
    temperature: float = 0.0            # 结构化输出用 0 保证确定性

# 所有 provider 统一通过 OpenAI SDK 兼容接口调用
# DeepSeek:  base_url="https://api.deepseek.com"
# Qwen:     base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
# GLM:      base_url="https://open.bigmodel.cn/api/paas/v4"
```

**结构化输出的重试降级流程：**

```
LLM 调用 (JSON mode)
    │
    ▼
Pydantic 校验
    ├── ✅ 通过 → 返回数据
    └── ❌ 失败 → retry_count += 1
                    │
                    ├── retry_count < 3 → 重试（Prompt 中附加校验错误信息）
                    └── retry_count = 3 → 降级到 fallback_model 重试
                                            ├── ✅ 通过 → 返回数据 + 记录降级事件
                                            └── ❌ 失败 → 标记本章/场失败，继续处理下一个
```

这套流程预计将 DeepSeek 的实际成功率从 ~70% 提升到 **95%+**，且失败时自动降级不丢数据。

---

## 4. 核心数据流

```
用户上传小说(.txt / .docx)
    │
    ▼
┌──────────────────────────────┐
│  1. 文本预处理               │
│  - 章节识别与分割（正则）    │
│  - 段落归一化（空行→段落）   │
│  - Token 估算 + 超长分片     │
│  输出: Chapter[]             │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  2. AI 提取阶段（逐章并行）  │
│  - 角色识别 + 关系抽取       │
│  - 场景边界检测              │
│  - 对白归属识别              │
│  - 道具/地点标记             │
│  输出: ChapterAnalysis[]     │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  3. AI 汇总与去重            │
│  - 角色跨章去重合并          │
│  - 别名归并                  │
│  - 场景时间线排序            │
│  - 角色关系图构建            │
│  输出: ConsolidatedAnalysis  │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  4. AI 剧本生成（分批）      │
│  - 按场次分批调用 AI         │
│  - 叙事→剧本格式转换         │
│  - 对话/舞台说明分类         │
│  - 幕/场结构组织             │
│  输出: Script (YAML)         │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  5. 输出                     │
│  - YAML 文件生成             │
│  - 文件下载 / API 返回       │
│  - 转换报告（角色数/场次数等）│
└──────────────────────────────┘
```

### 关键设计决策

**分批策略**：采用 **LLM×MapReduce 模式**（ACL 2025 验证有效）— 逐章 Map → 汇总 Reduce → 逐场生成。这是长文本处理的最佳实践（详见 [research.md §4](research.md#4-长文本处理策略)）。

**错误容忍**：单章分析失败不阻塞整体流程，失败章跳过并在报告中标注。AI 输出格式校验失败时重试最多 3 次。

**Token 预算与成本**：阶段 2（逐章提取）每章预算 ~4K output tokens；阶段 3（汇总）预算 ~8K output tokens；阶段 4（剧本生成）每场预算 ~2K output tokens。以 100 章小说计，DeepSeek V4 Flash 全流程 API 成本约 **¥2~3**（含重试）。

---

## 5. 核心数据结构与接口契约

### 5.1 输入：小说章节（预处理后）

```python
# models/input.py
from pydantic import BaseModel

class NovelChapter(BaseModel):
    chapter_index: int              # 章节序号，从 1 开始
    chapter_title: str              # 原始章节标题，如 "第一章 初入江湖"
    raw_text: str                   # 该章全部文本
    paragraph_count: int            # 段落数（用于分片判断）
    token_estimate: int             # Token 估算（字符数 × 1.5，中文粗估）

class NovelText(BaseModel):
    title: str                      # 书名（从文件名或用户输入推断）
    chapters: list[NovelChapter]    # 章节列表
    total_paragraphs: int
    total_tokens_estimate: int
```

### 5.2 AI 中间产物：章节分析结果

```python
# models/analysis.py
from pydantic import BaseModel

class ExtractedCharacter(BaseModel):
    name: str                       # 角色名
    aliases: list[str]              # 别名/称呼列表，如 ["三哥", "张兄"]
    role_hint: str                  # 角色定位线索，如 "主角"、"反派"、"路人"
    description: str                # 角色简介（AI 从文本中提取）
    first_appearance_chapter: int

class SceneBoundary(BaseModel):
    scene_index: int                # 本章内场景序号
    summary: str                    # 场景概要
    location: str                   # 地点
    time_hint: str                  # 时间线索，如 "傍晚"
    characters_present: list[str]   # 出场角色名（临时，待汇总阶段去重）
    start_paragraph: int            # 起始段落号
    end_paragraph: int              # 结束段落号

class DialogueEntry(BaseModel):
    paragraph_index: int            # 所在段落号
    speaker: str                    # 说话人
    raw_text: str                   # 原文片段
    cleaned_dialogue: str           # 清洗后的对白文本
    stage_direction: str            # 伴随的动作/神态描写

class ChapterAnalysis(BaseModel):
    chapter_index: int
    characters: list[ExtractedCharacter]
    scenes: list[SceneBoundary]
    dialogues: list[DialogueEntry]
    props: list[str]                # 道具
    locations: list[str]            # 地点
```

### 5.3 AI 汇总产物：跨章合并

```python
# models/consolidated.py
from pydantic import BaseModel

class ConsolidatedCharacter(BaseModel):
    id: str                         # CHAR_001 格式唯一 ID
    name: str                       # 规范名
    aliases: list[str]              # 合并后全部别名
    role: str                       # protagonist | antagonist | supporting | minor
    archetype: str                  # 角色原型
    description: str                # 跨章综合描述
    appears_in_chapters: list[int]
    related_props: list[str]

class CharacterRelationship(BaseModel):
    from_char: str                  # CHAR_001
    to_char: str                    # CHAR_002
    relation: str                   # 关系类型，如 "师徒"、"敌对"
    description: str

class TimelineScene(BaseModel):
    scene_id: str                   # S1, S2, ...
    source_chapter: int
    location: str
    time_hint: str
    summary: str
    characters: list[str]           # 角色 ID 列表

class ConsolidatedAnalysis(BaseModel):
    characters: list[ConsolidatedCharacter]
    relationships: list[CharacterRelationship]
    timeline: list[TimelineScene]
    global_locations: list[str]
    global_props: list[str]
```

### 5.4 输出：剧本 YAML Schema

```yaml
# ============================================
# AI 小说转剧本 — YAML Schema v1.0
# 设计原则见 §5.5
# ============================================

meta:
  title: "剧本标题"                       # string, 必填
  source_novel: "原著小说名"              # string, 可选
  author: "原作者"                        # string, 可选
  script_version: "1.0"
  generated_at: "2026-06-05T10:00:00Z"   # ISO 8601
  language: "zh-CN"

characters:                               # 角色清单
  - id: CHAR_001
    name: "张三"
    aliases: ["三哥", "张兄"]
    role: protagonist                     # protagonist | antagonist | supporting | minor | narrator
    archetype: "热血青年"                 # 角色原型
    description: >-
      年轻剑客，青云门第十四代弟子。性格刚烈，嫉恶如仇。
    props: ["青锋剑"]
    notes: ""

character_relationships:                  # 角色关系
  - from: CHAR_001
    to: CHAR_002
    relation: "师徒"
    description: "李四收张三为徒，传授青云剑法。"

acts:                                     # 幕列表
  - act_number: 1
    act_title: "第一幕"                   # 可选

    scenes:                               # 场列表
      - scene_number: 1
        scene_title: "酒楼初遇"           # 可选

        setting:
          location: "悦来酒楼二楼雅座"
          time: "傍晚，夕阳西下"
          atmosphere: "嘈杂中带着一丝紧张"  # 可选
          props: ["酒壶", "长剑"]          # 可选

        characters_present:               # 出场角色 ID
          - CHAR_001
          - CHAR_002

        content:                          # 场内容：按顺序排列
          - type: stage_direction         # 舞台说明
            text: |
              悦来酒楼二楼，靠窗的雅座。
              张三独自坐在桌前，桌上摆着一壶酒、两碟小菜。

          - type: dialogue                # 对白
            character: CHAR_002
            delivery: "(压低声音)"         # 表演提示，可选
            line: "小兄弟，这酒可不便宜，你一个人喝得完吗？"

          - type: stage_direction
            text: "李四从邻桌起身，踱步至张三桌前，不请自坐。"

          - type: dialogue
            character: CHAR_001
            delivery: "(冷冷地)"
            line: "与你何干？"

          - type: voiceover               # 画外音/内心独白
            character: CHAR_001
            line: "这人来者不善……"

          - type: transition              # 转场提示
            text: "灯光渐暗，幕落。"

source_mapping:                           # 剧本-原著溯源
  - scene_number: 1
    source_chapter: 1
    source_paragraphs: [3, 28]
    notes: "基本保持原文对话，仅调整了叙述顺序。"

adaptation_notes:                         # 改编备注
  - type: warning                         # warning | suggestion | info
    scene_number: 1
    element_index: 0
    message: "此处原著的内心描写较多，建议在排练中由导演指导演员呈现。"
```

### 5.5 YAML Schema 设计原因

1. **Act → Scene 二级结构** — 符合舞台剧和电影剧本的行业惯例
2. **`content` 多态数组** — 通过 `type` 字段（`stage_direction` / `dialogue` / `voiceover` / `transition`）扩展，不破坏现有结构。加 `shot`/`camera` 类型即可支持电影剧本
3. **角色 ID 化** — `CHAR_XXX` 唯一 ID，(a) 支持同名角色区分 (b) 改名只需改一处 (c) 便于关系图处理
4. **`source_mapping` 溯源** — 建立剧本场景与原著段落的映射，这是市面所有竞品都不具备的能力
5. **`adaptation_notes` 独立** — 备注与正文分离，可单独开关/过滤，保持剧本正文纯净
6. **YAML > JSON** — 人类直接编辑的体验远优于 JSON，可注释的特性对剧本创作场景至关重要。且市面无竞品使用 YAML，构成差异化

### 5.6 REST API 接口

```
POST   /api/convert                     # 上传小说文件，触发转换（同步返回 task_id）
GET    /api/convert/{task_id}           # 查询转换状态与进度
GET    /api/convert/{task_id}/script    # 获取转换完成的剧本（JSON）
GET    /api/convert/{task_id}/download  # 下载 YAML 文件
```

> V1 仅 4 个端点。无项目管理系统（V2 加）。所有交互通过 `task_id` 定位。

**POST /api/convert 请求**：
```
Content-Type: multipart/form-data
Body:
  - file: .txt 或 .docx 文件
  - title: 可选，书名
```

**GET /api/convert/{task_id} 响应**：
```json
{
  "task_id": "uuid",
  "status": "processing",          // pending | preprocessing | extracting | consolidating | generating | completed | failed
  "progress": {
    "stage": "extracting",         // 当前阶段
    "chapter_done": 3,
    "chapter_total": 10,
    "percent": 30
  },
  "result": null                   // 完成后填充
}
```

---

## 6. 项目结构

前后端拆分为独立子目录，共享根级配置与文档。

```
project-root/                       # Git 仓库根目录
│
├── design.md                       # 系统设计文档（本文件）
├── research.md                     # 市场与技术调研
├── decision-analysis.md            # 方案利弊决策分析
├── README.md                       # 项目说明
├── .gitignore
├── docker-compose.yml              # 一键启动前后端 + 依赖服务
│
├── backend/                        # ===== Python/FastAPI 后端 =====
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI 应用入口 + 路由注册
│   │   ├── config.py               # 配置（API Key, 模型参数, 路径, 限制）
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── input.py            # NovelChapter, NovelText
│   │   │   ├── analysis.py         # ChapterAnalysis, ExtractedCharacter 等
│   │   │   ├── consolidated.py     # ConsolidatedAnalysis
│   │   │   └── script.py           # 剧本 YAML 的 Pydantic 模型
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── llm.py              # LLM 调用抽象层（多 provider + 重试降级）
│   │   │   ├── parser.py           # 章节分割 + 段落归一化（.txt + .docx）
│   │   │   ├── chunker.py          # Token 估算 + 超长分片
│   │   │   ├── extractor.py        # AI 逐章提取（阶段 2）
│   │   │   ├── consolidator.py     # AI 汇总去重（阶段 3）
│   │   │   ├── generator.py        # AI 剧本生成（阶段 4）
│   │   │   └── yaml_writer.py      # Pydantic → YAML 序列化
│   │   ├── prompts/
│   │   │   ├── extract_characters.j2   # 角色提取 Prompt
│   │   │   ├── extract_scenes.j2       # 场景检测 Prompt
│   │   │   ├── extract_dialogues.j2    # 对白识别 Prompt
│   │   │   ├── consolidate.j2          # 汇总去重 Prompt
│   │   │   └── generate_scene.j2       # 单场剧本生成 Prompt
│   │   └── tasks.py                # BackgroundTasks 异步任务管理
│   ├── tests/
│   │   ├── test_parser.py
│   │   ├── test_chunker.py
│   │   ├── test_extractor.py
│   │   └── fixtures/               # 测试用小说片段
│   ├── projects/                   # 运行时输出目录（gitignore）
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example                # 环境变量模板（API Key 等）
│
├── frontend/                       # ===== React 前端（V2）=====
│   ├── src/
│   │   ├── components/             # React 组件
│   │   ├── pages/                  # 页面
│   │   ├── services/               # API 调用封装
│   │   └── types/                  # TypeScript 类型定义（与后端 Pydantic 对齐）
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   └── Dockerfile
│
└── samples/                        # 示例小说文件（用于测试与演示）
    └── sample_novel.txt
```

> **V1 说明**：`frontend/` 和 `samples/` 在 V1 阶段为目录占位或最小骨架，V2 再填充。V1 关注 `backend/` 全部功能跑通。

---

## 7. V1 范围与 V2 规划

### V1（当前 — 预计 3-5 天）

- [x] 设计文档与 Schema 定义
- [ ] LLM 调用抽象层（OpenAI SDK 兼容接口 + 多 provider 切换 + 重试降级）
- [ ] .txt + .docx 解析与章节分割
- [ ] Token 估算与超长分片
- [ ] AI 逐章提取（角色/场景/对白）— DeepSeek V4 Flash 为主，Qwen3.7 Plus 兜底
- [ ] 汇总去重
- [ ] 剧本 YAML 生成
- [ ] CLI 入口 + FastAPI 接口
- [ ] Docker 部署

### V2（规划）

- [ ] EPUB 输入支持
- [ ] SQLite 项目持久化与历史记录
- [ ] React Web 前端 + 在线剧本预览编辑
- [ ] 剧本类型参数（舞台/电影/短剧）
- [ ] 英文支持
- [ ] 更多模型接入（GLM-4.7 Flash 免费模型等）
- [ ] 转换质量评估报告

---

> **参考文档**：[research.md](research.md) — 市场与技术调研 | [decision-analysis.md](decision-analysis.md) — 方案利弊详细对比
