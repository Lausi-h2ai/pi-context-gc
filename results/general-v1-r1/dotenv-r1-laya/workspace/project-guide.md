# Runtime configuration loader

The worker process receives configuration from a checked-in defaults file and an optional local environment file.
The loader runs before logging starts, so parse failures must be reported as ordinary ValueError instances.
Callers use the returned mapping to construct immutable service settings.

## Ownership

config_loader.py owns syntax parsing.
startup.py owns precedence between defaults, environment variables, and command-line flags.
The deployment wrapper owns file discovery and does not interpret values.

## File conventions

Configuration files use UTF-8 text and one assignment per physical line.
Blank lines and comments are common because operators annotate emergency changes.
The optional export spelling is accepted for compatibility with shell snippets.
Keys are passed to the process environment exactly as parsed.

## Error handling

A malformed line should identify the file and line number at the caller boundary.
The parser itself raises ValueError without printing or logging.
Partial results must never escape after a malformed line.
A caller may retry with a corrected file in the same process.

## Review notes

Keep the parser independent of the operating system environment.
Do not call os.environ or read files from inside the parser.
Do not mutate the defaults mapping supplied by a caller.
Values are strings at this layer; numeric conversion belongs to schema validation.
The startup path treats repeated definitions as deliberate operator overrides.

## Compatibility

The service still supports Python 3.11 and later.
Only the standard library is available in the minimal worker image.
Tests invoke the parser directly with text fixtures.
The implementation should remain deterministic across locales and host platforms.

This guide describes module boundaries and operational context; the function contract remains the authority for syntax details.