from app.services.device_tokens import generate_device_token, hash_device_token, tokens_match


def test_generate_token_is_urlsafe_and_long():
    t = generate_device_token()
    assert len(t) >= 32
    assert t != generate_device_token()


def test_hash_roundtrip():
    t = generate_device_token()
    h = hash_device_token(t)
    assert tokens_match(t, h)
    assert not tokens_match("wrong", h)
