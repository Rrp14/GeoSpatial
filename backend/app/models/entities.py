import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, ForeignKey, JSON, DateTime, Float, Integer, BigInteger, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


def now():
    return datetime.now(timezone.utc)


def uid():
    return str(uuid.uuid4())


json_type = JSON().with_variant(JSONB, "postgresql")


class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uid)
    original_filename: Mapped[str] = mapped_column(String(255))
    object_key: Mapped[str] = mapped_column(String(100))
    file_type: Mapped[str] = mapped_column(String(30))
    file_size_bytes: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(30), default="UPLOADING", index=True)
    source_crs: Mapped[str | None] = mapped_column(Text)
    measurement_crs: Mapped[str | None] = mapped_column(Text)
    measurement_method: Mapped[str | None] = mapped_column(String(30))
    feature_count: Mapped[int | None] = mapped_column(Integer)
    bbox: Mapped[list | None] = mapped_column(json_type)
    warnings: Mapped[list] = mapped_column(json_type, default=list)
    summary: Mapped[dict] = mapped_column(json_type, default=dict)
    error_code: Mapped[str | None] = mapped_column(String(60))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    scan_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Feature(Base):
    __tablename__ = "features"
    __table_args__ = (UniqueConstraint("file_id", "feature_index"),)
    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uid)
    file_id: Mapped[str] = mapped_column(ForeignKey("uploaded_files.id", ondelete="CASCADE"), index=True)
    feature_index: Mapped[int] = mapped_column(Integer)
    source_feature_id: Mapped[str | None] = mapped_column(String(255))
    geometry_type: Mapped[str] = mapped_column(String(40))
    geometry_json: Mapped[dict | None] = mapped_column(json_type)
    properties: Mapped[dict] = mapped_column(json_type)
    status: Mapped[str] = mapped_column(String(30))
    warning: Mapped[str | None] = mapped_column(Text)
    measurement: Mapped["Measurement | None"] = relationship(lazy="selectin", cascade="all, delete-orphan")


class Measurement(Base):
    __tablename__ = "measurements"
    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uid)
    feature_id: Mapped[str] = mapped_column(ForeignKey("features.id", ondelete="CASCADE"), unique=True)
    measurement_type: Mapped[str] = mapped_column(String(20))
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(10))
    method: Mapped[str] = mapped_column(String(30))
    measurement_crs: Mapped[str | None] = mapped_column(Text)
    ellipsoid: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(30), default="OK")
    warning: Mapped[str | None] = mapped_column(Text)


class ProcessingEvent(Base):
    __tablename__ = "processing_events"
    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uid)
    file_id: Mapped[str] = mapped_column(ForeignKey("uploaded_files.id", ondelete="CASCADE"), index=True)
    stage: Mapped[str] = mapped_column(String(30))
    level: Mapped[str] = mapped_column(String(10), default="INFO")
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
