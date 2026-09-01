# Insight Engine Docker 볼륨 백업·복원

운영 데이터는 Compose named volume에 저장돼. 백업은 서비스를 멈추지 않고
읽기 전용으로 생성할 수 있지만, **복원은 컨테이너를 중지하고 운영자 확인 후** 수행해.

## 백업

```bash
mkdir -p "$HOME/backups/insight-engine"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)

for NAME in insight_app_data insight_app_cache insight_app_logs \
            insight_redis_data insight_media_redis_data; do
  docker run --rm \
    -v "insight-engine_${NAME}:/source:ro" \
    -v "$HOME/backups/insight-engine:/backup" \
    caddy@sha256:77c07d5ebfa5be9fd6c820d2094ae662c9e7eeb9bf98346b7f639900263ee2a2 \
    sh -c "cd /source && tar -czf /backup/${NAME}_${STAMP}.tar.gz ."
done

sha256sum "$HOME/backups/insight-engine/"*"_${STAMP}.tar.gz" \
  > "$HOME/backups/insight-engine/SHA256SUMS_${STAMP}"
```

모델 캐시는 재다운로드할 수 있어서 필수 대상에서 제외했어. 앱 데이터 내부 파일
단위 리허설은 기존 `python scripts/backup_app_data.py rehearse`로 추가 검증해.

## 복원 리허설

운영 볼륨 대신 임시 볼륨에 먼저 복원하고 파일 목록과 checksum을 확인해.

```bash
docker volume create insight-restore-rehearsal
docker run --rm \
  -v insight-restore-rehearsal:/target \
  -v "$HOME/backups/insight-engine:/backup:ro" \
  caddy@sha256:77c07d5ebfa5be9fd6c820d2094ae662c9e7eeb9bf98346b7f639900263ee2a2 \
  sh -c 'cd /target && tar -xzf /backup/<archive>.tar.gz && find . -type f -print'
```

## 운영 복원

> 경고: 아래 작업은 현재 데이터를 덮어쓸 수 있어. 백업 checksum 검증과 사용자
> 확인 없이 실행하면 안 돼.

1. `docker compose -f docker-compose.deploy.yml stop backend media-worker redis media-redis`
2. 대상 볼륨의 별도 안전 백업을 한 번 더 생성해.
3. 빈 임시 볼륨에 복원해 검증해.
4. 승인 후 대상 볼륨을 비우고 archive를 복원해.
5. 컨테이너를 시작하고 `/ready`, 노트 목록, Redis queue를 확인해.

정기 백업은 이 절차를 cron/systemd timer로 호출하고, 최소 1개 사본을 호스트 밖에
보관해.
