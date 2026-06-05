from pydantic import BaseModel, Field


class NovelChapter(BaseModel):
    """小说单章"""

    chapter_index: int = Field(ge=0, description="章节序号，从 0 开始")
    chapter_title: str = Field(min_length=1, description="章节标题")
    raw_text: str = Field(min_length=1, description="章节原始文本")
    paragraph_count: int = Field(default=0, ge=0, description="段落数量")
    token_estimate: int = Field(default=0, ge=0, description="Token 估算值")


class NovelText(BaseModel):
    """小说完整文本"""

    title: str = Field(min_length=1, description="书名")
    chapters: list[NovelChapter] = Field(default_factory=list, description="章节列表")

    @property
    def total_paragraphs(self) -> int:
        return sum(ch.paragraph_count for ch in self.chapters)

    @property
    def total_tokens_estimate(self) -> int:
        return sum(ch.token_estimate for ch in self.chapters)
