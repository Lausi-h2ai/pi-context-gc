from urllib.parse import parse_qsl, quote, urlencode, urlsplit


def canonical_url(url):
    """Return the canonical form of an absolute HTTP(S) URL."""
    if not isinstance(url, str) or any(ord(char) < 32 or ord(char) == 127 for char in url):
        raise ValueError("URL must be text without control characters")

    try:
        parsed = urlsplit(url)
        scheme = parsed.scheme.lower()
        if scheme not in ("http", "https"):
            raise ValueError("unsupported URL scheme")
        if "#" in url:
            raise ValueError("URL fragments are not allowed")
        if "@" in parsed.netloc:
            raise ValueError("URL credentials are not allowed")
        host = parsed.hostname
        if not host:
            raise ValueError("URL host is required")
        port = parsed.port
    except (ValueError, UnicodeError) as exc:
        raise ValueError("invalid URL") from exc

    host = host.lower()
    if host.endswith(".") and ":" not in host:
        host = host[:-1]
    if not host or any(char.isspace() for char in host):
        raise ValueError("URL host is invalid")

    # Bracket IPv6 literals when rebuilding the authority.
    authority_host = f"[{host}]" if ":" in host else host
    if port is not None and port != (80 if scheme == "http" else 443):
        authority_host += f":{port}"

    path = parsed.path or "/"
    trailing_slash = path.endswith("/") or path.endswith("/.") or path.endswith("/..")
    segments = []
    for segment in path.split("/"):
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
    # Keep Unicode and existing URL escapes while safely escaping raw spaces.
    path = quote(path, safe="/%:@!$&'()*+,;=-._~%")

    try:
        pairs = parse_qsl(parsed.query, keep_blank_values=True, encoding="utf-8", errors="strict")
    except (ValueError, UnicodeError) as exc:
        raise ValueError("invalid URL query") from exc
    pairs.sort(key=lambda pair: (pair[0], pair[1]))
    query = urlencode(pairs, doseq=True)
    return f"{scheme}://{authority_host}{path}" + (f"?{query}" if query else "")
