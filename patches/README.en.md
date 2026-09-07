# CLIProxyAPI Quota-Pool Isolation Patch

[한국어](README.md) · **English**

Target: v7.2.152, commit `c76dfd4e0edabab9000628b1560ab8ab379eadb8`.

`cliproxyapi-quota-pools.patch` fixes propagation of a Codex `usage_limit_reached` error to all models.

- Spark (`gpt-5.3-codex-spark`): separate allowance pool.
- `gpt-5.5` and `gpt-5.6-luna`: shared standard pool.
- Unverified models and other providers retain the existing credential-wide blocking behavior.
- Upstream reset deadlines are preserved. Existing longer cooldowns and disabled states are not weakened.
- The patch does not modify or delete authentication or usage files. Restarting the patched process clears incorrectly propagated in-memory state; the next upstream limit response reapplies any genuine cooldown to its pool.

The Dockerfile verifies the pinned commit, checks and applies the patch, runs `TestCodexQuotaPool`, and builds the binary. Revalidate the patch and pool mapping when upgrading. This is a project-local modification, not an official release fix.

For local builds, start from a clean checkout of the same pinned commit and use Go 1.26 or later:

```sh
git apply --check /absolute/path/to/cliproxyapi-quota-pools.patch
git apply /absolute/path/to/cliproxyapi-quota-pools.patch
go test ./sdk/cliproxy/auth -count=1
go build -buildvcs=false -o /new/path/cli-proxy-api-poolfix ./cmd/server
```

Preserve the original executable and point `CLIPROXYAPI_BINARY` to the new binary. Restart the running gateway to activate it. If persistent cooldown storage was enabled separately, inspect the origin of the saved state first: this patch does not automatically delete persisted credential-wide blocks.

Local verification on 2026-09-07: Spark returned 429 → Luna returned 200 → GPT-5.5 returned 200 → a second Spark request immediately returned 429 `model_cooldown`. Anonymous model-list access returned 401, authenticated access returned 200, and management paths returned 404. At the time of the usage query, the standard pool was 1% used and Spark's five-hour pool was 100% used. These are historical observations, not current account balances.
