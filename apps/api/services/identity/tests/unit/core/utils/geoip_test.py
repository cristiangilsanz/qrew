# covers locating an address and measuring the distance between two logins
from types import SimpleNamespace

from com.qode.qrew.v1.identity.core.utils.geoip import GeoIpService, haversine_km

MADRID = (40.4168, -3.7038)
BARCELONA = (41.3874, 2.1686)


# builds a geoip service whose reader answers with the given city record
def _service_with(record: object) -> GeoIpService:
    service = GeoIpService("/nonexistent.mmdb")
    service._reader = SimpleNamespace(city=lambda ip: record)  # type: ignore[assignment]
    return service


# builds a service whose reader raises on every lookup
def _service_that_fails() -> GeoIpService:
    # raises so the caller has to survive a broken database
    def _raise(ip: str) -> object:
        raise RuntimeError("db corrupt")

    service = GeoIpService("/nonexistent.mmdb")
    service._reader = SimpleNamespace(city=_raise)  # type: ignore[assignment]
    return service


# builds a city record with the given coordinates and names
def _record(
    lat: float | None = None,
    lon: float | None = None,
    city: str | None = None,
    country: str | None = None,
) -> object:
    return SimpleNamespace(
        location=SimpleNamespace(latitude=lat, longitude=lon),
        city=SimpleNamespace(name=city),
        country=SimpleNamespace(name=country),
    )


class TestHaversine:
    # verifies that the distance from a point to itself is zero
    def test_the_distance_to_itself_is_zero(self) -> None:
        assert haversine_km(*MADRID, *MADRID) == 0

    # verifies that a known distance is measured within a few kilometres
    def test_a_known_distance_is_measured(self) -> None:
        assert 490 < haversine_km(*MADRID, *BARCELONA) < 520

    # verifies that the distance is the same in either direction
    def test_the_distance_is_symmetric(self) -> None:
        there = haversine_km(*MADRID, *BARCELONA)
        back = haversine_km(*BARCELONA, *MADRID)
        assert abs(there - back) < 1e-9


class TestGeoIpService:
    # verifies that a missing database leaves the service inert rather than failing
    def test_a_missing_database_leaves_the_service_inert(self) -> None:
        service = GeoIpService("/nonexistent.mmdb")
        assert service.locate("203.0.113.1") is None
        assert service.locate_label("203.0.113.1") is None

    # verifies that a resolved address returns its coordinate
    def test_a_resolved_address_returns_its_coordinate(self) -> None:
        service = _service_with(_record(lat=40.4168, lon=-3.7038))
        assert service.locate("203.0.113.1") == MADRID

    # verifies that a record without coordinates resolves to nothing
    def test_a_record_without_coordinates_resolves_to_nothing(self) -> None:
        assert _service_with(_record()).locate("203.0.113.1") is None

    # verifies that a failed lookup resolves to nothing
    def test_a_failed_lookup_resolves_to_nothing(self) -> None:
        assert _service_that_fails().locate("203.0.113.1") is None

    # verifies that a full record reads as city and country
    def test_a_full_record_reads_as_city_and_country(self) -> None:
        service = _service_with(_record(city="Madrid", country="Spain"))
        assert service.locate_label("203.0.113.1") == "Madrid, Spain"

    # verifies that a record with only a country reads as the country
    def test_a_country_only_record_reads_as_the_country(self) -> None:
        assert _service_with(_record(country="Spain")).locate_label("203.0.113.1") == "Spain"

    # verifies that a record naming nowhere reads as nothing
    def test_a_record_naming_nowhere_reads_as_nothing(self) -> None:
        assert _service_with(_record()).locate_label("203.0.113.1") is None

    # verifies that a failed label lookup reads as nothing
    def test_a_failed_label_lookup_reads_as_nothing(self) -> None:
        assert _service_that_fails().locate_label("203.0.113.1") is None

    # verifies that the service measures the distance between two coordinates
    def test_it_measures_the_distance_between_two_coordinates(self) -> None:
        service = GeoIpService("/nonexistent.mmdb")
        assert 490 < service.distance_km(MADRID, BARCELONA) < 520
