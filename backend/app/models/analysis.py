from pydantic import BaseModel, Field


class ExtractedCharacter(BaseModel):
    """AI 从单章中提取的角色"""

    name: str = Field(min_length=1, description="角色名称")
    aliases: list[str] = Field(default_factory=list, description="别名/称呼列表")
    role_hint: str = Field(default="", description="角色定位提示（主角/反派/配角/龙套）")
    description: str = Field(default="", description="角色外貌、性格描述")
    first_appearance_chapter: int = Field(ge=0, description="首次出场章节序号")


class SceneBoundary(BaseModel):
    """AI 检测的场景切换边界"""

    scene_index: int = Field(ge=0, description="场景序号（章内从 0 开始）")
    summary: str = Field(default="", description="场景内容摘要")
    location: str = Field(default="", description="场景地点")
    time_hint: str = Field(default="", description="时间提示")
    characters_present: list[str] = Field(default_factory=list, description="在场角色名称列表")
    start_paragraph: int = Field(ge=0, description="场景起始段落序号")
    end_paragraph: int = Field(ge=0, description="场景结束段落序号")


class DialogueEntry(BaseModel):
    """AI 从单章中提取的对白条目"""

    paragraph_index: int = Field(ge=0, description="对白所在段落序号")
    speaker: str = Field(default="", description="说话人")
    raw_text: str = Field(default="", description="原文中的原始对白文本")
    cleaned_dialogue: str = Field(default="", description="清洗后的对白内容（去引号/叙述）")
    stage_direction: str = Field(default="", description="伴随的舞台指示/动作描述")


class ChapterAnalysis(BaseModel):
    """单章分析结果聚合"""

    chapter_index: int = Field(ge=0, description="对应章节序号")
    characters: list[ExtractedCharacter] = Field(default_factory=list, description="提取的角色列表")
    scenes: list[SceneBoundary] = Field(default_factory=list, description="检测的场景边界列表")
    dialogues: list[DialogueEntry] = Field(default_factory=list, description="提取的对白列表")
    props: list[str] = Field(default_factory=list, description="出现的道具列表")
    locations: list[str] = Field(default_factory=list, description="出现的地点列表")
