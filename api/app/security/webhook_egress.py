"""Outbound webhook egress filtering.

This module exposes :func:`is_allowed_url` used by the notification worker to
validate webhook destinations and guard against SSRF or abuse.
"""

from __future__ import annotations

import os
import socket
from fnmatch import fnmatch
from ipaddress import ip_address, ip_network
from typing import Iterable
from urllib.parse import urlparse


def _host_allowed(host: str, patterns: Iterable[str]) -> bool:
    host = host.lower()
    for pattern in patterns:
        if fnmatch(host, pattern):
            return True
    return False


def _load_allow_hosts() -> list[str]:
    raw = os.getenv("WEBHOOK_ALLOW_HOSTS", "")
    return [h.strip().lower() for h in raw.split(",") if h.strip()]


def _load_deny_cidrs() -> list[ip_network]:
    cidrs: list[ip_network] = []
    raw = os.getenv("WEBHOOK_DENY_CIDRS", "")
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            cidrs.append(ip_network(item, strict=False))
        except ValueError:
            continue
    return cidrs


def _resolve_ips(host: str) -> list[ip_address]:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return []
    ips: list[ip_address] = []
    for info in infos:
        addr = info[4][0]
        try:
            ip = ip_address(addr)
        except ValueError:
            continue
        if ip not in ips:
            ips.append(ip)
    return ips


def is_allowed_url(url: str) -> bool:
    """Return ``True`` if ``url`` is allowed for outbound webhook egress."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = parsed.hostname
    if not host:
        return False
    allow_hosts = _load_allow_hosts()
    if not _host_allowed(host, allow_hosts):
        return False
    deny_cidrs = _load_deny_cidrs()
    try:
        ips = [ip_address(host)]
    except ValueError:
        ips = _resolve_ips(host)
    if not ips:
        return False
    for ip in ips:
        if not ip.is_global:
            return False
        for net in deny_cidrs:
            if ip in net:
                return False
    return True
