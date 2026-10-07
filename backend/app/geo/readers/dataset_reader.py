import geopandas as gpd
import pyogrio
from defusedxml import ElementTree
from app.core.exceptions import AppError
from app.geo.validation.archive_validator import extract_shapefile


def read_dataset(path, file_type, directory, settings):
    if file_type == "SHAPEFILE_ZIP":
        path = extract_shapefile(path, directory / "extracted", settings)
        driver = "ESRI Shapefile"
    else:
        driver = "KML"
        try:
            root = ElementTree.parse(path).getroot()
            if root.tag.split("}")[-1] != "kml":
                raise ValueError()
            for element in root.iter():
                if element.tag.split("}")[-1] in {"NetworkLink", "Link", "href"}:
                    raise ValueError()
        except Exception:
            raise AppError("INVALID_KML", "KML must be safe XML without external resources.") from None
    try:
        layers = pyogrio.list_layers(path)
        frames = []
        count = 0
        for layer, _ in layers:
            info = pyogrio.read_info(path, layer=layer)
            if info["driver"] not in ({"KML", "LIBKML"} if driver == "KML" else {driver}):
                raise AppError("INVALID_DATASET", "The dataset driver does not match its file type.")
            frame = gpd.read_file(path, layer=layer, engine="pyogrio", rows=settings.max_features + 1, fid_as_index=True)
            count += len(frame)
            if count > settings.max_features:
                raise AppError("TOO_MANY_FEATURES", "Dataset exceeds the feature limit.")
            frame["_source_id"] = [f"{layer}:{index}" for index in frame.index]
            frames.append(frame)
        if not frames or not count:
            raise AppError("EMPTY_DATASET", "The dataset contains no features.")
        import pandas as pd
        if any(f.crs != frames[0].crs for f in frames):
            raise AppError("CRS_INVALID", "Dataset layers use inconsistent CRS definitions.")
        return gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=frames[0].crs)
    except AppError:
        raise
    except Exception:
        raise AppError("INVALID_DATASET", "The geospatial dataset could not be read.") from None
