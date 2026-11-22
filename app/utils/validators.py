"""Validate public URLs and resolve *only* globally routable addresses.

The selected address is used for the actual connection (DNS pinning), and the
original host is used for the HTTP Host header and TLS certificate validation.
"""
from __future__ import annotations
import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit


class UnsafeURL(ValueError):
    """User-submitted URL cannot be fetched safely."""


async def require_public_website(url: str) -> str:
    """Return a verified public IP address to connect to; fail closed."""
    if len(url) > 2048 or any(ord(ch) < 32 for ch in url):
        raise UnsafeURL("URL is too long or contains control characters")
    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise UnsafeURL("Invalid URL") from exc
    if parsed.scheme not in ("http", "https") or not host:
        raise UnsafeURL("Only HTTP/HTTPS website URLs are allowed")
    if parsed.username is not None or parsed.password is not None:
        raise UnsafeURL("Credentials in URLs are not permitted")
    if port not in (None, 80, 443):
        raise UnsafeURL("Only ports 80 and 443 are allowed")
    lowered = host.lower().rstrip(".")
    if lowered == "localhost" or lowered.endswith((".localhost", ".local", ".internal", ".home.arpa", ".test")):
        raise UnsafeURL("Internal hostnames are not allowed")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None:
        if not address.is_global:
            raise UnsafeURL("Private or non-public IP addresses are not allowed")
        return str(address)
    try:
        answers = await asyncio.wait_for(asyncio.to_thread(
            socket.getaddrinfo, host, port or (443 if parsed.scheme == "https" else 80), 0, socket.SOCK_STREAM,
        ), timeout=6)
    except (socket.gaierror, OSError, UnicodeError, asyncio.TimeoutError) as exc:
        raise UnsafeURL("Could not resolve website hostname") from exc
    if not answers:
        raise UnsafeURL("Website hostname has no DNS records")
    addresses = {ipaddress.ip_address(result[4][0]) for result in answers}
    # Reject mixed public/private records rather than selecting an unsafe address.
    if any(not address.is_global for address in addresses):
        raise UnsafeURL("Hostname resolves to a non-public network address")
    # IPv4 first, stable ordering. The selected address MUST be used at connect time.
    return str(sorted(addresses, key=lambda a: (a.version != 4, int(a)))[0])
