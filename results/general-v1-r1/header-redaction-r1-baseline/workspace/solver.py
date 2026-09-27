DEFAULT_SENSITIVE = {
    'authorization',
    'proxy-authorization',
    'cookie',
    'set-cookie',
    'x-api-key',
}


def redact_headers(headers, sensitive=()):
    sensitive_names = {
        name.strip(' \t\n\r\v\f').casefold() for name in sensitive
    }
    redacted_names = DEFAULT_SENSITIVE | sensitive_names
    return [
        [
            name,
            '[REDACTED]'
            if name.strip(' \t\n\r\v\f').casefold() in redacted_names
            else value,
        ]
        for name, value in headers
    ]
