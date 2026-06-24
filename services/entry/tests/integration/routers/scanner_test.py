import uuid
from datetime import date

import pytest

from tests.integration.conftest import (
    make_access_token,
    make_scanner_token,
    seed_scanner,
    seed_user,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


# ---------------------------------------------------------------------------
# POST /v1/admin/scanners — create
# ---------------------------------------------------------------------------


async def test_create_scanner(client, db):
    admin = await seed_user(db, is_admin=True)
    token = make_access_token(admin.id)
    venue_id = uuid.uuid4()
    event_id = uuid.uuid4()

    response = await client.post(
        "/v1/admin/scanners",
        json={
            "name": "Main Gate",
            "venue_id": str(venue_id),
            "event_id": str(event_id),
            "date": date.today().isoformat(),
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert "scanner_id" in data
    assert "token" in data
    assert data["expires_in_hours"] > 0


async def test_create_scanner_not_admin(client, db):
    user = await seed_user(db, is_admin=False)
    token = make_access_token(user.id)
    venue_id = uuid.uuid4()
    event_id = uuid.uuid4()

    response = await client.post(
        "/v1/admin/scanners",
        json={
            "name": "Gate",
            "venue_id": str(venue_id),
            "event_id": str(event_id),
            "date": date.today().isoformat(),
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


async def test_create_scanner_no_auth(client):
    response = await client.post(
        "/v1/admin/scanners",
        json={
            "name": "Gate",
            "venue_id": str(uuid.uuid4()),
            "event_id": str(uuid.uuid4()),
            "date": date.today().isoformat(),
        },
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /v1/admin/scanners — list
# ---------------------------------------------------------------------------


async def test_list_scanners(client, db):
    admin = await seed_user(db, is_admin=True)
    venue_id = uuid.uuid4()
    await seed_scanner(db, created_by=admin.id, venue_id=venue_id)

    token = make_access_token(admin.id)
    response = await client.get(
        "/v1/admin/scanners",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "scanners" in data
    assert isinstance(data["scanners"], list)


# ---------------------------------------------------------------------------
# GET /v1/admin/scanners/{scanner_id}
# ---------------------------------------------------------------------------


async def test_get_scanner_by_id(client, db):
    admin = await seed_user(db, is_admin=True)
    venue_id = uuid.uuid4()
    scanner = await seed_scanner(db, created_by=admin.id, venue_id=venue_id)

    token = make_access_token(admin.id)
    response = await client.get(
        f"/v1/admin/scanners/{scanner.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(scanner.id)
    assert data["is_active"] is True


async def test_get_scanner_not_found(client, db):
    admin = await seed_user(db, is_admin=True)
    token = make_access_token(admin.id)

    response = await client.get(
        f"/v1/admin/scanners/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /v1/admin/scanners/{scanner_id}/rotate
# ---------------------------------------------------------------------------


async def test_rotate_scanner(client, db):
    admin = await seed_user(db, is_admin=True)
    venue_id = uuid.uuid4()
    scanner = await seed_scanner(db, created_by=admin.id, venue_id=venue_id)
    event_id = uuid.uuid4()

    token = make_access_token(admin.id)
    response = await client.post(
        f"/v1/admin/scanners/{scanner.id}/rotate",
        json={
            "venue_id": str(venue_id),
            "event_id": str(event_id),
            "date": date.today().isoformat(),
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["scanner_id"] == str(scanner.id)
    assert "token" in data


# ---------------------------------------------------------------------------
# DELETE /v1/admin/scanners/{scanner_id}
# ---------------------------------------------------------------------------


async def test_deactivate_scanner(client, db):
    admin = await seed_user(db, is_admin=True)
    venue_id = uuid.uuid4()
    scanner = await seed_scanner(db, created_by=admin.id, venue_id=venue_id)

    token = make_access_token(admin.id)
    response = await client.delete(
        f"/v1/admin/scanners/{scanner.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Scanner deactivated."


# ---------------------------------------------------------------------------
# POST /v1/scanners/refresh
# ---------------------------------------------------------------------------


async def test_refresh_scanner(client, db):
    admin = await seed_user(db, is_admin=True)
    venue_id = uuid.uuid4()
    event_id = uuid.uuid4()
    scanner = await seed_scanner(db, created_by=admin.id, venue_id=venue_id)

    scanner_token = make_scanner_token(scanner.id, venue_id, event_id)
    response = await client.post(
        "/v1/scanners/refresh",
        headers={"Authorization": f"Bearer {scanner_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["scanner_id"] == str(scanner.id)
    assert "token" in data


async def test_refresh_scanner_invalid_token(client):
    response = await client.post(
        "/v1/scanners/refresh",
        headers={"Authorization": "Bearer not.a.valid.token"},
    )
    assert response.status_code == 401
