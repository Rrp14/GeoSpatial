from uuid import UUID
from fastapi import APIRouter, Depends, File, Query, UploadFile
from app.api.dependencies import get_processor, get_repository
from app.core.exceptions import AppError
from app.schemas.file import FileResponse, FilePage
from app.schemas.measurement import MeasurementPage

router = APIRouter(prefix="/api/files", tags=["files"])


def find_file(repo, file_id):
    record = repo.get(str(file_id))
    if not record:
        raise AppError("FILE_NOT_FOUND", "The requested file does not exist.", 404)
    return record


@router.post("/", response_model=FileResponse, status_code=201)
def upload(file: UploadFile = File(...), processor=Depends(get_processor)):
    # Starlette's bounded multipart spool is transient transport, not durable upload storage.
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    return processor.upload(file.filename, file.file, size)


@router.get("/", response_model=FilePage)
def list_files(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), repo=Depends(get_repository)):
    items, total = repo.list(page, page_size)
    return dict(items=items, total=total, page=page, page_size=page_size)


@router.get("/{file_id}/", response_model=FileResponse)
def details(file_id: UUID, repo=Depends(get_repository)):
    return find_file(repo, file_id)


@router.get("/{file_id}/measurements/", response_model=MeasurementPage)
def measurements(file_id: UUID, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100), geometry_type: str | None = Query(None, max_length=40), repo=Depends(get_repository)):
    record = find_file(repo, file_id)
    items, total = repo.features(record.id, page, page_size, geometry_type)
    for item in items:
        if item.measurement:
            item.measurement.source_crs = record.source_crs
    return dict(items=items, total=total, source_crs=record.source_crs, page=page, page_size=page_size)
