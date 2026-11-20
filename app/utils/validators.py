"""Basic SSRF checks for the public-website-only assessment API.

This pre-flight DNS check is useful but not a complete DNS-rebinding defense.
Production deployment should ALSO enforce network egress restrictions and ideally
pin verified DNS results at connection time.
"""

import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit


class UnsafeURL(ValueError):
    """User-supplied URL is not allowed to be fetched."""


async def require_public_website(url: str) -> None:
    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise UnsafeURL("Invalid URL") from exc

    if parsed.scheme not in {"http", "https"} or not hostname:
        raise UnsafeURL("Only absolute HTTP/HTTPS URLs are allowed")
    if parsed.username is not None or parsed.password is not None:
        raise UnsafeURL("URLs containing user credentials are not allowed")
    if port not in {None, 80, 443}:
        raise UnsafeURL("Only standard website ports (80 and 443) are allowed")
    if hostname.lower().rstrip(".").endswith(
        ("localhost", ".local", ".internal", ".home.arpa", ".test")
    ):
        raise UnsafeURL("Local or internal hostnames are not allowed")

    try:
        literal_address = ipaddress.ip_address(hostname)
    except ValueError:
        literal_address = None
    if literal_address is not None:
        if not literal_address.is_global:
            raise UnsafeURL("Private or non-public IP addresses are not allowed")
        return

    try:
        answers = await asyncio.to_thread(
            socket.getaddrinfo,
            hostname,
            port or (443 if parsed.scheme == "https" else 80),
            0,
            socket.SOCK_STREAM,
        )
    except (socket.gaierror, OSError, UnicodeError) as exc:
        raise UnsafeURL("Website hostname could not be resolved") from exc

    if not answers:
        raise UnsafeURL("Website hostname has no DNS records")
    addresses = {result[4][0] for result in answers}
    for address in addresses:
        if not ipaddress.ip_address(address).is_global:
            raise UnsafeURL("Hostname resolves to a private or non-public IP address")
