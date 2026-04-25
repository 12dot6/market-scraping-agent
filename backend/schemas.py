from datetime import datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str


# ---------------------------------------------------------------------------
# Job schemas
# ---------------------------------------------------------------------------

class JobCreate(BaseModel):
    urls: list[str] = Field(min_length=1)


class JobCreated(BaseModel):
    job_id: str


class JobSummary(BaseModel):
    id: str
    status: str  # queued | running | complete | failed
    url_count: int
    processed: int
    in_scope: int
    excluded: int
    errors: int
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class JobDetail(JobSummary):
    started_at: datetime | None


# ---------------------------------------------------------------------------
# Product / ingredient schemas
# ---------------------------------------------------------------------------

class IngredientItem(BaseModel):
    name: str
    internal_name: str | None
    component: str
    is_dye_active: bool


class ProductResult(BaseModel):
    id: str
    url: str
    name: str
    in_scope: bool
    scope_reason: str | None
    ingredients: list[IngredientItem]
    error: str | None


# ---------------------------------------------------------------------------
# Generic raw responses (used for internal tooling / future use)
# ---------------------------------------------------------------------------

class JobResponse(BaseModel):
    id: str
    status: str
    url_count: int
    processed: int
    in_scope: int
    excluded: int
    errors: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class ProductResponse(BaseModel):
    id: str
    job_id: str
    url: str
    name: str
    ingredients_raw: str
    in_scope: bool
    scope_reason: str | None
    error: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class IngredientResponse(BaseModel):
    id: int
    name: str
    internal_name: str | None
    count: int
    is_dye_active: bool

    model_config = {"from_attributes": True}


class ProductIngredientResponse(BaseModel):
    product_id: str
    ingredient_id: int
    component: str
    is_dye_active: bool

    model_config = {"from_attributes": True}
