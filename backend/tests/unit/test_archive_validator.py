import stat
import zipfile
import pytest
from app.core.exceptions import AppError
from app.geo.validation.archive_validator import extract_shapefile
from conftest import make_zip

BASE = {"parcel.shp": "x", "parcel.shx": "x", "parcel.dbf": "x", "parcel.prj": "x"}


@pytest.mark.parametrize("name", ["../evil.shp", "/evil.shp", "a\\evil.shp", "C:evil.shp", "a/../../evil.shp", "a./evil.shp"])
def test_unsafe_paths(tmp_path, settings, name):
    path = make_zip(tmp_path / "bad.zip", {**BASE, name: "bad"})
    with pytest.raises(AppError):
        extract_shapefile(path, tmp_path / "out", settings)


def test_components_and_crs(tmp_path, settings):
    for missing, code in [("parcel.shx", "SHAPEFILE_COMPONENT_MISSING"), ("parcel.prj", "CRS_MISSING")]:
        path = make_zip(tmp_path / "bad.zip", {k: v for k, v in BASE.items() if k != missing})
        with pytest.raises(AppError) as exc:
            extract_shapefile(path, tmp_path / "out", settings)
        assert exc.value.code == code


def test_limits(tmp_path, settings):
    settings.max_archive_files = 3
    path = make_zip(tmp_path / "many.zip", BASE)
    with pytest.raises(AppError) as exc:
        extract_shapefile(path, tmp_path / "out", settings)
    assert exc.value.code == "ARCHIVE_TOO_LARGE"
    settings.max_archive_files = 100
    path = make_zip(tmp_path / "large.zip", {**BASE, "parcel.dbf": "a" * (1024 * 1024 + 1)})
    with pytest.raises(AppError) as exc:
        extract_shapefile(path, tmp_path / "out", settings)
    assert exc.value.code == "ARCHIVE_TOO_LARGE"


def test_single_dataset_and_duplicates(tmp_path, settings):
    for entries in [{**BASE, "other.shp": "x"}, {**BASE, "PARCEL.SHP": "x"}]:
        with pytest.raises(AppError):
            extract_shapefile(make_zip(tmp_path / "bad.zip", entries), tmp_path / "out", settings)


def test_symlink(tmp_path, settings):
    path = make_zip(tmp_path / "bad.zip", BASE)
    with zipfile.ZipFile(path, "a") as archive:
        member = zipfile.ZipInfo("link.shp")
        member.create_system = 3
        member.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(member, "parcel.shp")
    with pytest.raises(AppError, match="Links"):
        extract_shapefile(path, tmp_path / "out", settings)


def test_nested_uppercase_dataset(tmp_path, settings):
    path = make_zip(tmp_path / "valid.zip", {"Survey/" + k.upper(): v for k, v in BASE.items()})
    result = extract_shapefile(path, tmp_path / "out", settings)
    assert result.is_file()
    assert result.name == "parcel.shp"
