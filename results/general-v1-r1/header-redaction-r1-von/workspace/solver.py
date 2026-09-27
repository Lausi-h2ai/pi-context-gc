DEFAULT_SENSITIVE = {
    'authorization', 'proxy-authorization', 'cookie', 'set-cookie', 'x-api-key'
}


def _normalize_header_name(name):
    """Normalize a header name for case-insensitive matching."""
    return name.strip(' \t\n\v\f\r').casefold()


def redact_headers(headers, sensitive=()):
    """Return copied header pairs with sensitive values redacted."""
    sensitive_names = DEFAULT_SENSITIVE | {
        _normalize_header_name(name) for name in sensitive
    }
    return [
        [name, '[REDACTED]' if _normalize_header_name(name) in sensitive_names else value]
        for name, value in headers
    ]
