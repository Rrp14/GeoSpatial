import math
import numpy as np
from pyproj import Transformer, Geod
from shapely import get_coordinates
from shapely.geometry.polygon import orient
from shapely.ops import transform
from shapely.validation import explain_validity


def measure(geometry, source, strategy):
    if geometry is None or geometry.is_empty:
        return "EMPTY", "Geometry is null or empty.", None
    if not np.isfinite(get_coordinates(geometry)).all():
        return "INVALID", "Geometry contains non-finite coordinates.", None
    if not geometry.is_valid:
        return "INVALID", explain_validity(geometry), None
    kind = geometry.geom_type
    if kind in ("Point", "MultiPoint"):
        return "OK", None, None
    if kind not in ("Polygon", "MultiPolygon", "LineString", "MultiLineString"):
        return "UNSUPPORTED", "Geometry type is not supported in V1.", None
    area = kind in ("Polygon", "MultiPolygon")
    try:
        if strategy.method == "PROJECTED":
            projected = transform(Transformer.from_crs(source, strategy.target, always_xy=True).transform, geometry)
            value = projected.area if area else projected.length
        else:
            geo = transform(Transformer.from_crs(source, 4326, always_xy=True).transform, geometry)
            coords = get_coordinates(geo)
            if not np.isfinite(coords).all() or (abs(coords[:, 1]) > 90).any() or (abs(coords[:, 0]) > 180).any():
                return "INVALID", "Coordinates fall outside geographic bounds.", None
            geod = Geod(ellps="WGS84")
            if area:
                # Geod returns signed areas only up to half the globe. Refuse ambiguous huge polygons.
                if geo.bounds[2] - geo.bounds[0] > 180:
                    return "UNSUPPORTED", "Polygon spans the antimeridian or over 180 degrees; split it before measuring.", None
                pieces = geo.geoms if kind == "MultiPolygon" else [geo]
                value = sum(abs(geod.geometry_area_perimeter(orient(p, sign=1))[0]) for p in pieces)
            else:
                value = geod.geometry_length(geo)
        if not math.isfinite(value):
            raise ValueError()
        return "OK", None, {"measurement_type": "AREA" if area else "LENGTH", "value": value, "unit": "m2" if area else "m", "method": strategy.method, "measurement_crs": strategy.target.to_string() if strategy.target else None, "ellipsoid": "WGS84" if strategy.method == "GEODESIC" else None}
    except Exception:
        return "INVALID", "Geometry cannot be measured safely in the selected CRS.", None
