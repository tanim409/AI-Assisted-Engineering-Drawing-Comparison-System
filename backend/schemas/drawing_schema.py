"""Pydantic schemas for the VLM hybrid comparison pipeline (Track A + Track B)."""
from typing import Literal, Optional, Union

from pydantic import Field, BaseModel


# ── Track A: Inventory Extraction Schemas ─────────────────────────────────────

class InventoryEntry(BaseModel):
    entity_name: str = Field(description="Name or label of the drawing entity (e.g. 'BATH-2 width', 'Sheet Number', 'Material Note 3')")
    value: Optional[str] = Field(default=None, description="The stated value/text for this entity (e.g. '2400mm', 'REV B', 'Steel')")
    location: Optional[str] = Field(default=None, description="Free text location on the drawing (e.g. 'Unit B, north-east corner', 'Title Block')")
    entity_type: Literal["dimension", "label", "note", "fixture", "title_block", "other"] = Field(
        default="other",
        description="Class of entity: dimension (numeric), label (room/area name), note (text callout), fixture, title_block field, other"
    )


class DrawingInventory(BaseModel):
    summary: str = Field(description="One-sentence summary of what this drawing page shows")
    entries: list[InventoryEntry] = Field(default_factory=list, description="All labeled entities found on the drawing")


# ── Track A: Change Records (extraction-based, high confidence) ───────────────

class TrackAChange(BaseModel):
    source: Literal["extraction"] = Field(default="extraction", description="Track A: produced by inventory extraction and diff")
    confidence_tier: Literal["high"] = Field(default="high", description="Track A changes are always high confidence — grounded in exact label/value comparison")
    category: str = Field(
        description="Change category. One of: dimension_change, addition, removal, relabel, title_block_change, layout_change, fixture_change, structural_change, other"
    )
    entity_name: str = Field(description="Name or identifier of the changed entity")
    location: Optional[str] = Field(default=None, description="Free text location description")
    old_value: Optional[str] = Field(default=None, description="Old value from baseline drawing")
    new_value: Optional[str] = Field(default=None, description="New value from revised drawing")
    description: str = Field(description="Human-readable description of what changed")


# ── Track B: Visual Pass Records (visual-only, needs review) ──────────────────

class TrackBChange(BaseModel):
    source: Literal["visual"] = Field(default="visual", description="Track B: produced by whole-image visual comparison pass")
    confidence_tier: Literal["needs_review"] = Field(default="needs_review", description="Track B changes always need human review — not grounded in labeled text")
    category: str = Field(
        description="Change category. One of: geometry_change, structural_change, symbol_change, layout_change, addition, removal, fixture_change, other"
    )
    location: str = Field(description="Free text location description (required for visual track since no labeled anchor exists)")
    description: str = Field(description="Human-readable description of the visual change observed")
    old_value: None = Field(default=None, description="Not applicable for visual-only changes")
    new_value: None = Field(default=None, description="Not applicable for visual-only changes")


# ── Diff-Driven ROI Patch Audit Schemas (Step 4 Universal VLM Inspection) ─────

class ROIPatchAuditResult(BaseModel):
    is_change: bool = Field(
        description="True if a genuine engineering revision occurred. False if identical or non-informational noise/slight alignment shift."
    )
    discipline: str = Field(
        description="Detected domain (e.g. Architectural, Mechanical, Electrical, Civil, P&ID)"
    )
    category: Literal[
        "dimensional_change",
        "geometry_change",
        "symbol_change",
        "text_annotation",
        "title_block",
        "addition",
        "deletion"
    ] = Field(description="Classification of the detected change")
    baseline_value: str = Field(
        description="Exact text, number, or description in Crop 1 (Baseline Revision), or 'None' if added"
    )
    current_value: str = Field(
        description="Exact text, number, or description in Crop 2 (Current Revision), or 'None' if deleted"
    )
    description: str = Field(
        description="Engineering-grade explanation of the change and its functional impact"
    )


class ROIPatchChange(BaseModel):
    id: str = Field(description="Unique change identifier (e.g. CHG-001)")
    source: Literal["roi_diff"] = Field(default="roi_diff", description="Diff-driven ROI patch architecture")
    confidence_tier: Literal["high", "needs_review"] = Field(default="high")
    discipline: str = Field(description="Engineering discipline")
    category: str = Field(description="Change category")
    location: str = Field(description="Location description or grid reference (kept per schema requirement)")
    norm_bbox: Optional[dict] = Field(default=None, description="Normalized bounding box coordinates {x, y, w, h} (0.0 to 1.0)")
    baseline_value: Optional[str] = Field(default=None, description="Baseline value from Crop 1")
    current_value: Optional[str] = Field(default=None, description="Current value from Crop 2")
    old_value: Optional[str] = Field(default=None, description="Alias of baseline_value for frontend compat")
    new_value: Optional[str] = Field(default=None, description="Alias of current_value for frontend compat")
    description: str = Field(description="Engineering description of the change")
    is_change: bool = Field(default=True)


# ── Combined Result ───────────────────────────────────────────────────────────

class HybridComparisonResult(BaseModel):
    summary: str = Field(description="Executive summary of all verified engineering changes across the drawing page")
    changes: list[Union[ROIPatchChange, TrackAChange, TrackBChange]] = Field(default_factory=list, description="List of verified ROI patch changes")


# ── Inventory Extraction VLM Response ────────────────────────────────────────

class InventoryExtractionResult(BaseModel):
    summary: str = Field(description="One-sentence summary of what this drawing shows")
    entries: list[InventoryEntry] = Field(default_factory=list, description="Complete inventory of labeled entities")


# ── Track B VLM Response ─────────────────────────────────────────────────────

class VisualChangeEntry(BaseModel):
    category: str = Field(description="One of: geometry_change, structural_change, symbol_change, layout_change, addition, removal, fixture_change, other")
    location: str = Field(description="Where on the drawing this change is located (free text)")
    description: str = Field(description="What visually changed")


class VisualComparisonResult(BaseModel):
    visual_summary: str = Field(description="Brief summary of visual differences found (or 'No visual-only changes detected')")
    visual_changes: list[VisualChangeEntry] = Field(default_factory=list, description="List of unlabeled/geometric/structural visual changes")


# ── Other API Schemas ─────────────────────────────────────────────────────────

class AskRequest(BaseModel):
    report_id: str
    question: str


class ChangeReviewRequest(BaseModel):
    status: Literal["confirmed", "false_positive"]
    note: Optional[str] = None
    reviewer_id: Optional[str] = None


class QAResponse(BaseModel):
    answer: str = Field(description="A direct answer to the user's question, based only on the provided changes list")
    referenced_change_indices: list[int] = Field(
        description="Indices (position in the changes list, 0-based) of the specific changes this answer is based on. Empty list if none apply."
    )


class CreateDrawingRequest(BaseModel):
    name: Optional[str] = Field(default=None, description="Optional display name; defaults to 'Untitled Drawing'")


class RenameDrawingRequest(BaseModel):
    name: str = Field(min_length=1, description="New display name for the drawing")


class DrawingSettingsRequest(BaseModel):
    # Page matcher tuning — still relevant
    min_title_match_score: Optional[float] = None
    min_title_ocr_confidence: Optional[float] = None
    min_title_words: Optional[int] = None
    # Title block region (page_matcher + extraction)
    title_block_x_pct: Optional[float] = None
    title_block_y_pct: Optional[float] = None
    title_block_w_pct: Optional[float] = None
    title_block_h_pct: Optional[float] = None
    # Page size / rendering quality
    page_size_mismatch_threshold: Optional[float] = None
    target_physical_width_inches: Optional[float] = None
    # NOTE: min_ocr_confidence and visual_change_threshold removed —
    # those tuned the old CV alignment/diff pipeline which no longer exists.


# ── Legacy aliases (kept for backward compat on old stored data reads) ────────
# These are NOT used by the new pipeline, but old reports stored in DB may
# reference these category/field shapes; the frontend reads generically.
EntityChange = TrackAChange   # soft alias for old code that might still import it
WholeImageComparisonResult = HybridComparisonResult  # soft alias
RegionResult = TrackAChange
BatchClassification = HybridComparisonResult
