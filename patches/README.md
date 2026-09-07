# CLIProxyAPI 한도 풀 분리 수정

**한국어** · [English](README.en.md)

대상: v7.2.152, 커밋 `c76dfd4e0edabab9000628b1560ab8ab379eadb8`.

`cliproxyapi-quota-pools.patch`는 Codex의 `usage_limit_reached`가 모든 모델로 전파되는 문제를 수정한다.

- Spark (`gpt-5.3-codex-spark`): 별도 사용량 풀.
- `gpt-5.5`, `gpt-5.6-luna`: 같은 일반 사용량 풀.
- 확인하지 않은 모델과 다른 공급자는 기존 계정 전체 차단 동작을 유지한다.
- 실제 서버가 반환한 대기 시간을 유지하며, 기존의 더 긴 대기나 비활성화 상태를 완화하지 않는다.
- 기존 인증·사용량 파일을 수정하거나 삭제하는 코드는 없다. 과거 프로세스에 잘못 잡힌 메모리 상태는 수정판 재시작으로 해제되며, 실제 한도 초과는 다음 공급자 응답으로 해당 풀에 다시 적용된다.

Dockerfile은 고정 커밋 검증 → 패치 적용 검사 → 적용 → `TestCodexQuotaPool` 테스트 → 빌드 순으로 실행한다. 버전 변경 시 패치와 풀 구성을 다시 검증해야 한다. 이 수정은 공식 릴리스가 아닌 프로젝트 로컬 수정이다.

로컬 빌드도 동일 커밋의 깨끗한 소스에서 다음 순서를 사용한다(Go 1.26 이상).

```sh
git apply --check /absolute/path/to/cliproxyapi-quota-pools.patch
git apply /absolute/path/to/cliproxyapi-quota-pools.patch
go test ./sdk/cliproxy/auth -count=1
go build -buildvcs=false -o /new/path/cli-proxy-api-poolfix ./cmd/server
```

기존 실행 파일을 보존하고 `CLIPROXYAPI_BINARY`를 새 경로로 지정한다. 실행 중인 서버는 재시작해야 반영된다. 영구 차단 상태 저장을 별도로 켠 환경은 과거 상태의 출처를 먼저 확인해야 하며, 이 패치만으로 저장된 계정 전체 차단을 자동 삭제하지 않는다.

2026-09-07 로컬 검증: Spark 요청 429 → Luna 200 → GPT-5.5 200 → Spark 재요청 즉시 429 `model_cooldown`. 인증 없는 모델 조회 401, 인증된 조회 200, 관리 경로 404 확인. 실제 사용량 조회 당시 일반 풀 1%, Spark 5시간 풀 100%였다.

위 수치는 당시 검증 기록이며 현재 계정의 잔여 사용량을 의미하지 않는다.
