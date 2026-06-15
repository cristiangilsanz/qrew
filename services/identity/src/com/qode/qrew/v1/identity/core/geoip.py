import math

import geoip2.database
import structlog

logger = structlog.get_logger(__name__)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute the great-circle distance in kilometres between two points."""
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + (
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class GeoIpService:
    """Resolve an IP address to an approximate geolocation."""

    def __init__(self, db_path: str) -> None:
        self._reader: geoip2.database.Reader | None = None
        try:
            self._reader = geoip2.database.Reader(db_path)
        except Exception:
            logger.warning("geoip_db_not_loaded", path=db_path)

    def locate(self, ip: str) -> tuple[float, float] | None:
        """Resolve an IP to a latitude and longitude."""
        if self._reader is None:
            return None
        try:
            response = self._reader.city(ip)
            lat = response.location.latitude
            lon = response.location.longitude
            if lat is None or lon is None:
                return None
            return (float(lat), float(lon))
        except Exception:
            return None

    def distance_km(
        self,
        loc1: tuple[float, float],
        loc2: tuple[float, float],
    ) -> float:
        """Return the distance in kilometres between two locations."""
        return haversine_km(loc1[0], loc1[1], loc2[0], loc2[1])
