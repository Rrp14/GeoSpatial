from pydantic import BaseModel, ConfigDict, Field


class MeasurementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    type: str = Field(validation_alias="measurement_type")
    value: float
    unit: str
    method: str
    source_crs: str | None = None
    measurement_crs: str | None
    ellipsoid: str | None
    status: str
    warning: str | None


class FeatureResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    feature_index: int
    source_feature_id: str | None
    geometry_type: str
    geometry_json: dict | None
    properties: dict
    status: str
    warning: str | None
    measurement: MeasurementResponse | None


class MeasurementPage(BaseModel):
    items: list[FeatureResponse]
    source_crs: str | None
    page: int
    page_size: int
    total: int
