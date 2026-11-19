"""Bundle generation must rise on every content change (multi-group, delete)."""

ADMIN = {"X-API-Key": "test-admin-key"}
DEVICE = {"X-API-Key": "test-device-key"}


def _create(client, name: str, countries: list[str]):
    return client.post(
        "/api/v1/admin/country-restrictions",
        headers=ADMIN,
        json={
            "name": name,
            "countries": countries,
            "applyTo": ["call"],
            "enabled": True,
        },
    ).json()


def test_second_group_bumps_bundle_version(client) -> None:
    """Regression: new group must not be ignored when another group already has higher row version."""
    a = _create(client, "A", ["CN"])
    client.put(
        f"/api/v1/admin/country-restrictions/{a['id']}",
        headers=ADMIN,
        json={"countries": ["CN", "RU"]},
    )
    before = client.get("/api/v1/rules/latest", headers=DEVICE).json()
    assert before["version"] >= 1

    _create(client, "B", ["KP"])
    after = client.get("/api/v1/rules/latest", headers=DEVICE).json()
    assert after["version"] > before["version"]
    ids = {r["id"] for r in after["countryRestrictions"]}
    assert a["id"] in ids
    assert len(after["countryRestrictions"]) == 2


def test_delete_bumps_bundle_version_and_drops_group(client) -> None:
    a = _create(client, "A", ["CN"])
    b = _create(client, "B", ["RU"])
    # bump A so it has the max row version
    client.put(
        f"/api/v1/admin/country-restrictions/{a['id']}",
        headers=ADMIN,
        json={"countries": ["CN", "IR"]},
    )
    before = client.get("/api/v1/rules/latest", headers=DEVICE).json()
    assert before["version"] >= 1

    deleted = client.delete(
        f"/api/v1/admin/country-restrictions/{a['id']}",
        headers=ADMIN,
    )
    assert deleted.status_code == 204

    after = client.get("/api/v1/rules/latest", headers=DEVICE).json()
    assert after["version"] > before["version"]
    ids = {r["id"] for r in after["countryRestrictions"]}
    assert a["id"] not in ids
    assert b["id"] in ids


def test_non_max_group_update_bumps_bundle_version(client) -> None:
    a = _create(client, "A", ["CN"])
    b = _create(client, "B", ["RU"])
    client.put(
        f"/api/v1/admin/country-restrictions/{a['id']}",
        headers=ADMIN,
        json={"countries": ["CN", "IR"]},
    )
    before = client.get("/api/v1/rules/latest", headers=DEVICE).json()

    client.put(
        f"/api/v1/admin/country-restrictions/{b['id']}",
        headers=ADMIN,
        json={"enabled": False},
    )
    after = client.get("/api/v1/rules/latest", headers=DEVICE).json()
    assert after["version"] > before["version"]
    b_row = next(r for r in after["countryRestrictions"] if r["id"] == b["id"])
    assert b_row["enabled"] is False
