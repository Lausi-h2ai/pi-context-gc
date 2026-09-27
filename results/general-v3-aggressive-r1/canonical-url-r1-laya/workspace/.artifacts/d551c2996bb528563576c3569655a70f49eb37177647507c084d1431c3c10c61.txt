# HTTP cache key notes

The client cache stores GET responses by a canonical URL string.
The cache is shared by the request layer and the offline replay tool.
A key must identify the same origin and resource for every supported spelling.

## Request flow

request.py parses a URL, applies the transport policy, and asks cache.py for a key.
The transport layer rejects credentials before opening a socket.
Redirect handling is outside this helper and supplies a fresh URL on every hop.
Fragments are browser-only state and are never sent to the HTTP server.

## Authority conventions

The supported schemes are HTTP and HTTPS.
Host names are case-insensitive and service records occasionally include a terminal dot.
Default ports are omitted from cache keys so equivalent configuration does not fork entries.
Non-default ports remain part of the authority.

## Path conventions

The origin server treats repeated separators and dot segments as equivalent resource paths.
The canonical form always begins with a slash.
A trailing slash can distinguish a collection endpoint from its parent resource.
Unicode path text is retained for diagnostics and is encoded by the transport boundary later.

## Query conventions

Query order has no semantic meaning for this API.
Blank values are meaningful because feature flags use a key with an empty value.
Repeated keys are allowed and sorted by their key and value pair.
Form encoding is used for the canonical query representation.

## Safety and testing

Credentials, fragments, malformed ports, and unsupported schemes must fail before caching.
Do not perform DNS lookups or network I/O while building a key.
The helper has no global cache and must return the same value for the same input.
The implementation is used by both synchronous and asynchronous clients.

This guide gives repository context; the function contract defines the exact normalization boundary.