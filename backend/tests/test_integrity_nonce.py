from app.services.integrity import _nonce_matches, _package_matches


def test_nonce_matches_request_details():
    payload = {"requestDetails": {"nonce": "abc123", "requestPackageName": "com.eldershield"}}
    assert _nonce_matches(payload, "abc123") is True
    assert _nonce_matches(payload, "nope") is False


def test_package_matches_when_present():
    payload = {"requestDetails": {"requestPackageName": "com.eldershield"}}
    assert _package_matches(payload, "com.eldershield") is True
    assert _package_matches(payload, "com.other") is False
    assert _package_matches({}, "com.eldershield") is True
