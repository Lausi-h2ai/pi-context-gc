DEFAULT_SENSITIVE = {
    'authorization',
    'proxy-authorization',
    'cookie',
    'set-cookie',
    'x-api-key',
}


def _normalize_header_name(name):
    """Trim ASCII whitespace and case-fold a header name for comparison."""
    return name.strip(' \t\n\r\v\f').casefold()


def redact_headers(headers, sensitive=()):
    """Return a copy of headers with sensitive values redacted."""
    sensitive_names = DEFAULT_SENSITIVE | {
        _normalize_header_name(name) for name in sensitive
    }
    return [
        [name, '[REDACTED]' if _normalize_header_name(name) in sensitive_names else value]
        for name, value in headers
    ]
