from fastapi import Depends
from app.core.config import get_settings
from app.db.session import get_db
from app.repositories.file_repository import FileRepository
from app.services.storage_service import StorageService
from app.services.malware_scan_service import MalwareScanService
from app.services.processing_service import ProcessingService


def get_repository(db=Depends(get_db)):
    return FileRepository(db)


def get_processor(repo=Depends(get_repository), settings=Depends(get_settings)):
    return ProcessingService(repo, StorageService(settings), MalwareScanService(settings), settings)
