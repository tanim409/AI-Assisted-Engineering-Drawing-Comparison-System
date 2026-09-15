from typing import Literal

from pydantic import Field,BaseModel


class RegionResult(BaseModel):
    region_index: int = Field(description="Input region index this result corresponds to")
    category: Literal[
        "unclassified",
        "pending_review",
        "no_change",
        "addition",
        "note_or_annotation_change",
        "symbol_or_code_change",
        "removal",
        "dimension_change"
    ] = Field(description="Confirmed or corrected type of change")
    description: str = Field(description="Short human-readable change description using visible values")
    old_value: str | None = Field(default=None, description="Extracted prior value or text from OLD drawing, if applicable")
    new_value: str | None = Field(default=None, description="Extracted new value or text from NEW drawing, if applicable")
    confidence: float = Field(description="Confidence from 0 to 1", ge=0, le=1)


class BatchClassification(BaseModel):
    results: list[RegionResult] = Field(description="One result per region, matched by region_index")
    overall_summary: str = Field(description="summarizing all changes across the drawing")

class AskRequest(BaseModel):
    report_id: str
    question: str


class ChangeReviewRequest(BaseModel):
    status: Literal["confirmed", "false_positive"]
    note: str | None = None
    reviewer_id: str | None = None

class QAResponse(BaseModel):
    answer: str = Field(description="A direct answer to the user's question, based only on the provided changes list")
    referenced_change_indices: list[int] = Field(
        description="Indices (position in the changes list, 0-based) of the specific changes this answer is based on. Empty list if none apply."
    )


class CreateDrawingRequest(BaseModel):
    name: str | None = Field(default=None, description="Optional display name; defaults to 'Untitled Drawing'")


class RenameDrawingRequest(BaseModel):
    name: str = Field(min_length=1, description="New display name for the drawing")


class DrawingSettingsRequest(BaseModel):
    min_ocr_confidence: float | None = None
    visual_change_threshold: float | None = None
    min_title_match_score: float | None = None
    min_title_ocr_confidence: float | None = None
    min_title_words: int | None = None
    title_block_x_pct: float | None = None
    title_block_y_pct: float | None = None
    title_block_w_pct: float | None = None
    title_block_h_pct: float | None = None
    page_size_mismatch_threshold: float | None = None
    target_physical_width_inches: float | None = None
