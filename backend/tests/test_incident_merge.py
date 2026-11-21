from datetime import datetime, timedelta, timezone
from app.services.incident_merge import should_merge, merge_payloads

def test_should_merge_within_one_hour():
    t0 = datetime(2026, 11, 21, 3, 0, tzinfo=timezone.utc)
    assert should_merge(t0, t0 + timedelta(minutes=50))
    assert not should_merge(t0, t0 + timedelta(hours=2))

def test_merge_unions_triggers_and_calls():
    base = {"triggers": ["call_reject"], "calls": [{"phoneHash": "a"}], "apps": [], "dns": {"available": False, "events": []}}
    inc = {"triggers": ["app_scan"], "calls": [{"phoneHash": "b"}], "apps": [{"packageName": "x"}], "dns": {"available": False, "events": []}}
    out = merge_payloads(base, inc)
    assert set(out["triggers"]) == {"call_reject", "app_scan"}
    assert len(out["calls"]) == 2
    assert out["apps"][0]["packageName"] == "x"
