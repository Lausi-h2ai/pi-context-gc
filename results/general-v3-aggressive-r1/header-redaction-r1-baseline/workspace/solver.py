DEFAULT_SENSITIVE = {
    'authorization',
    'proxy-authorization',
    'cookie',
    'set-cookie',
    'x-api-key',
}

_ASCII_WHITESPACE = ' \t\n\r\v\f'


def redact_headers(headers, sensitive=()):
    """Return headers with sensitive values replaced by a redaction marker."""
    sensitive_names = DEFAULT_SENSITIVE | {
        name.strip(_ASCII_WHITESPACE).casefold() for name in sensitive
    }

    return [
        [name, '[REDACTED]' if name.strip(_ASCII_WHITESPACE).casefold() in sensitive_names else value]
        for name, value in headers
    ]
