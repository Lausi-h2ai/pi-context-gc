DEFAULT_SENSITIVE = {
    'authorization', 'proxy-authorization', 'cookie', 'set-cookie', 'x-api-key'
}

_ASCII_WHITESPACE = ' \t\n\r\v\f'


def _normalize_header_name(name):
    return name.strip(_ASCII_WHITESPACE).casefold()


def redact_headers(headers, sensitive=()):
    sensitive_names = DEFAULT_SENSITIVE | {
        _normalize_header_name(name) for name in sensitive
    }
    return [
        [name, '[REDACTED]' if _normalize_header_name(name) in sensitive_names else value]
        for name, value in headers
    ]
