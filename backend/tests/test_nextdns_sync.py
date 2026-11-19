import json

import httpx
import pytest

from app.services.nextdns_sync import NextDnsNotConfigured, sync_policy_to_nextdns


def test_sync_requires_env():
    with pytest.raises(NextDnsNotConfigured):
        sync_policy_to_nextdns([], api_key=None, profile_id="abc")


def test_sync_tlds_and_denylist_merge():
    rows = [{"countries": ["CN"], "apply_to": ["dns"], "enabled": True}]
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        calls.append((request.method, path))
        if request.method == "GET" and path.endswith("/security"):
            return httpx.Response(
                200,
                json={"data": {"tlds": [{"id": "accountants"}, {"id": "ru"}]}},
            )
        if request.method == "PATCH" and path.endswith("/security"):
            payload = json.loads(request.content.decode())
            ids = {t["id"] for t in payload["tlds"]}
            assert "accountants" in ids
            assert "cn" in ids
            assert "ru" not in ids
            return httpx.Response(204)
        if request.method == "GET" and path.endswith("/denylist"):
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"id": "baidu.com", "active": True},
                        {"id": "user-custom.com", "active": True},
                    ]
                },
            )
        if request.method == "POST" and path.endswith("/denylist"):
            return httpx.Response(204)
        if request.method == "DELETE":
            return httpx.Response(204)
        return httpx.Response(500, text=f"unexpected {request.method} {path}")

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport, base_url="https://api.nextdns.io") as client:
        result = sync_policy_to_nextdns(
            rows,
            api_key="k",
            profile_id="abc123",
            client=client,
        )
    assert result["ok"] is True
    assert "cn" in result["plan"]["tlds"]
    assert "baidu.com" in result["plan"]["domains"]
    assert ("PATCH", "/profiles/abc123/security") in calls
