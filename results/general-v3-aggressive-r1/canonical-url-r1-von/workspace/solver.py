import re
from urllib.parse import parse_qsl, quote_plus, urlsplit, urlunsplit


def canonical_url(url):
    if not isinstance(url, str) or any(ord(char) < 32 or ord(char) == 127 for char in url):
        raise ValueError("invalid URL")

    try:
        parsed = urlsplit(url)
        scheme = parsed.scheme.lower()
        if scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("unsupported or incomplete URL")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("credentials are not allowed")
        if "#" in url:
            raise ValueError("fragments are not allowed")

        hostname = parsed.hostname
        if not hostname:
            raise ValueError("missing hostname")
        hostname = hostname.lower()
        if hostname.endswith("."):
            hostname = hostname[:-1]
        if not hostname:
            raise ValueError("missing hostname")

        port = parsed.port
        if port is not None and not 0 <= port <= 65535:
            raise ValueError("invalid port")
    except (ValueError, UnicodeError) as exc:
        raise ValueError("invalid URL") from exc

    # Bracket IPv6 literals when rebuilding the authority.
    authority_host = f"[{hostname}]" if ":" in hostname else hostname
    if port is not None and not (scheme == "http" and port == 80 or scheme == "https" and port == 443):
        authority = f"{authority_host}:{port}"
    else:
        authority = authority_host

    path = parsed.path or "/"
    trailing_slash = path.endswith("/")
    segments = []
    for segment in re.split(r"/+", path):
        if segment in ("", "."):
            continue
        if segment == "..":
            if segments:
                segments.pop()
        else:
            segments.append(segment)
    path = "/" + "/".join(segments)
    if trailing_slash and path != "/":
        path += "/"

    pairs = parse_qsl(parsed.query, keep_blank_values=True, encoding="utf-8", errors="replace")
    pairs.sort(key=lambda pair: (pair[0], pair[1]))
    query = "&".join(
        f"{quote_plus(key, safe='~')}={quote_plus(value, safe='~')}"
        for key, value in pairs
    )

    return urlunsplit((scheme, authority, path, query, ""))
