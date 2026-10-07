import io
from unittest.mock import Mock
import pytest
from sqlalchemy import select, func
from fastapi.testclient import TestClient
from app.services.processing_service import ProcessingService
from app.core.exceptions import AppError
from app.models.entities import Feature, ProcessingEvent
from conftest import FakeScanner


@pytest.mark.parametrize("code,status", [("SCAN_ERROR", "QUARANTINED"), ("MALWARE_DETECTED", "REJECTED")])
def test_failed_scan_never_parses(repo, storage, settings, code, status):
    reader = Mock()
    service = ProcessingService(repo, storage, FakeScanner(code), settings, reader)
    record = service.upload("sample.kml", io.BytesIO(b"test"), 4)
    assert record.status == status
    assert record.error_code == code
    reader.assert_not_called()
    assert not storage.clean
    assert storage.quarantine


def test_success_persists_results_and_events(repo, storage, settings, frame):
    service = ProcessingService(repo, storage, FakeScanner(), settings, lambda *args: frame)
    record = service.upload("sample.kml", io.BytesIO(b"test"), 4)
    assert record.status == "COMPLETED"
    assert record.feature_count == 3
    assert record.summary["total_area_m2"] == pytest.approx(10000)
    assert record.summary["total_length_m"] == pytest.approx(5)
    assert repo.session.scalar(select(func.count()).select_from(Feature)) == 3
    assert repo.session.scalar(select(func.count()).select_from(ProcessingEvent)) == 6
    assert storage.clean


def test_storage_failure(repo, settings, storage):
    storage.upload = Mock(side_effect=AppError("STORAGE_ERROR", "Unavailable.", 503))
    scanner, reader = FakeScanner(), Mock()
    result = ProcessingService(repo, storage, scanner, settings, reader).upload("a.kml", io.BytesIO(b"x"), 1)
    assert result.error_code == "STORAGE_ERROR"
    assert scanner.calls == 0
    reader.assert_not_called()


def test_promotion_failure_never_parses(repo, settings, storage):
    storage.promote = Mock(side_effect=AppError("STORAGE_ERROR", "Promotion failed.", 503))
    reader = Mock()
    result = ProcessingService(repo, storage, FakeScanner(), settings, reader).upload("a.kml", io.BytesIO(b"x"), 1)
    assert result.error_code == "STORAGE_ERROR"
    reader.assert_not_called()


def test_database_constraint_failure_rolls_back(repo, settings, storage, frame, monkeypatch):
    import app.services.processing_service as module
    def invalid_measurement(*args):
        return "OK", None, {"measurement_type":"AREA", "value":1, "unit":None, "method":"PROJECTED"}
    monkeypatch.setattr(module, "measure", invalid_measurement)
    result = ProcessingService(repo, storage, FakeScanner(), settings, lambda *args: frame).upload("a.kml", io.BytesIO(b"x"), 1)
    assert result.status == "PROCESSING_FAILED"
    assert result.error_code == "PROCESSING_ERROR"
    assert repo.session.scalar(select(func.count()).select_from(Feature)) == 0


def test_feature_transaction_rolls_back(repo, settings, storage, frame, monkeypatch):
    import app.services.processing_service as module
    original = module.measure
    calls = 0
    def broken_measure(*args):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("private details")
        return original(*args)
    monkeypatch.setattr(module, "measure", broken_measure)
    result = ProcessingService(repo, storage, FakeScanner(), settings, lambda *args: frame).upload("a.kml", io.BytesIO(b"x"), 1)
    assert result.status == "PROCESSING_FAILED"
    assert repo.session.scalar(select(func.count()).select_from(Feature)) == 0
    assert "private" not in result.error_message


def test_api_upload_pagination_and_errors(repo, settings, storage, frame):
    from app.main import app
    from app.api.dependencies import get_repository, get_processor
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_processor] = lambda: ProcessingService(repo, storage, FakeScanner(), settings, lambda *args: frame)
    try:
        with TestClient(app) as client:
            response = client.post("/api/files/", files={"file": ("sample.kml", b"test")})
            assert response.status_code == 201, response.text
            file = response.json()
            assert file["filename"] == "sample.kml"
            measurements = client.get(f"/api/files/{file['id']}/measurements/?page_size=1&geometry_type=Polygon").json()
            assert measurements["total"] == 1
            assert measurements["items"][0]["measurement"]["type"] == "AREA"
            assert client.get("/api/files/").json()["total"] == 1
            assert client.get("/api/files/?page_size=101").status_code == 422
            invalid = client.post("/api/files/", files={"file": ("evil.exe", b"test")})
            assert invalid.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"
            assert client.get("/api/files/not-a-uuid/").status_code == 422
    finally:
        app.dependency_overrides.clear()
