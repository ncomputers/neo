import socket

from api.app.security.webhook_egress import is_allowed_url


def _patch_dns(monkeypatch, host: str, addr: str) -> None:
    def fake_getaddrinfo(target, *args, **kwargs):  # pragma: no cover - simple stub
        assert target == host
        return [(socket.AF_INET, 0, 0, "", (addr, 0))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)


def test_public_host_allowed(monkeypatch):
    monkeypatch.setenv("WEBHOOK_ALLOW_HOSTS", "hooks.slack.com")
    _patch_dns(monkeypatch, "hooks.slack.com", "1.2.3.4")
    assert is_allowed_url("https://hooks.slack.com/services/foo")


def test_private_ip_blocked(monkeypatch):
    monkeypatch.setenv("WEBHOOK_ALLOW_HOSTS", "intra.example.com")
    _patch_dns(monkeypatch, "intra.example.com", "10.0.0.1")
    assert not is_allowed_url("https://intra.example.com/hook")


def test_host_not_in_allowlist(monkeypatch):
    monkeypatch.setenv("WEBHOOK_ALLOW_HOSTS", "hooks.slack.com")
    _patch_dns(monkeypatch, "evil.com", "1.2.3.4")
    assert not is_allowed_url("https://evil.com/x")


def test_custom_deny_cidr(monkeypatch):
    monkeypatch.setenv("WEBHOOK_ALLOW_HOSTS", "hooks.slack.com")
    monkeypatch.setenv("WEBHOOK_DENY_CIDRS", "1.2.3.0/24")
    _patch_dns(monkeypatch, "hooks.slack.com", "1.2.3.4")
    assert not is_allowed_url("https://hooks.slack.com/x")
