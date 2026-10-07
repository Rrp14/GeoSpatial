import io
import zipfile
from contextlib import contextmanager
import pytest
import geopandas as gpd
from shapely.geometry import Polygon, LineString, Point
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.core.config import Settings
from app.db.base import Base
from app.repositories.file_repository import FileRepository
from app.core.exceptions import AppError


@pytest.fixture
def settings():
    return Settings(database_url="sqlite://", max_upload_size_mb=1, max_archive_uncompressed_mb=1)


@pytest.fixture
def repo():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield FileRepository(session)
    engine.dispose()


@pytest.fixture
def frame():
    return gpd.GeoDataFrame({"name": ["Plot A", "Road", "Marker"], "geometry": [Polygon([(500000, 0), (500100, 0), (500100, 100), (500000, 100)]), LineString([(500000, 0), (500003, 4)]), Point(500010, 10)]}, crs=32643)


class MemoryStorage:
    def __init__(self):
        self.quarantine, self.clean = {}, {}

    def upload(self, key, stream, size):
        self.quarantine[key] = stream.read()

    @contextmanager
    def open(self, key, clean=False):
        yield io.BytesIO((self.clean if clean else self.quarantine)[key])

    def promote(self, key):
        self.clean[key] = self.quarantine[key]


class FakeScanner:
    def __init__(self, error=None):
        self.error = error
        self.calls = 0

    def scan(self, stream):
        self.calls += 1
        if self.error:
            raise AppError(self.error, "Test scan failure.", 503)


@pytest.fixture
def storage():
    return MemoryStorage()


def make_zip(path, entries):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return path
