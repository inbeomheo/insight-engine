# Identity & Access BC

## 책임
인증·계정·API 키·사용량·RBAC를 단일 권위로 관리하며, 미래 Billing 경계를 위한
크레딧 값 객체만 보유하는 Bounded Context.

## 유비쿼터스 언어
- **UserAccount**: 인증 가능한 사용자 단위 (auth.users.id를 AccountId로)
- **ApiKey**: BYO(Bring Your Own) 또는 공유 키. 평문은 Vault에만 존재
- **UsageQuota**: 일일 사용량 카운터 (기본 20회, decrement_usage_safe RPC로 원자적 차감)
- **CreditBalance**: 미래 Billing BC 연동용 값 객체. 현재 영속 원장은 없으며 항상 0으로 조립
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
- 계정 조회·저장, API 키 Vault, 단일 사용량 차감 구현 완료
- 비용 작업용 멱등 예약·소유권 검증·환불 원장 구현 완료
- 결제 크레딧은 미구현 상태를 명시하며, 존재하지 않는 `ie_credits` 테이블로 폴백하지 않음
- 기존 `services/data/*` 직접 호출처는 ACL 뒤로 점진 마이그레이션 중
