from geoalchemy2 import WKTElement
from geoalchemy2.shape import to_shape


def make_point(lat: float, lon: float) -> WKTElement:
    return WKTElement(f"POINT({lon} {lat})", srid=4326)


def point_to_latlon(location) -> tuple[float, float] | None:
    if location is None:
        return None
    shape = to_shape(location)
    return shape.y, shape.x
