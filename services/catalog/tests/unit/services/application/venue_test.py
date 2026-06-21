import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from com.qode.qrew.v1.catalog.services.application.venue import (
    VenueError,
    VenueService,
    _validate_coordinates,
    _validate_country,
    _validate_radius,
    _validate_timezone,
)
from conftest import make_venue


def _make_svc(*, venue: object = None) -> tuple[VenueService, MagicMock]:
    repo = MagicMock()
    repo.insert = AsyncMock(side_effect=lambda v: v)
    repo.get_by_id = AsyncMock(return_value=venue)

    audit = AsyncMock()
    audit.record = AsyncMock()

    svc = VenueService(repo=repo, audit=audit)
    return svc, repo


class TestValidateCoordinates:
    def test_raises_when_latitude_too_low(self) -> None:
        with pytest.raises(VenueError, match="Latitude"):
            _validate_coordinates(Decimal("-91"), Decimal("0"))

    def test_raises_when_latitude_too_high(self) -> None:
        with pytest.raises(VenueError, match="Latitude"):
            _validate_coordinates(Decimal("91"), Decimal("0"))

    def test_raises_when_longitude_too_low(self) -> None:
        with pytest.raises(VenueError, match="Longitude"):
            _validate_coordinates(Decimal("0"), Decimal("-181"))

    def test_raises_when_longitude_too_high(self) -> None:
        with pytest.raises(VenueError, match="Longitude"):
            _validate_coordinates(Decimal("0"), Decimal("181"))

    def test_valid_passes(self) -> None:
        _validate_coordinates(Decimal("52.370"), Decimal("4.895"))
        _validate_coordinates(Decimal("90"), Decimal("180"))
        _validate_coordinates(Decimal("-90"), Decimal("-180"))


class TestValidateRadius:
    def test_raises_when_below_minimum(self) -> None:
        with pytest.raises(VenueError, match="50"):
            _validate_radius(49)

    def test_raises_when_above_maximum(self) -> None:
        with pytest.raises(VenueError, match="5000"):
            _validate_radius(5001)

    def test_boundary_values_pass(self) -> None:
        _validate_radius(50)
        _validate_radius(5000)


class TestValidateTimezone:
    def test_raises_when_unknown(self) -> None:
        with pytest.raises(VenueError, match="timezone"):
            _validate_timezone("Moon/Crater")

    def test_valid_timezone_passes(self) -> None:
        _validate_timezone("Europe/Amsterdam")
        _validate_timezone("UTC")


class TestValidateCountry:
    def test_raises_when_not_two_letters(self) -> None:
        with pytest.raises(VenueError, match="ISO"):
            _validate_country("NLD")

    def test_raises_when_contains_digit(self) -> None:
        with pytest.raises(VenueError, match="ISO"):
            _validate_country("N1")

    def test_valid_passes(self) -> None:
        _validate_country("NL")
        _validate_country("GB")


class TestVenueServiceCreate:
    async def test_raises_when_country_invalid(self, actor_id: uuid.UUID) -> None:
        svc, _ = _make_svc()
        with pytest.raises(VenueError, match="ISO"):
            await svc.create_venue(
                actor_id=actor_id, name="V", address_line="A", city="C",
                country="XYZ", latitude=Decimal("52"), longitude=Decimal("4"),
                geofence_radius_m=200, timezone="UTC", description=None,
            )

    async def test_raises_when_coordinates_invalid(self, actor_id: uuid.UUID) -> None:
        svc, _ = _make_svc()
        with pytest.raises(VenueError, match="Latitude"):
            await svc.create_venue(
                actor_id=actor_id, name="V", address_line="A", city="C",
                country="NL", latitude=Decimal("999"), longitude=Decimal("4"),
                geofence_radius_m=200, timezone="UTC", description=None,
            )

    async def test_raises_when_radius_invalid(self, actor_id: uuid.UUID) -> None:
        svc, _ = _make_svc()
        with pytest.raises(VenueError, match="50"):
            await svc.create_venue(
                actor_id=actor_id, name="V", address_line="A", city="C",
                country="NL", latitude=Decimal("52"), longitude=Decimal("4"),
                geofence_radius_m=10, timezone="UTC", description=None,
            )

    async def test_raises_when_timezone_invalid(self, actor_id: uuid.UUID) -> None:
        svc, _ = _make_svc()
        with pytest.raises(VenueError, match="timezone"):
            await svc.create_venue(
                actor_id=actor_id, name="V", address_line="A", city="C",
                country="NL", latitude=Decimal("52"), longitude=Decimal("4"),
                geofence_radius_m=200, timezone="Not/Real", description=None,
            )

    async def test_creates_venue(self, actor_id: uuid.UUID) -> None:
        svc, repo = _make_svc()
        result = await svc.create_venue(
            actor_id=actor_id, name="Stadium", address_line="Dam 1", city="Amsterdam",
            country="nl", latitude=Decimal("52.370"), longitude=Decimal("4.895"),
            geofence_radius_m=200, timezone="Europe/Amsterdam", description=None,
        )
        assert result.name == "Stadium"
        assert result.country == "NL"  # uppercased
        repo.insert.assert_awaited_once()

    async def test_audit_error_is_swallowed(self, actor_id: uuid.UUID) -> None:
        svc, _ = _make_svc()
        svc._audit.record = AsyncMock(side_effect=RuntimeError("audit down"))
        result = await svc.create_venue(
            actor_id=actor_id, name="Stadium", address_line="Dam 1", city="Amsterdam",
            country="NL", latitude=Decimal("52.370"), longitude=Decimal("4.895"),
            geofence_radius_m=200, timezone="Europe/Amsterdam", description=None,
        )
        assert result is not None
