from enum import Enum

from pydantic import BaseModel, Field


class ContentType(str, Enum):
    """剧本内容元素类型"""

    STAGE_DIRECTION = "stage_direction"
    DIALOGUE = "dialogue"
    VOICEOVER = "voiceover"
    TRANSITION = "transition"


class ScriptMeta(BaseModel):
    """剧本元信息"""

    title: str = Field(min_length=1, description="剧本标题")
    source_novel: str = Field(default="", description="原著名称")
    generated_at: str = Field(default="", description="生成时间 ISO 格式")
    total_acts: int = Field(default=0, ge=0, description="幕数")
    total_scenes: int = Field(default=0, ge=0, description="场次数")


class ScriptCharacter(BaseModel):
    """剧本角色卡片"""

    id: str = Field(min_length=1, description="角色 ID")
    name: str = Field(min_length=1, description="角色名称")
    aliases: list[str] = Field(default_factory=list, description="别名")
    role: str = Field(default="minor", description="角色类型")
    archetype: str = Field(default="", description="角色原型")
    description: str = Field(default="", description="角色描述")


class CharacterRelation(BaseModel):
    """剧本角色关系"""

    from_char: str = Field(min_length=1, description="源角色 ID")
    to_char: str = Field(min_length=1, description="目标角色 ID")
    relation: str = Field(min_length=1, description="关系类型")
    description: str = Field(default="", description="关系描述")


class Setting(BaseModel):
    """场景设定"""

    location: str = Field(default="", description="地点")
    time: str = Field(default="", description="时间")
    description: str = Field(default="", description="场景描述")


class ContentElement(BaseModel):
    """剧本内容元素（一场中的最小单元）"""

    type: ContentType = Field(description="元素类型")
    character: str = Field(default="", description="对白/独白的说话角色 ID")
    text: str = Field(default="", description="内容文本")
    delivery: str = Field(default="", description="表演提示/语气")


class ScriptScene(BaseModel):
    """单场剧本"""

    scene_id: str = Field(min_length=1, description="场景 ID")
    scene_heading: str = Field(default="", description="场标题，如 INT. 城主府 - 日")
    setting: Setting = Field(default_factory=Setting, description="场景设定")
    characters_present: list[str] = Field(default_factory=list, description="出场角色 ID 列表")
    content: list[ContentElement] = Field(default_factory=list, description="内容元素序列")


class ScriptAct(BaseModel):
    """一幕剧本（包含多场）"""

    act_number: int = Field(ge=0, description="幕序号，从 0 开始")
    act_title: str = Field(default="", description="幕标题")
    scenes: list[ScriptScene] = Field(default_factory=list, description="场内场景列表")


class SourceMapping(BaseModel):
    """剧本元素 → 原文段落的溯源映射"""

    scene_id: str = Field(min_length=1, description="剧本场景 ID")
    source_chapter: int = Field(ge=0, description="来源章节序号")
    source_paragraphs: list[int] = Field(default_factory=list, description="来源段落序号列表")


class AdaptationNote(BaseModel):
    """改编备注"""

    scene_id: str = Field(default="", description="关联场景 ID")
    severity: str = Field(default="info", description="严重程度: info/warning/critical")
    message: str = Field(default="", description="备注内容")


class Script(BaseModel):
    """完整剧本"""

    meta: ScriptMeta = Field(default_factory=ScriptMeta, description="剧本元信息")
    characters: list[ScriptCharacter] = Field(default_factory=list, description="角色列表")
    character_relationships: list[CharacterRelation] = Field(default_factory=list, description="角色关系列表")
    acts: list[ScriptAct] = Field(default_factory=list, description="幕列表")
    source_mapping: list[SourceMapping] = Field(default_factory=list, description="溯源映射列表")
    adaptation_notes: list[AdaptationNote] = Field(default_factory=list, description="改编备注列表")
