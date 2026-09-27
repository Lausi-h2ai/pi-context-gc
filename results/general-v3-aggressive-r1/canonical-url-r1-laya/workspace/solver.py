from urllib.parse import parse_qsl, quote_plus, urlsplit, urlunsplit


def canonical_url(url):
    if not isinstance(url, str) or any(ord(char) < 32 or ord(char) == 127 for char in url):
        raise ValueError("invalid URL")

    try:
        parsed = urlsplit(url)
        scheme = parsed.scheme.lower()
        if scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("unsupported or relative URL")
        if parsed.username is not None or parsed.password is not None or "@" in parsed.netloc:
            raise ValueError("credentials are not allowed")
        if "#" in url:
            raise ValueError("fragments are not allowed")
        hostname = parsed.hostname
        if not hostname:
            raise ValueError("missing hostname")
        port = parsed.port
    except (ValueError, UnicodeError) as exc:
        raise ValueError("invalid URL") from exc

    hostname = hostname.lower()
    if hostname.endswith("."):
        hostname = hostname[:-1]
    if not hostname:
        raise ValueError("missing hostname")
    # Bracket IPv6 literals when rebuilding the authority.
    host = f"[{hostname}]" if ":" in hostname else hostname
    if port is not None and port != (80 if scheme == "http" else 443):
        host += f":{port}"

    path = parsed.path or "/"
    trailing_slash = path.endswith("/")
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

    try:
        pairs = parse_qsl(parsed.query, keep_blank_values=True, encoding="utf-8", errors="strict")
    except (UnicodeError, ValueError) as exc:
        raise ValueError("invalid query") from exc
    pairs.sort(key=lambda pair: (pair[0], pair[1]))
    query = "&".join(f"{quote_plus(key, safe='')}={quote_plus(value, safe='')}" for key, value in pairs)
    return urlunsplit((scheme, host, path, query, ""))
