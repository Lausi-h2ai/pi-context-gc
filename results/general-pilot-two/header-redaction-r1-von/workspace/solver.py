DEFAULT_SENSITIVE = {
    'authorization',
    'proxy-authorization',
    'cookie',
    'set-cookie',
    'x-api-key',
}


def redact_headers(headers, sensitive=()):
    """Return headers with sensitive values redacted, without mutating input."""
    sensitive_names = {
        name.strip(' \t\r\n\v\f').casefold()
        for name in sensitive
    }
    redact_names = DEFAULT_SENSITIVE | sensitive_names

    return [
        [
            name,
            '[REDACTED]'
            if name.strip(' \t\r\n\v\f').casefold() in redact_names
            else value,
        ]
        for name, value in headers
    ]
