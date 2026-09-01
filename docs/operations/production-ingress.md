# Production ingress

`insight.fiv.co.kr`의 유일한 origin은 로컬 Caddy edge여야 해.

```text
Cloudflare Tunnel public hostname
  insight.fiv.co.kr  ->  http://localhost:8090
```

`localhost:3000`(Next)이나 `localhost:5001`(Flask)을 직접 지정하면 Caddy의 Basic
Auth와 보안 헤더를 우회하므로 금지해. Cloudflare Zero Trust 대시보드에서 Public
Hostname 설정을 바꾼 뒤 다음을 확인해.

```bash
# 인증 없는 페이지/API는 challenge를 반환해야 한다.
curl -si https://insight.fiv.co.kr/ | sed -n '1,15p'
curl -si https://insight.fiv.co.kr/api/notes | sed -n '1,15p'

# 공개 공유 페이지와 health만 정책상 허용된 상태인지 별도로 확인한다.
curl -si https://insight.fiv.co.kr/health | sed -n '1,15p'
```

배포 전 `caddy validate --config /etc/caddy/Caddyfile`와
`docker compose -f docker-compose.deploy.yml config --quiet`를 통과시켜.
