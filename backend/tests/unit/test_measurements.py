import pytest
from pyproj import CRS
from shapely.geometry import Polygon, LineString, Point, GeometryCollection, MultiPolygon
from app.services.crs_service import validate_crs
from app.services.measurement_service import measure
from app.geo.measurement.strategy_selector import select_strategy, Strategy
from app.core.exceptions import AppError


def test_crs_missing_and_invalid():
    for value, code in [(None, "CRS_MISSING"), ("nonsense", "CRS_INVALID")]:
        with pytest.raises(AppError) as exc:
            validate_crs(value)
        assert exc.value.code == code


def test_projected_area_and_length(frame):
    source = CRS(32643)
    strategy = Strategy("PROJECTED", source)
    assert measure(frame.geometry[0], source, strategy)[2]["value"] == pytest.approx(10000)
    assert measure(frame.geometry[1], source, strategy)[2]["value"] == pytest.approx(5)


def test_geodesic_known_values():
    source, strategy = CRS(4326), Strategy("GEODESIC")
    line = LineString([(0, 0), (1, 0)])
    assert measure(line, source, strategy)[2]["value"] == pytest.approx(111319.49, abs=.1)
    square = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    assert measure(square, source, strategy)[2]["value"] == pytest.approx(12308778361, rel=1e-7)
    reverse = Polygon(list(square.exterior.coords)[::-1])
    assert measure(reverse, source, strategy)[2]["value"] == pytest.approx(measure(square, source, strategy)[2]["value"])


def test_holes_and_multipart_orientation():
    outer = [(0,0),(2,0),(2,2),(0,2)]
    hole = [(.5,.5),(1.5,.5),(1.5,1.5),(.5,1.5)]
    source, strategy = CRS(4326), Strategy("GEODESIC")
    area = lambda g: measure(g, source, strategy)[2]["value"]
    assert area(Polygon(outer, [hole])) == pytest.approx(area(Polygon(outer)) - area(Polygon(hole)))
    second = Polygon([(3,0),(3,1),(4,1),(4,0)])
    assert area(MultiPolygon([Polygon(outer), second])) == pytest.approx(area(Polygon(outer)) + area(second))


@pytest.mark.parametrize("geometry,status", [(None,"EMPTY"),(Point(),"EMPTY"),(Point(0,0),"OK"),(GeometryCollection([Point(0,0)]),"UNSUPPORTED"),(Polygon([(0,0),(1,1),(1,0),(0,1)]),"INVALID")])
def test_feature_statuses(geometry, status):
    result = measure(geometry, CRS(4326), Strategy("GEODESIC"))
    assert result[0] == status
    assert result[2] is None


def test_selection():
    assert select_strategy(CRS(4326), [77, 12, 77.2, 12.2]).target.to_epsg() == 32643
    assert select_strategy(CRS(4326), [5.9, 12, 6.1, 12.2]).method == "GEODESIC"
    assert select_strategy(CRS(4326), [-100, 10, 100, 70]).method == "GEODESIC"
    assert select_strategy(CRS(4326), [10, 85, 11, 86]).method == "GEODESIC"
    assert select_strategy(CRS(3857), [-100, 10, 100, 70]).method == "GEODESIC"


def test_out_of_range_and_ambiguous_polygon():
    assert measure(LineString([(0,91),(1,92)]), CRS(4326), Strategy("GEODESIC"))[0] == "INVALID"
    assert measure(Polygon([(-179,0),(179,0),(179,1),(-179,1)]), CRS(4326), Strategy("GEODESIC"))[0] == "UNSUPPORTED"
