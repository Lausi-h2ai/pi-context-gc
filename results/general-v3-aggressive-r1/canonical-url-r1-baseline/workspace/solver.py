from urllib.parse import parse_qsl, quote_plus, urlsplit


def canonical_url(url):
    if not isinstance(url, str) or any(ord(char) < 32 or ord(char) == 127 for char in url):
        raise ValueError("invalid URL")

    try:
        parsed = urlsplit(url)
        scheme = parsed.scheme.lower()
        if scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("unsupported or non-absolute URL")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("credentials are not allowed")
        if "#" in url:
            raise ValueError("fragments are not allowed")

        host = parsed.hostname
        if not host:
            raise ValueError("missing host")
        host = host.lower()
        if ":" not in host and host.endswith("."):
            host = host[:-1]
        if not host:
            raise ValueError("missing host")

        port = parsed.port
        if ":" not in host and any(not label for label in host.split(".")):
            raise ValueError("invalid host")
    except (ValueError, UnicodeError) as exc:
        raise ValueError("invalid URL") from exc

    # Preserve IPv6 authority brackets; urlsplit.hostname omits them.
    if ":" in host:
        authority_host = "[" + host + "]"
    else:
        authority_host = host
    if port is not None and port != (80 if scheme == "http" else 443):
        authority = f"{authority_host}:{port}"
    else:
        authority = authority_host

    raw_path = parsed.path or "/"
    trailing_slash = raw_path.endswith("/")
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
    if trailing_slash and path != "/":
        path += "/"

    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    pairs.sort(key=lambda pair: (pair[0], pair[1]))
    query = "&".join(
        quote_plus(key, safe="") + "=" + quote_plus(value, safe="")
        for key, value in pairs
    )
    return f"{scheme}://{authority}{path}" + ("?" + query if query else "")
