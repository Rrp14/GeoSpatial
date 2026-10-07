import json
import logging
from sqlalchemy import select, func
from app.models.entities import UploadedFile, Feature, ProcessingEvent
from app.core.logging import request_id

logger = logging.getLogger("geomeasure")

TRANSITIONS = {
    "UPLOADING": {"QUARANTINED", "PROCESSING_FAILED"},
    "QUARANTINED": {"SCANNING", "PROCESSING_FAILED"},
    "SCANNING": {"CLEAN", "QUARANTINED", "REJECTED", "PROCESSING_FAILED"},
    "CLEAN": {"VALIDATING", "PROCESSING_FAILED"},
    "VALIDATING": {"PROCESSING", "PROCESSING_FAILED"},
    "PROCESSING": {"COMPLETED", "PROCESSING_FAILED"},
}


class FileRepository:
    def __init__(self, session):
        self.session = session

    def get(self, file_id):
        return self.session.get(UploadedFile, file_id)

    def create(self, record):
        self.session.add(record)
        self.session.commit()

    def transition(self, record, status, **values):
        if status not in TRANSITIONS.get(record.status, set()):
            raise ValueError("Invalid file lifecycle transition.")
        record.status = status
        for key, value in values.items():
            setattr(record, key, value)
        self.session.add(ProcessingEvent(file_id=record.id, stage=status, message=values.get("error_code") or status))
        self.session.commit()
        logger.info(json.dumps({"request_id": request_id.get(), "file_id": record.id, "stage": status, "status": status, "error_code": record.error_code}))

    def list(self, page, size):
        query = select(UploadedFile).order_by(UploadedFile.created_at.desc(), UploadedFile.id)
        return list(self.session.scalars(query.offset((page - 1) * size).limit(size))), self.session.scalar(select(func.count()).select_from(UploadedFile))

    def features(self, file_id, page, size, geometry_type):
        query = select(Feature).where(Feature.file_id == file_id)
        if geometry_type:
            query = query.where(Feature.geometry_type == geometry_type)
        total = self.session.scalar(select(func.count()).select_from(query.subquery()))
        return list(self.session.scalars(query.order_by(Feature.feature_index).offset((page - 1) * size).limit(size))), total
