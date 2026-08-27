# Security policy

Please report suspected vulnerabilities through GitHub's private vulnerability
reporting flow instead of opening a public issue. Include the affected route or
component, reproduction steps, and the impact you observed. Do not include live
credentials or personal data.

## Supported version

Security fixes are applied to the repository's default `master` branch. Run the
production readiness check and the full verification suite before deploying a
revision from that branch.

## ChromaDB deployment boundary

Insight Engine uses ChromaDB only as an embedded, filesystem-backed
`PersistentClient`. It must never expose Chroma's HTTP server, CLI server mode,
or `HttpClient` to a network. Application routes create collections from fixed
server-side configuration; callers cannot supply embedding-function repositories
or `trust_remote_code` settings.

This boundary is currently a required compensating control for the following
upstream advisories, for which ChromaDB 1.5.9 has no patched PyPI release:

- `CVE-2026-45829` / `PYSEC-2026-311`
- `CVE-2026-45830`
- `CVE-2026-45831`
- `CVE-2026-45833`

These advisories affect Chroma's network server collection/authentication APIs,
which this deployment does not start. Remove the temporary audit exception as
soon as Chroma publishes a compatible patched release. A dependency update must
still pass the embedded-client and account-isolation tests before deployment.
