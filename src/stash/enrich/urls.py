import ipaddress
import re
from types import MappingProxyType

from stash.domain import http_url_host

WEB = "web"
_PLATFORM_DOMAINS = MappingProxyType(
    {
        "instagram.com": "instagram",
        "youtube.com": "youtube",
        "youtu.be": "youtube",
        "tiktok.com": "tiktok",
        "x.com": "x",
        "twitter.com": "x",
        "reddit.com": "reddit",
        "redd.it": "reddit",
    }
)
PLATFORMS = (*dict.fromkeys(_PLATFORM_DOMAINS.values()), WEB)

_LINK = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
_TRAILING_PUNCTUATION = ".,;:!?"
_OPENER_OF = MappingProxyType({")": "(", "]": "[", "}": "{"})
_PRIVATE_SUFFIXES = (
    ".localhost",
    ".local",
    ".internal",
    ".lan",
    ".home.arpa",
    ".intranet",
    ".corp",
    ".private",
    ".home",
    ".localdomain",
    ".svc",
)
_NAT64 = ipaddress.IPv6Network("64:ff9b::/96")
_SIX_TO_FOUR = ipaddress.IPv6Network("2002::/16")
_IPV4_COMPATIBLE = ipaddress.IPv6Network("::/96")
_SIIT = ipaddress.IPv6Network("::ffff:0:0:0/96")
_LOW_32_BIT_NETWORKS = (_NAT64, _IPV4_COMPATIBLE, _SIIT)
_LOW_32_BITS = 0xFFFFFFFF
_SIX_TO_FOUR_SHIFT = 80
_LEGACY_NUMERIC_LABEL = re.compile(r"\d+|0x[0-9a-f]+", re.IGNORECASE)


def extract_urls(text: str) -> tuple[str, ...]:
    candidates = (_trimmed(match) for match in _LINK.findall(text))
    return tuple(dict.fromkeys(url for url in candidates if http_url_host(url) is not None))


def platform_of(url: str) -> str:
    host = http_url_host(url)
    if host is None:
        return WEB
    host = host.rstrip(".")
    for domain, platform in _PLATFORM_DOMAINS.items():
        if host == domain or host.endswith(f".{domain}"):
            return platform
    return WEB


def is_public_http_url(url: str) -> bool:
    host = http_url_host(url)
    if host is None:
        return False
    host = host.rstrip(".")
    if not host or host == "localhost" or host.endswith(_PRIVATE_SUFFIXES):
        return False
    address = _literal_address(host)
    if address is not None:
        unicast = _embedded_ipv4(address)
        return unicast.is_global and not unicast.is_multicast
    return "." in host and _LEGACY_NUMERIC_LABEL.fullmatch(host.rsplit(".", 1)[-1]) is None


def _literal_address(host: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        return None


def _embedded_ipv4(
    address: ipaddress.IPv4Address | ipaddress.IPv6Address,
) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    if isinstance(address, ipaddress.IPv6Address):
        if any(address in network for network in _LOW_32_BIT_NETWORKS):
            return ipaddress.IPv4Address(int(address) & _LOW_32_BITS)
        if address in _SIX_TO_FOUR:
            return ipaddress.IPv4Address((int(address) >> _SIX_TO_FOUR_SHIFT) & _LOW_32_BITS)
    return address


def _trimmed(candidate: str) -> str:
    while True:
        stripped = candidate.rstrip(_TRAILING_PUNCTUATION)
        if stripped and _ends_with_unmatched_closer(stripped):
            stripped = stripped[:-1]
        if stripped == candidate:
            return candidate
        candidate = stripped


def _ends_with_unmatched_closer(url: str) -> bool:
    closer = url[-1]
    opener = _OPENER_OF.get(closer)
    return opener is not None and url.count(closer) > url.count(opener)
