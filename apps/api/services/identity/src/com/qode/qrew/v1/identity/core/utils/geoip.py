# locates ip addresses and measures the distance between two logins
import math

import geoip2.database
import structlog

logger = structlog.get_logger(__name__)


# computes the great circle distance between two coordinates in kilometres
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + (
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class GeoIpService:
    # opens the geoip database if one is configured
    def __init__(self, db_path: str) -> None:
        self._reader: geoip2.database.Reader | None = None
        try:
            self._reader = geoip2.database.Reader(db_path)
        except Exception as exc:
            logger.warning("geoip_db_not_loaded", path=db_path, error=repr(exc))

    # resolves an ip address to a coordinate
    def locate(self, ip: str) -> tuple[float, float] | None:
        if self._reader is None:
            return None
        try:
            response = self._reader.city(ip)
            lat = response.location.latitude
            lon = response.location.longitude
            if lat is None or lon is None:
                return None
            return (float(lat), float(lon))
        except Exception as exc:
            logger.warning("geoip_locate_failed", ip=ip, error=repr(exc))
            return None

    # resolves an ip address to a human readable city and country
    def locate_label(self, ip: str) -> str | None:
        if self._reader is None:
            return None
        try:
            response = self._reader.city(ip)
            city = response.city.name
            country = response.country.name
            if city and country:
                return f"{city}, {country}"
            if country:
                return country
            return None
        except Exception as exc:
            logger.warning("geoip_label_failed", ip=ip, error=repr(exc))
            return None

    # computes the distance between two resolved coordinates
    def distance_km(
        self,
        loc1: tuple[float, float],
        loc2: tuple[float, float],
    ) -> float:
        return haversine_km(loc1[0], loc1[1], loc2[0], loc2[1])
