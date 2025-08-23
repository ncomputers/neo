import importlib.util
import json

# Load webhook_signing module
spec = importlib.util.spec_from_file_location(
    "webhook_signing", "api/app/utils/webhook_signing.py"
)
webhook_signing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(webhook_signing)


def test_signature_and_verification():
    secret = "topsecret"
    body = json.dumps({"msg": "hi"}, separators=(",", ":")).encode()
    ts = 100
    sig = webhook_signing.sign(secret, ts, body)
    assert (
        sig
        == "sha256=970a34c850da51f6010b465dfd20d0dc4909de5ddb5e39daf4e8b456d1af1ab4"
    )
    assert webhook_signing.verify(secret, ts, body, sig, max_skew=10**10)
    # Modified body should fail verification
    assert not webhook_signing.verify(secret, ts, body + b" ", sig, max_skew=10**10)
