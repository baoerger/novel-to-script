# AI 小说转剧本工具 — 系统设计文档

## 1. 核心目标

将长篇小说文本（3 章以上）自动转换为结构化的 YAML 格式剧本，降低小说作者将作品改编为剧本的门槛。系统通过 AI 完成以下核心转换：

- **角色提取与归类**：从小说文本中自动识别所有角色、角色关系、角色对白归属。
- **场景切分与重组**：将小说的叙事段落切分为剧本场景（Scene），按时间/空间重排。
- **叙事 → 剧本格式转换**：将小说中的描写性语言转换为舞台说明（Stage Direction），将对白转换为标准剧本对白格式。
- **可编辑初稿输出**：输出结构化 YAML，作者可直接编辑、打磨，无需从空白开始。

## 2. 待澄清问题

在进入开发前，以下问题需要明确：

| # | 问题 | 影响范围 |
|---|------|----------|
| **Q1** | 输入文件的格式是什么？纯文本(.txt)、Markdown(.md)、Word(.docx) 还是 PDF？ | 文件解析模块设计 |
| **Q2** | 目标剧本类型是舞台剧、电影剧本还是电视剧本？格式差异较大（如电视剧本分集、电影剧本分场）。 | YAML Schema 结构 |
| **Q3** | 小说语言是中文、英文还是多语言混合？ | AI 模型选型与提示词设计 |
| **Q4** | 章节边界如何识别？依赖用户手动标注、标题关键词匹配（"第X章"），还是 AI 自动检测？ | 章节解析策略 |
| **Q5** | 用户是否需要 Web 界面，还是命令行工具即可？ | 前端工作量评估 |
| **Q6** | 单次处理的小说长度上限是多少？是否需要对超长文本做分片处理？ | 架构设计与成本控制 |
| **Q7** | 是否需要用户认证与历史记录管理？ | 数据库设计与后端复杂度 |
| **Q8** | 转换后的剧本是否需要支持人工在线编辑与再导出？ | 前端功能范围 |

> **请在开发前确认以上问题。本文档后续设计基于以下假设：**
> - 输入为 `.txt` 纯文本，章节由 "第X章" 模式自动识别
> - 目标剧本为**电影/舞台剧剧本**格式
> - 中文小说为主
> - 提供 Web 界面
> - 长文本需要分片处理
> - 不包含用户系统，单机/单用户使用

## 3. 技术栈推荐

| 层级 | 技术选型 | 理由 |
|------|----------|------|
| **后端框架** | Python 3.12+ / FastAPI | AI/LLM 生态最完善；FastAPI 高性能、类型安全 |
| **AI 引擎** | Claude API (Anthropic) 或 OpenAI GPT-4o | 长文本理解能力强，结构化输出稳定 |
| **Prompt 管理** | 内联模板 (Jinja2) | 轻量，不需要额外 Prompt 管理平台 |
| **前端** | React 18 + TypeScript + Vite | 主流技术栈，生态丰富，适合文本编辑器场景 |
| **样式** | Tailwind CSS | 快速原型开发 |
| **数据存储** | SQLite（本地文件）+ YAML 文件导出 | 轻量，无需额外数据库服务，剧本以 YAML 文件持久化 |
| **异步任务** | Celery + Redis 或 FastAPI BackgroundTasks | 长文本转换需异步处理，避免 HTTP 超时 |
| **部署** | Docker 单容器 | 简单可复现 |

## 4. 核心数据流

```
用户上传小说(.txt)
    │
    ▼
┌─────────────────────────────┐
│  1. 文本预处理              │
│  - 章节识别与分割           │
│  - 段落归一化               │
│  - 长度分片（超长章节）     │
└──────────┬──────────────────┘
           │  Chapter[]
           ▼
┌─────────────────────────────┐
│  2. AI 提取阶段（逐章）     │
│  - 角色识别 + 关系抽取      │
│  - 场景边界检测             │
│  - 对白归属识别             │
│  - 重要道具/地点标记        │
└──────────┬──────────────────┘
           │  ChapterAnalysis[]
           ▼
┌─────────────────────────────┐
│  3. AI 汇总与去重           │
│  - 角色去重合并             │
│  - 场景跨章关联             │
│  - 时间线推断               │
└──────────┬──────────────────┘
           │  ConsolidatedAnalysis
           ▼
┌─────────────────────────────┐
│  4. AI 剧本生成             │
│  - 小说叙事 → 剧本格式     │
│  - 对话/舞台说明分类        │
│  - 幕/场结构组织            │
└──────────┬──────────────────┘
           │  Script (YAML)
           ▼
┌─────────────────────────────┐
│  5. 输出与展示              │
│  - YAML 文件下载            │
│  - Web 端预览与编辑         │
└─────────────────────────────┘
```

## 5. 核心数据结构与接口契约

### 5.1 输入：小说章节

```json
// POST /api/projects — 创建项目并上传文件
{
  "title": "书名（可选，默认从文件名推断）",
  "file": "<multipart/form-data .txt file>"
}

// 系统内部模型 NovelChapter（预处理后）
{
  "chapterIndex": 1,           // 章节序号，从 1 开始
  "chapterTitle": "第一章 初入江湖",  // 原始章节标题
  "rawText": "完整的章节原文...",      // 该章全部文本
  "paragraphCount": 142,       // 段落数（用于分片判断）
  "tokenEstimate": 8500        // Token 估算（用于分片判断）
}
```

### 5.2 AI 中间产物：章节分析结果

```json
// ChapterAnalysis — 单章 AI 提取结果
{
  "chapterIndex": 1,
  "characters": [
    {
      "name": "张三",
      "aliases": ["三哥", "张兄"],
      "role": "主角",
      "description": "年轻剑客，师从青云门",
      "firstAppearance": "第一章"
    }
  ],
  "scenes": [
    {
      "sceneIndex": 1,
      "summary": "张三在酒楼遇到李四，二人发生争执",
      "location": "悦来酒楼二楼雅座",
      "time": "傍晚",
      "charactersPresent": ["张三", "李四", "店小二"],
      "startParagraph": 3,
      "endParagraph": 28
    }
  ],
  "dialogueMapping": [
    {
      "paragraphIndex": 12,
      "speaker": "张三",
      "rawText": "\"这酒不对味！\"张三拍桌道。",
      "cleanedDialogue": "这酒不对味！",
      "stageDirection": "张三拍桌"
    }
  ],
  "props": ["青锋剑", "酒壶"],
  "locations": ["悦来酒楼", "城外破庙"]
}
```

### 5.3 AI 汇总产物：跨章合并后的分析

```json
// ConsolidatedAnalysis
{
  "characters": [
    {
      "id": "CHAR_001",
      "name": "张三",
      "aliases": ["三哥", "张兄", "张少侠"],
      "role": "主角",
      "description": "年轻剑客，青云门弟子，性格刚烈",
      "chapters": [1, 2, 3, 4, 5]
    }
  ],
  "characterRelationships": [
    {
      "from": "CHAR_001",
      "to": "CHAR_002",
      "relation": "师徒",
      "description": "李四是张三的授业恩师"
    }
  ],
  "sceneTimeline": [
    {
      "sceneId": "S1",
      "chapter": 1,
      "location": "悦来酒楼",
      "time": "傍晚",
      "summary": "张三初遇李四",
      "characters": ["CHAR_001", "CHAR_002"]
    }
  ],
  "globalLocations": ["悦来酒楼", "城外破庙", "青云山"],
  "globalProps": ["青锋剑", "酒壶", "秘籍残卷"]
}
```

### 5.4 输出：剧本 YAML Schema

```yaml
# ============================================
# AI 小说转剧本 — YAML Schema 定义
# 版本: 1.0
# ============================================

# --- 元信息 ---
meta:
  title: "剧本标题"                   # string, 必填
  source_novel: "原著小说名"          # string, 可选
  author: "原作者"                    # string, 可选
  script_version: "1.0"              # string, 版本号
  generated_at: "2026-06-05T10:00:00Z"  # datetime, 生成时间
  language: "zh-CN"                  # string, 语言代码

# --- 角色清单 ---
characters:
  - id: CHAR_001                     # string, 唯一标识
    name: "张三"                     # string, 角色名
    aliases: ["三哥", "张兄"]        # string[], 别名/称呼列表
    role: protagonist                # enum: protagonist | antagonist | supporting | minor | narrator
    archetype: "热血青年"            # string, 角色原型描述
    description: >-                  # string, 角色简介
      年轻剑客，青云门第十四代弟子。性格刚烈，嫉恶如仇。
      身高七尺，面容清秀，惯用长剑。
    props: ["青锋剑"]                # string[], 关联道具
    notes: ""                        # string, 补充说明

  - id: CHAR_002
    name: "李四"
    role: supporting
    archetype: "世外高人"
    description: "青云门掌门，张三的师父。外表邋遢，实则武功深不可测。"

# --- 角色关系 ---
character_relationships:
  - from: CHAR_001
    to: CHAR_002
    relation: "师徒"                 # string, 关系类型
    description: "李四收张三为徒，传授青云剑法。"

# --- 剧本正文 ---
acts:                                # Act[], 幕列表
  - act_number: 1                    # int, 第几幕
    act_title: "第一幕"              # string, 幕标题（可选）

    scenes:                          # Scene[], 场列表
      - scene_number: 1              # int, 第几场
        scene_title: "酒楼初遇"      # string, 场标题（可选）

        setting:                     # 场景设置
          location: "悦来酒楼二楼雅座"  # string, 地点
          time: "傍晚，夕阳西下"        # string, 时间
          atmosphere: "嘈杂中带着一丝紧张"  # string, 氛围（可选）
          props: ["酒壶", "长剑"]     # string[], 本场道具（可选）

        characters_present:          # string[], 本场出场角色 ID
          - CHAR_001
          - CHAR_002
          - CHAR_003

        # --- 场内容：按顺序排列的剧本元素 ---
        content:
          # 元素 1：舞台说明
          - type: stage_direction
            text: |
              悦来酒楼二楼，靠窗的雅座。
              张三独自坐在桌前，桌上摆着一壶酒、两碟小菜。
              夕阳透过窗棂洒在地上，楼下传来嘈杂的人声。

          # 元素 2：角色对白
          - type: dialogue
            character: CHAR_002       # 说话者 ID
            delivery: "(压低声音)"     # string, 表演提示（可选）
            line: "小兄弟，这酒可不便宜，你一个人喝得完吗？"

          # 元素 3：舞台说明（动作）
          - type: stage_direction
            text: "李四从邻桌起身，踱步至张三桌前，不请自坐。"

          # 元素 4：角色对白
          - type: dialogue
            character: CHAR_001
            delivery: "(冷冷地)"
            line: "与你何干？"

          # 元素 5：画外音 / 内心独白
          - type: voiceover
            character: CHAR_001
            line: "这人来者不善……"

          # 元素 6：转场提示
          - type: transition
            text: "灯光渐暗，幕落。"

# --- 原始映射（用于溯源） ---
source_mapping:
  - scene_number: 1
    source_chapter: 1
    source_paragraphs: [3, 28]        # 原著段落范围
    notes: "基本保持原文对话，仅调整了叙述顺序。"

# --- 改编备注 ---
adaptation_notes:
  - type: warning                     # enum: warning | suggestion | info
    scene_number: 1
    element_index: 0
    message: "此处原著的内心描写较多，建议在排练中由导演指导演员呈现。"
  - type: suggestion
    scene_number: 1
    element_index: 3
    message: "此处对白较短，可考虑扩充以增强戏剧张力。"
```

### 5.5 YAML Schema 设计原因说明

此 Schema 的设计遵循以下原则：

1. **剧本行业惯例**：采用 Act → Scene 二级结构，符合舞台剧和电影剧本的标准格式。`content` 数组中的 `stage_direction` / `dialogue` / `voiceover` / `transition` 四种类型覆盖了剧本的核心元素。
2. **可追溯性**：`source_mapping` 字段建立剧本场景与原著章节的映射关系，作者可以随时回溯原文，验证改编是否恰当。
3. **角色 ID 化**：角色使用 `CHAR_XXX` 唯一 ID 而非直接写名称，(a) 支持同名角色区分，(b) 角色改名时只需改一处，(c) 便于程序化处理角色关系图。
4. **可扩展的 Content 模型**：`content` 使用 `type` 字段的多态数组，未来可扩展新类型（如 `song`、`flashback`、`montage`），不破坏现有结构。
5. **改编备注独立**：`adaptation_notes` 作为独立字段而非嵌入 content，使得剧本正文保持纯净，备注可单独开关/过滤。
6. **机器可处理 + 人类可读**：YAML 格式兼顾了程序化处理（解析、转换、对比）和人类直接编辑的需求，比 JSON 更友好，比纯文本更结构化。

### 5.6 API 接口设计

```
POST   /api/projects                    # 创建项目 + 上传小说文件
GET    /api/projects                    # 列出所有项目
GET    /api/projects/{id}               # 获取项目详情（含章节列表）
DELETE /api/projects/{id}               # 删除项目

POST   /api/projects/{id}/convert       # 触发异步转换
GET    /api/projects/{id}/status        # 查询转换进度（WebSocket 可选）
GET    /api/projects/{id}/script        # 获取转换结果（JSON/YAML）
PUT    /api/projects/{id}/script        # 保存用户编辑后的剧本
GET    /api/projects/{id}/export        # 导出 YAML 文件下载

GET    /api/projects/{id}/characters    # 获取角色列表（可手动编辑）
PUT    /api/projects/{id}/characters    # 更新角色信息（合并/改名）

POST   /api/projects/{id}/reanalyze    # 针对某章重新分析
```

## 6. 关键设计决策

### 6.1 分批处理策略

长篇小说的 Token 数远超单次 AI 调用的上下文窗口，因此采用 **逐章提取 → 汇总去重 → 逐场生成** 的三阶段策略：

- **阶段一（逐章）**：每章独立调用 AI 做角色/场景/对白提取。各章结果可能包含重叠角色（不同称呼）和跨章场景。
- **阶段二（汇总）**：将所有章节分析结果汇总，调用 AI 做角色去重合并、别名归并、场景时间线排序。
- **阶段三（生成）**：基于汇总结果，按场次分批调用 AI 将叙事文本转为剧本格式。

### 6.2 编辑友好性

- 转换完成后，用户可在 Web 端逐场编辑、调整对白。
- 支持角色名称全局替换（例如 AI 误识别了角色名）。
- 每次保存生成版本快照，支持回退。

### 6.3 错误处理

- 单章分析失败不影响其他章节，支持单章重试。
- AI 输出格式不符预期时，使用 Pydantic 校验 + 重试机制（最多 3 次）。
- 长文本 Token 溢出时，自动按段落边界分片，保证分片不切断对白。

---

> **下一步**：请确认第 2 节中的待澄清问题后，进入第二步 "核心逻辑实现"。
