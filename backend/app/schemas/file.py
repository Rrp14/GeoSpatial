from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class FileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    id: str
    filename: str = Field(validation_alias="original_filename")
    file_type: str
    file_size_bytes: int
    status: str
    source_crs: str | None
    measurement_crs: str | None
    measurement_method: str | None
    feature_count: int | None
    bbox: list | None
    warnings: list
    summary: dict
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    scan_completed_at: datetime | None
    processing_started_at: datetime | None
    processed_at: datetime | None


class FilePage(BaseModel):
    items: list[FileResponse]
    page: int
    page_size: int
    total: int
