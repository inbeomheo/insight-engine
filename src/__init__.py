"""DDD 리팩토링용 루트 패키지.

`src/` 아래의 모든 코드는 새로운 도메인 주도 설계 구조(`shared/`, `contexts/`)를
따른다. 기존 `services/`, `routes/` 트리는 점진적으로 이 구조로 마이그레이션된다.

Phase 2: Identity & Access BC 기반 구조 (도메인 모델 + Repository 인터페이스).
"""
