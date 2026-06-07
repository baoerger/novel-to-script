// ── Task ──

export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'

export interface TaskInfo {
  task_id: string
  status: TaskStatus
  filename: string
  progress: number
  message: string
  created_at: string
  updated_at: string
  result_path: string
  error: string
}

// ── Chapters ──

export interface ChapterPreview {
  index: number
  title: string
  line_count: number
  preview: string
}

export interface ChapterListResponse {
  task_id: string
  chapter_count: number
  chapters: ChapterPreview[]
}

// ── Script ──

export type ContentType = 'stage_direction' | 'dialogue' | 'voiceover' | 'transition'

export interface ScriptMeta {
  title: string
  source_novel: string
  generated_at: string
  total_acts: number
  total_scenes: number
}

export interface ScriptCharacter {
  id: string
  name: string
  aliases: string[]
  role: string
  archetype: string
  description: string
}

export interface CharacterRelation {
  from_char: string
  to_char: string
  relation: string
  description: string
}

export interface Setting {
  location: string
  time: string
  description: string
}

export interface ContentElement {
  type: ContentType
  character: string
  text: string
  delivery: string
}

export interface ScriptScene {
  scene_id: string
  scene_heading: string
  setting: Setting
  characters_present: string[]
  content: ContentElement[]
}

export interface ScriptAct {
  act_number: number
  act_title: string
  scenes: ScriptScene[]
}

export interface SourceMapping {
  scene_id: string
  source_chapter: number
  source_paragraphs: number[]
}

export interface AdaptationNote {
  scene_id: string
  severity: string
  message: string
}

export interface Script {
  meta: ScriptMeta
  characters: ScriptCharacter[]
  character_relationships: CharacterRelation[]
  acts: ScriptAct[]
  source_mapping: SourceMapping[]
  adaptation_notes: AdaptationNote[]
}
