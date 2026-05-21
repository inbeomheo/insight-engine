# Identity & Access BC

## 책임
인증·계정·API 키·사용량·크레딧·RBAC를 단일 권위로 관리하는 Bounded Context.

## 유비쿼터스 언어
- **UserAccount**: 인증 가능한 사용자 단위 (auth.users.id를 AccountId로)
- **ApiKey**: BYO(Bring Your Own) 또는 공유 키. 평문은 Vault에만 존재
- **UsageQuota**: 일일 사용량 카운터 (기본 20회, decrement_usage_safe RPC로 원자적 차감)
- **CreditBalance**: 결제 기반 크레딧 잔액 (Billing BC와 연동)
- **RbacRole**: admin/owner/editor/viewer 역할

## Aggregate
**UserAccount** (루트) — ApiKey[], UsageQuota, CreditBalance, RbacRole[].

## 외부 ACL
- `IAccountRepository` — 어카운트 영속화 (SupabaseAccountRepository 구현)
- `IApiKeyVault` — API 키 평문 안전 저장
- `IUsageGateway` — 데코레이터/미들웨어에서 사용량 차감 호출

## 의존 방향
- 다른 BC → Identity: `IAccountRepository`, `IApiKeyVault` 인터페이스만
- Identity → 다른 BC: 없음 (단방향)
- Identity → Infrastructure: Supabase 클라이언트는 `_get_client()`로 lazy

## 현재 진척
- Phase 2-a/b/c: 기반 구조 완료 (이 디렉토리)
- Phase 2-d/e/f: NotImplementedError 영역 — 다음 PR
- Phase 2-g: 50개 호출처 점진 마이그레이션
