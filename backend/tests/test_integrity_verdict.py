from app.services.integrity import _meets_device_integrity


def test_meets_device_integrity_accepts_verdict():
    payload = {
        "deviceIntegrity": {
            "deviceRecognitionVerdict": ["MEETS_DEVICE_INTEGRITY", "MEETS_BASIC_INTEGRITY"]
        }
    }
    assert _meets_device_integrity(payload) is True


def test_meets_device_integrity_rejects_empty():
    assert _meets_device_integrity({}) is False
    assert _meets_device_integrity({"deviceIntegrity": {}}) is False
