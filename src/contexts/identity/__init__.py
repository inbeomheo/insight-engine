"""Identity & Access Bounded Context.

책임: 인증, 어카운트, API 키, 사용량 쿼터, 크레딧, RBAC를 단일 권위로 관리.

외부에 노출되는 진입점은 `application/ports.py`의 인터페이스이며,
다른 BC는 절대로 `domain/` 또는 `infrastructure/`를 직접 import하지 않는다.

참고: `README.md` (유비쿼터스 언어 + 의존 방향).
"""
