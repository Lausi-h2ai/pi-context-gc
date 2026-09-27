from urllib.parse import parse_qsl, quote_plus, urlsplit


def canonical_url(url):
    if not isinstance(url, str) or any(ord(ch) < 32 or ord(ch) == 127 for ch in url):
        raise ValueError("invalid URL")

    try:
        parsed = urlsplit(url)
        scheme = parsed.scheme.lower()
        if scheme not in ("http", "https"):
            raise ValueError("unsupported scheme")
        if not parsed.netloc or parsed.username is not None or parsed.password is not None:
            raise ValueError("invalid authority")
        if "#" in url:
            raise ValueError("fragments are not supported")
        if parsed.netloc.endswith(":"):
            raise ValueError("invalid port")
        host = parsed.hostname
        if not host:
            raise ValueError("missing host")
        port = parsed.port  # Access validates malformed and out-of-range ports.
    except (TypeError, UnicodeError) as exc:
        raise ValueError("invalid URL") from exc

    host = host.lower()
    if host.endswith("."):
        host = host[:-1]
    if not host:
        raise ValueError("missing host")

    # Preserve IPv6 literal brackets in the authority.
    if ":" in host:
        host = f"[{host}]"
    default_port = 80 if scheme == "http" else 443
    authority = host if port is None or port == default_port else f"{host}:{port}"

    raw_path = parsed.path
    trailing = raw_path.endswith("/")
    segments = []
    for segment in raw_path.split("/"):
        if segment in ("", "."):
            continue
        if segment == "..":
            if segments:
                segments.pop()
        else:
            segments.append(segment)
    path = "/" + "/".join(segments)
    if trailing and path != "/":
        path += "/"

    pairs = parse_qsl(parsed.query, keep_blank_values=True, encoding="utf-8", errors="strict")
    pairs.sort(key=lambda pair: (pair[0], pair[1]))
    query = "&".join(f"{quote_plus(key)}={quote_plus(value)}" for key, value in pairs)
    return f"{scheme}://{authority}{path}" + (f"?{query}" if pairs else "")
