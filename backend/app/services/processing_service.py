import json
import logging
import math
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4
from shapely.geometry import mapping
from app.core.exceptions import AppError
from app.core.logging import request_id
from app.models.entities import UploadedFile, Feature, Measurement, now
from app.geo.readers.dataset_reader import read_dataset
from app.geo.measurement.strategy_selector import select_strategy
from app.services.crs_service import validate_crs
from app.services.measurement_service import measure


def json_safe(value):
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if hasattr(value, "item"):
        return json_safe(value.item())
    return str(value)


class ProcessingService:
    """Synchronous use case; accepts a binary stream and has no HTTP dependency."""
    def __init__(self, repository, storage, scanner, settings, reader=read_dataset):
        self.repo, self.storage, self.scanner, self.settings, self.reader = repository, storage, scanner, settings, reader

    def upload(self, filename, stream, size):
        started = time.monotonic()
        extension = Path(filename or "").suffix.lower()
        if not filename or len(filename) > 255 or extension not in (".kml", ".zip"):
            raise AppError("UNSUPPORTED_FILE_TYPE", "Select a .kml file or a Shapefile .zip archive.")
        if size <= 0:
            raise AppError("EMPTY_FILE", "The uploaded file is empty.")
        if size > self.settings.max_upload_size_mb * 1024 * 1024:
            raise AppError("FILE_TOO_LARGE", "The upload exceeds the configured size limit.", 413)
        file_id = str(uuid4())
        record = UploadedFile(id=file_id, original_filename=filename, object_key=f"{file_id}/original{extension}", file_size_bytes=size, file_type="KML" if extension == ".kml" else "SHAPEFILE_ZIP")
        self.repo.create(record)
        try:
            self.storage.upload(record.object_key, stream, size)
            self.repo.transition(record, "QUARANTINED")
            self.repo.transition(record, "SCANNING")
            with self.storage.open(record.object_key) as source:
                self.scanner.scan(source)
            self.repo.transition(record, "CLEAN", scan_completed_at=now())
            self.storage.promote(record.object_key)
            self.repo.transition(record, "VALIDATING")
            # Only scanned objects are materialized locally; temporary files are removed on every exit.
            with TemporaryDirectory(prefix="geomeasure-") as temp:
                directory = Path(temp)
                path = directory / ("input" + extension)
                with self.storage.open(record.object_key, clean=True) as source, path.open("wb") as output:
                    copied = 0
                    while chunk := source.read(65536):
                        copied += len(chunk)
                        if copied > self.settings.max_upload_size_mb * 1024 * 1024:
                            raise AppError("FILE_TOO_LARGE", "Stored object exceeds upload limit.")
                        output.write(chunk)
                frame = self.reader(path, record.file_type, directory, self.settings)
                source_crs = validate_crs(frame.crs)
                valid = frame.geometry.notna() & ~frame.geometry.is_empty & frame.geometry.is_valid
                bounds = frame.loc[valid].to_crs(4326).total_bounds if valid.any() else [0, 0, 180, 90]
                strategy = select_strategy(source_crs, bounds)
                self.repo.transition(record, "PROCESSING", processing_started_at=now())
                summary = {"polygons": 0, "lines": 0, "points": 0, "total_area_m2": 0.0, "total_length_m": 0.0, "warnings": 0}
                for index, (_, row) in enumerate(frame.iterrows()):
                    geometry = row.geometry
                    status, warning, result = measure(geometry, source_crs, strategy)
                    kind = geometry.geom_type if geometry is not None else "Null"
                    properties = row.drop(labels=[frame.geometry.name, "_source_id"], errors="ignore").to_dict()
                    feature = Feature(file_id=record.id, feature_index=index, source_feature_id=str(row.get("_source_id", index)), geometry_type=kind, geometry_json=json_safe(mapping(geometry)) if geometry is not None else None, properties=json_safe(properties), status=status, warning=warning)
                    if result:
                        feature.measurement = Measurement(**result)
                        key = "total_area_m2" if result["measurement_type"] == "AREA" else "total_length_m"
                        summary[key] += result["value"]
                    if "Polygon" in kind:
                        summary["polygons"] += 1
                    elif "LineString" in kind:
                        summary["lines"] += 1
                    elif "Point" in kind:
                        summary["points"] += 1
                    if warning:
                        summary["warnings"] += 1
                    self.repo.session.add(feature)
                warnings = [f"{summary['warnings']} feature(s) have warnings; review their statuses."] if summary["warnings"] else []
                self.repo.transition(record, "COMPLETED", source_crs=source_crs.to_string(), measurement_method=strategy.method, measurement_crs=strategy.target.to_string() if strategy.target else None, feature_count=len(frame), bbox=json_safe(list(bounds)), summary=summary, warnings=warnings, processed_at=now())
        except Exception as exc:
            self.repo.session.rollback()
            error = exc if isinstance(exc, AppError) else AppError("PROCESSING_ERROR", "The file could not be processed.", 500)
            logging.getLogger("geomeasure").error(json.dumps({"file_id": file_id, "stage": record.status, "error_code": error.code, "exception_type": type(exc).__name__}))
            status = "QUARANTINED" if error.code == "SCAN_ERROR" else "REJECTED" if error.code == "MALWARE_DETECTED" else "PROCESSING_FAILED"
            self.repo.transition(record, status, error_code=error.code, error_message=error.message)
        logging.getLogger("geomeasure").info(json.dumps({"request_id": request_id.get(), "file_id": record.id, "stage": "upload_finished", "status": record.status, "duration": round(time.monotonic() - started, 3), "error_code": record.error_code}))
        return record
