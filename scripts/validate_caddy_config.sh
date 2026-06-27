#!/usr/bin/env bash
set -euo pipefail

basic_auth_user="${BASIC_AUTH_USER:-ci-admin}"
basic_auth_hash="$(docker run --rm caddy:2-alpine caddy hash-password --plaintext ci-basic-auth-password)"
caddyfile="${CADDYFILE:-${PWD}/Caddyfile.deploy}"

reverse_proxy_count="$(grep -Ec '^[[:space:]]*reverse_proxy([[:space:]]|$)' "$caddyfile" || true)"
forwarded_host_count="$(grep -Ec '^[[:space:]]*header_up[[:space:]]+X-Forwarded-Host[[:space:]]+\{host\}[[:space:]]*$' "$caddyfile" || true)"
forwarded_proto_count="$(grep -Ec '^[[:space:]]*header_up[[:space:]]+X-Forwarded-Proto[[:space:]]+\{scheme\}[[:space:]]*$' "$caddyfile" || true)"
if [[ "$reverse_proxy_count" -eq 0 ]]; then
  printf 'ERROR: Caddyfile must define reverse_proxy routes.\n' >&2
  exit 1
fi
if [[ "$forwarded_host_count" -ne "$reverse_proxy_count" ]]; then
  printf 'ERROR: every Caddy reverse_proxy route must overwrite X-Forwarded-Host with {host}.\n' >&2
  exit 1
fi
if [[ "$forwarded_proto_count" -ne "$reverse_proxy_count" ]]; then
  printf 'ERROR: every Caddy reverse_proxy route must overwrite X-Forwarded-Proto with {scheme}.\n' >&2
  exit 1
fi

backend_matcher="$(grep -E '^[[:space:]]*@backend[[:space:]]+path[[:space:]]+' "$caddyfile" || true)"
if [[ -z "$backend_matcher" ]]; then
  printf 'ERROR: Caddyfile must define a protected @backend path matcher.\n' >&2
  exit 1
fi

for required_path in '/api/*' '/generate' '/generate-stream' '/generate-batch' '/regenerate' '/feed.xml' '/version' '/metrics' '/openapi.json' '/oauth/*' '/graphql' '/graphql/*'; do
  if [[ "$backend_matcher" != *"$required_path"* ]]; then
    printf 'ERROR: Caddy @backend matcher must include %s.\n' "$required_path" >&2
    exit 1
  fi
done

public_share_block="$(sed -n '/^[[:space:]]*@publicShare[[:space:]]*{/,/^[[:space:]]*}/p' "$caddyfile")"
if [[ -z "$public_share_block" ]]; then
  printf 'ERROR: Caddyfile must define a @publicShare matcher.\n' >&2
  exit 1
fi
if [[ "$public_share_block" != *'method GET'* ]]; then
  printf 'ERROR: Caddy @publicShare matcher must be limited to GET.\n' >&2
  exit 1
fi
for required_path in '/share/*' '/api/shares/*'; do
  if [[ "$public_share_block" != *"$required_path"* ]]; then
    printf 'ERROR: Caddy @publicShare matcher must include %s.\n' "$required_path" >&2
    exit 1
  fi
done
if [[ "$public_share_block" == *'/api/shares '* || "$public_share_block" == *'/api/shares"'* ]]; then
  printf 'ERROR: Caddy @publicShare matcher must not expose protected /api/shares create route.\n' >&2
  exit 1
fi

signed_webhook_block="$(sed -n '/^[[:space:]]*@signedInboundWebhook[[:space:]]*{/,/^[[:space:]]*}/p' "$caddyfile")"
if [[ -z "$signed_webhook_block" ]]; then
  printf 'ERROR: Caddyfile must define a @signedInboundWebhook matcher.\n' >&2
  exit 1
fi
if [[ "$signed_webhook_block" != *'method POST'* ]]; then
  printf 'ERROR: Caddy @signedInboundWebhook matcher must be limited to POST.\n' >&2
  exit 1
fi
for required_path in '/api/payment/webhook' '/api/paddle/webhook' '/api/crypto/webhook' '/api/webhooks/slack' '/api/webhooks/discord' '/api/webhooks/telegram'; do
  if [[ "$signed_webhook_block" != *"$required_path"* ]]; then
    printf 'ERROR: Caddy @signedInboundWebhook matcher must include %s.\n' "$required_path" >&2
    exit 1
  fi
done
for protected_path in '/metrics' '/openapi.json' '/graphql' '/api/*' '/generate'; do
  if [[ "$public_share_block" == *"$protected_path"* || "$signed_webhook_block" == *"$protected_path"* ]]; then
    printf 'ERROR: Caddy public matchers must not expose protected path %s.\n' "$protected_path" >&2
    exit 1
  fi
done

basic_auth_line="$(grep -n '^[[:space:]]*basic_auth[[:space:]]*{' "$caddyfile" | head -n1 | cut -d: -f1 || true)"
backend_line="$(grep -En '^[[:space:]]*@backend[[:space:]]+path[[:space:]]+' "$caddyfile" | head -n1 | cut -d: -f1 || true)"
if [[ -z "$basic_auth_line" || -z "$backend_line" || "$basic_auth_line" -ge "$backend_line" ]]; then
  printf 'ERROR: Caddy @backend matcher must remain behind basic_auth.\n' >&2
  exit 1
fi

for public_handle in '@publicShare' '@signedInboundWebhook'; do
  public_line="$(grep -n "^[[:space:]]*handle[[:space:]]\\+$public_handle[[:space:]]*{" "$caddyfile" | head -n1 | cut -d: -f1 || true)"
  if [[ -z "$public_line" || "$public_line" -ge "$basic_auth_line" ]]; then
    printf 'ERROR: Caddy handle %s must remain before basic_auth.\n' "$public_handle" >&2
    exit 1
  fi
done

docker run --rm \
  -e BASIC_AUTH_USER="${basic_auth_user}" \
  -e BASIC_AUTH_HASH="${basic_auth_hash}" \
  -v "${caddyfile}:/etc/caddy/Caddyfile:ro" \
  caddy:2-alpine caddy validate --config /etc/caddy/Caddyfile
