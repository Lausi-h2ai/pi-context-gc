DEFAULT_SENSITIVE = {
    'authorization',
    'proxy-authorization',
    'cookie',
    'set-cookie',
    'x-api-key',
}

_ASCII_WHITESPACE = ' \t\n\r\v\f'


def redact_headers(headers, sensitive=()):
    def normalize(name):
        return name.strip(_ASCII_WHITESPACE).casefold()

    sensitive_names = DEFAULT_SENSITIVE | {normalize(name) for name in sensitive}
    return [
        [name, '[REDACTED]' if normalize(name) in sensitive_names else value]
        for name, value in headers
    ]
