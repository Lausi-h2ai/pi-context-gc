from urllib.parse import parse_qsl, urlencode, urlsplit


def canonical_url(url):
    """Return a validated, normalized HTTP(S) URL suitable for a cache key."""
    if not isinstance(url, str) or any(ord(char) < 32 or ord(char) == 127 for char in url):
        raise ValueError("invalid URL")
    if "#" in url:
        raise ValueError("fragments are not allowed")

    try:
        parsed = urlsplit(url)
        scheme = parsed.scheme.lower()
        if scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("absolute HTTP or HTTPS URL required")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("credentials are not allowed")
        hostname = parsed.hostname
        if not hostname:
            raise ValueError("hostname is required")
        port = parsed.port  # Accessing this also validates range and syntax.
        # Detect an empty explicit port, including after an IPv6 literal.
        authority_text = parsed.netloc.rsplit("@", 1)[-1]
        if authority_text.endswith(":"):
            raise ValueError("invalid port")
    except (ValueError, UnicodeError) as exc:
        raise ValueError("invalid URL") from exc

    hostname = hostname.lower()
    if hostname.endswith("."):
        hostname = hostname[:-1]
    if not hostname:
        raise ValueError("hostname is required")

    host = f"[{hostname}]" if ":" in hostname else hostname
    default_port = 80 if scheme == "http" else 443
    authority = host if port is None or port == default_port else f"{host}:{port}"

    # Split on separators first so repeated slashes collapse along with dot segments.
    original_path = parsed.path or "/"
    segments = []
    for segment in original_path.split("/"):
        if segment in ("", "."):
            continue
        if segment == "..":
            if segments:
                segments.pop()
        else:
            segments.append(segment)
    path = "/" + "/".join(segments)
    if path != "/" and (original_path.endswith("/") or original_path.endswith("/.") or original_path.endswith("/..")):
        path += "/"

    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    pairs.sort(key=lambda pair: (pair[0], pair[1]))
    query = urlencode(pairs)
    return f"{scheme}://{authority}{path}" + (f"?{query}" if query else "")
