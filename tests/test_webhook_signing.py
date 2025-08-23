import importlib.util
import json
import hmac
import hashlib

# Load notify_worker module
spec = importlib.util.spec_from_file_location("notify_worker", "scripts/notify_worker.py")
notify_worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(notify_worker)


def _verify(secret: str, body: str, ts: str, sig: str) -> bool:
    expected = "sha256=" + hmac.new(
        secret.encode(), f"{ts}.{body}".encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, sig)


def test_signature_and_verification():
    secret = "topsecret"
    body = json.dumps({"msg": "hi"}, separators=(",", ":"))
    ts, sig = notify_worker.sign_webhook(body, secret, "100")
    assert ts == "100"
    assert _verify(secret, body, ts, sig)
    # Modified body should fail verification
    assert not _verify(secret, body + " ", ts, sig)
