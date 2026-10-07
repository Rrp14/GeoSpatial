from pyproj import CRS
from app.core.exceptions import AppError


def validate_crs(value):
    if not value:
        raise AppError("CRS_MISSING", "The uploaded dataset does not define a coordinate reference system.")
    try:
        crs = CRS.from_user_input(value)
        if not (crs.is_projected or crs.is_geographic):
            raise ValueError()
        return crs
    except Exception:
        raise AppError("CRS_INVALID", "The dataset CRS is not supported.") from None
