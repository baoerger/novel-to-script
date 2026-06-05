from pydantic import BaseModel, Field


class ConsolidatedCharacter(BaseModel):
    """跨章去重合并后的角色"""

    id: str = Field(min_length=1, description="唯一标识，如 CHAR_001")
    name: str = Field(min_length=1, description="角色名称")
    aliases: list[str] = Field(default_factory=list, description="所有别名汇总")
    role: str = Field(default="minor", description="角色类型: protagonist/antagonist/supporting/minor")
    archetype: str = Field(default="", description="角色原型，如 导师/盟友/阴影")
    description: str = Field(default="", description="综合角色描述（外貌+性格+背景）")
    appears_in_chapters: list[int] = Field(default_factory=list, description="出场章节序号列表")
    related_props: list[str] = Field(default_factory=list, description="关联道具")


class CharacterRelationship(BaseModel):
    """角色关系"""

    from_char: str = Field(min_length=1, description="源角色 ID")
    to_char: str = Field(min_length=1, description="目标角色 ID")
    relation: str = Field(min_length=1, description="关系类型，如 师徒/敌对/恋人")
    description: str = Field(default="", description="关系描述")


class TimelineScene(BaseModel):
    """跨章时间线中的场景节点"""

    scene_id: str = Field(min_length=1, description="全局唯一场景 ID，如 SCENE_001")
    source_chapter: int = Field(ge=0, description="来源章节序号")
    location: str = Field(default="", description="场景地点")
    time_hint: str = Field(default="", description="时间提示")
    summary: str = Field(default="", description="场景内容摘要")
    characters: list[str] = Field(default_factory=list, description="出场角色 ID 列表")


class ConsolidatedAnalysis(BaseModel):
    """跨章汇总分析结果"""

    characters: list[ConsolidatedCharacter] = Field(default_factory=list, description="去重后的角色列表")
    relationships: list[CharacterRelationship] = Field(default_factory=list, description="角色关系列表")
    timeline: list[TimelineScene] = Field(default_factory=list, description="全局时间线（按顺序排列）")
    global_locations: list[str] = Field(default_factory=list, description="全局地点汇总")
    global_props: list[str] = Field(default_factory=list, description="全局道具汇总")
