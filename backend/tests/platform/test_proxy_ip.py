"""Offline test suite for trusted proxy client IP resolution and anti-spoofing (REQ-SEC-02)."""

import pytest
from starlette.requests import Request
from httpx import AsyncClient

from app.core.config import settings
from app.core.security import get_trusted_client_ip, is_trusted_proxy_ip, login_throttle


def _make_dummy_request(client_host: str, headers: dict = None) -> Request:
    """Constructs a minimal Starlette Request instance for unit testing."""
    raw_headers = []
    if headers:
        for k, v in headers.items():
            raw_headers.append((k.lower().encode("latin-1"), v.encode("latin-1")))
    scope = {
        "type": "http",
        "client": (client_host, 54321),
        "headers": raw_headers,
    }
    return Request(scope)


def test_direct_connection_without_headers() -> None:
    """Direct client without forwarded headers returns client host."""
    req = _make_dummy_request("203.0.113.10")
    assert get_trusted_client_ip(req) == "203.0.113.10"


def test_untrusted_client_cannot_spoof_forwarded_headers() -> None:
    """Direct untrusted client sending spoofed X-Forwarded-For or X-Real-IP is ignored."""
    req = _make_dummy_request(
        "203.0.113.50",
        headers={
            "x-forwarded-for": "1.1.1.1, 8.8.8.8",
            "x-real-ip": "1.1.1.1",
        },
    )
    # Must return the direct untrusted peer IP, ignoring the spoofed headers
    assert get_trusted_client_ip(req) == "203.0.113.50"


def test_trusted_proxy_resolves_x_real_ip() -> None:
    """Request from trusted proxy (127.0.0.1) resolves X-Real-IP set by Nginx."""
    req = _make_dummy_request(
        "127.0.0.1",
        headers={"x-real-ip": "198.51.100.42"},
    )
    assert get_trusted_client_ip(req) == "198.51.100.42"


def test_trusted_docker_network_proxy_walks_forwarded_for() -> None:
    """Request from configured Docker bridge subnet (172.28.0.5) parses X-Forwarded-For chain."""
    req = _make_dummy_request(
        "172.28.0.5",
        headers={"x-forwarded-for": "203.0.113.99, 172.28.0.2"},
    )
    # When TRUSTED_PROXY_CIDRS includes 172.28.0.0/16, the docker proxy is trusted
    assert get_trusted_client_ip(req, allowed_cidrs="172.28.0.0/16,127.0.0.1/32") == "203.0.113.99"


def test_untrusted_private_ip_cannot_spoof_client_ip() -> None:
    """An untrusted private IP (e.g. 10.0.0.1, 192.168.1.50) cannot spoof forwarded headers."""
    # Scenario 1: Default configuration (only loopback trusted) rejects 10.0.0.1 and 192.168.1.50
    for untrusted_ip in ("10.0.0.1", "192.168.1.50", "172.16.5.10"):
        req = _make_dummy_request(
            untrusted_ip,
            headers={"x-forwarded-for": "1.2.3.4", "x-real-ip": "5.6.7.8"},
        )
        assert is_trusted_proxy_ip(untrusted_ip) is False
        assert get_trusted_client_ip(req) == untrusted_ip

    # Scenario 2: With deterministic docker subnet 172.28.0.0/16, other private ranges are STILL untrusted
    docker_cidrs = "127.0.0.1/32,::1/128,172.28.0.0/16"
    assert is_trusted_proxy_ip("172.28.0.2", allowed_cidrs=docker_cidrs) is True
    assert is_trusted_proxy_ip("10.0.0.1", allowed_cidrs=docker_cidrs) is False
    assert is_trusted_proxy_ip("192.168.1.50", allowed_cidrs=docker_cidrs) is False

    req_spoof = _make_dummy_request(
        "10.0.0.1",
        headers={"x-forwarded-for": "8.8.8.8", "x-real-ip": "8.8.8.8"},
    )
    assert get_trusted_client_ip(req_spoof, allowed_cidrs=docker_cidrs) == "10.0.0.1"


def test_untrusted_private_ip_cannot_bypass_throttle_with_rotating_forwarded_headers() -> None:
    """An attacker from untrusted private IP 10.0.0.1 cannot bypass login throttle by rotating headers."""
    login_throttle.clear_all()
    untrusted_attacker_ip = "10.0.0.1"

    # Attacker tries multiple different fake X-Forwarded-For IPs
    for i in range(settings.LOGIN_MAX_FAILED_ATTEMPTS):
        req = _make_dummy_request(
            untrusted_attacker_ip,
            headers={"x-forwarded-for": f"198.51.100.{i+1}"},
        )
        client_ip = get_trusted_client_ip(req)
        # Because direct host 10.0.0.1 is not in trusted CIDRs, resolved IP is always 10.0.0.1
        assert client_ip == untrusted_attacker_ip
        login_throttle.record_failure(f"ip:{client_ip}")

    # 11th attempt: even with yet another fake header, attacker is throttled based on real IP
    req_next = _make_dummy_request(
        untrusted_attacker_ip,
        headers={"x-forwarded-for": "1.1.1.1"},
    )
    client_ip_next = get_trusted_client_ip(req_next)
    is_blocked = login_throttle.is_blocked(f"ip:{client_ip_next}")
    assert is_blocked is True
    login_throttle.clear_all()


def test_ipv6_loopback_trusted_proxy_and_safe_parsing() -> None:
    """IPv6 loopback (::1) is trusted without raising TypeError in ipaddress."""
    req = _make_dummy_request(
        "::1",
        headers={"x-real-ip": "203.0.113.77"},
    )
    assert is_trusted_proxy_ip("::1") is True
    assert get_trusted_client_ip(req) == "203.0.113.77"


def test_malformed_headers_fall_back_safely() -> None:
    """Garbage / unparseable forwarded headers safely fall back to direct IP."""
    req = _make_dummy_request(
        "127.0.0.1",
        headers={
            "x-real-ip": "not-an-ip-address",
            "x-forwarded-for": "also-not-an-ip",
        },
    )
    assert get_trusted_client_ip(req) == "127.0.0.1"


@pytest.mark.asyncio
async def test_auth_endpoint_uses_trusted_proxy_ip_for_throttle(unauth_client: AsyncClient) -> None:
    """Verify auth endpoint throttles by real client IP when forwarded through trusted proxy."""
    login_throttle.clear_all()
    spoofed_ip = "198.51.100.88"

    # Send failed requests with X-Real-IP header through test client
    for _ in range(settings.LOGIN_MAX_FAILED_ATTEMPTS):
        res = await unauth_client.post(
            "/api/v1/auth/token",
            json={"username": "victim@domain.vn", "password": "BadPassword"},
            headers={"x-real-ip": spoofed_ip},
        )
        assert res.status_code == 401

    # Next attempt from same forwarded IP is throttled (429)
    res_blocked = await unauth_client.post(
        "/api/v1/auth/token",
        json={"username": "other_user@domain.vn", "password": "BadPassword"},
        headers={"x-real-ip": spoofed_ip},
    )
    assert res_blocked.status_code == 429
    login_throttle.clear_all()

