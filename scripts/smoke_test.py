"""Exercise the running stack, leaving small labeled fixtures visible in the UI.

Run with the backend virtualenv: python scripts/smoke_test.py
The EICAR test string is constructed in memory; it is never a local executable.
"""
import io
import json
import sys
import tempfile
import zipfile
from pathlib import Path
import geopandas as gpd
import httpx
from shapely.geometry import Polygon

base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
client = httpx.Client(base_url=base, timeout=180)
results = []


def upload(name, data, expected_status, expected_code=None):
    response = client.post("/api/files/", files={"file": (name, data)})
    response.raise_for_status()
    result = response.json()
    assert result["status"] == expected_status, result
    assert result["error_code"] == expected_code, result
    results.append({"filename": name, "status": result["status"], "error_code": result["error_code"], "id": result["id"]})
    return result


assert client.get("/health").json() == {"status":"ok"}
kml = (Path(__file__).resolve().parents[1] / "backend/tests/fixtures/valid/survey.kml").read_bytes()
file = upload("survey.kml", kml, "COMPLETED")
assert file["feature_count"] == 3
measurements = client.get(f"/api/files/{file['id']}/measurements/").json()
assert measurements["total"] == 3
assert len([f for f in measurements["items"] if f["measurement"]]) == 2
with tempfile.TemporaryDirectory() as temp:
    directory = Path(temp)
    frame = gpd.GeoDataFrame({"name":["10,000 m2 test parcel"], "geometry":[Polygon([(500000,0),(500100,0),(500100,100),(500000,100)])]}, crs=32643)
    frame.to_file(directory / "parcel.shp", engine="pyogrio")
    def archive(exclude=None):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as out:
            for path in directory.iterdir():
                if path.suffix != exclude:
                    out.write(path, path.name)
        return buffer.getvalue()
    file = upload("parcel.zip", archive(), "COMPLETED")
    assert abs(file["summary"]["total_area_m2"] - 10000) < .01
    upload("missing-shx.zip", archive(".shx"), "PROCESSING_FAILED", "SHAPEFILE_COMPONENT_MISSING")
    upload("missing-crs.zip", archive(".prj"), "PROCESSING_FAILED", "CRS_MISSING")
unsafe = io.BytesIO()
with zipfile.ZipFile(unsafe, "w") as out:
    out.writestr("../outside.shp", "invalid")
upload("unsafe-path.zip", unsafe.getvalue(), "PROCESSING_FAILED", "INVALID_ARCHIVE")
# Standard inert antivirus test marker. Send only to the local test deployment.
eicar = bytes.fromhex("58354f2150254041505b345c505a58353428505e2937434329377d2445494341522d5354414e444152442d414e544956495255532d544553542d46494c452124482b482a")
upload("antivirus-test.kml", eicar, "REJECTED", "MALWARE_DETECTED")
response = client.post("/api/files/", files={"file": ("unsupported.txt", b"test")})
assert response.status_code == 422
assert response.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"
assert client.get("/api/files/?page_size=101").status_code == 422
print(json.dumps({"passed": True, "uploads": results}, indent=2))
