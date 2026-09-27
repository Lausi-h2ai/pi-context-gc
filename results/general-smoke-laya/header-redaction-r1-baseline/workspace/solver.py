DEFAULT_SENSITIVE = {
    'authorization',
    'proxy-authorization',
    'cookie',
    'set-cookie',
    'x-api-key',
}


def redact_headers(headers, sensitive=()):
    """Return copied headers with sensitive values redacted."""
    sensitive_names = DEFAULT_SENSITIVE | {
        name.strip(' \t\n\r\v\f').casefold() for name in sensitive
    }
    return [
        [name, '[REDACTED]' if name.strip(' \t\n\r\v\f').casefold() in sensitive_names else value]
        for name, value in headers
    ]
