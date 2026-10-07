import math
from dataclasses import dataclass
from pyproj import CRS


@dataclass
class Strategy:
    method: str
    target: CRS | None = None


def select_strategy(source, geographic_bounds):
    west, south, east, north = geographic_bounds
    # Only directly trust metre-based UTM inside its documented area of use.
    # Web Mercator is not suitable for physical measurement.
    if source.is_projected and source.utm_zone and source.area_of_use and all(abs(a.unit_conversion_factor - 1) < 1e-9 for a in source.axis_info[:2]):
        bounds = source.area_of_use.bounds
        if bounds[0] <= west <= east <= bounds[2] and bounds[1] <= south <= north <= bounds[3]:
            return Strategy("PROJECTED", source)
    if all(math.isfinite(v) for v in geographic_bounds) and -80 <= south <= north <= 84 and -180 <= west <= east <= 180:
        zone = lambda x: min(60, max(1, int((x + 180) // 6) + 1))
        if east - west <= 3 and north - south <= 3 and zone(west) == zone(east) and south * north >= 0:
            code = (32600 if (south + north) / 2 >= 0 else 32700) + zone((west + east) / 2)
            return Strategy("PROJECTED", CRS.from_epsg(code))
    return Strategy("GEODESIC")
