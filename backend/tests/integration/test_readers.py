import zipfile
from pathlib import Path
import pytest
from app.geo.readers.dataset_reader import read_dataset
from app.core.exceptions import AppError


def test_real_kml_reader(tmp_path, settings):
    path = Path(__file__).parents[1] / "fixtures" / "valid" / "survey.kml"
    frame = read_dataset(path, "KML", tmp_path, settings)
    assert len(frame) == 3
    assert frame.crs.to_epsg() == 4326
    assert set(frame.geom_type) == {"Polygon", "LineString", "Point"}


def test_real_shapefile_reader(tmp_path, settings, frame):
    shape = tmp_path / "parcel.shp"
    frame.iloc[:1].to_file(shape, engine="pyogrio")
    archive = tmp_path / "parcel.zip"
    with zipfile.ZipFile(archive, "w") as output:
        for component in tmp_path.glob("parcel.*"):
            if component.suffix != ".zip":
                output.write(component, component.name)
    result = read_dataset(archive, "SHAPEFILE_ZIP", tmp_path / "work", settings)
    assert len(result) == 1
    assert result.crs.to_epsg() == 32643


@pytest.mark.parametrize("content", ['<!DOCTYPE kml [<!ENTITY ext SYSTEM "file:///etc/passwd">]><kml>&ext;</kml>', '<kml><NetworkLink><Link><href>http://example.com</href></Link></NetworkLink></kml>'])
def test_kml_external_resources_rejected(tmp_path, settings, content):
    path = tmp_path / "bad.kml"
    path.write_text(content)
    with pytest.raises(AppError, match="safe XML"):
        read_dataset(path, "KML", tmp_path, settings)
