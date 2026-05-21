"""Bounded Context 루트 패키지.

각 하위 패키지는 독립된 BC이며, 다음 4계층 구조를 따른다.

```
contexts/<bc_name>/
  domain/         # 엔티티, 값 객체, 도메인 서비스, 이벤트, 예외
  application/    # 유스케이스, 포트(인터페이스/ACL), 어플리케이션 서비스
  infrastructure/ # 포트 구현 (Supabase, 외부 API 등)
  interface/      # HTTP 라우트/CLI/스케줄러 어댑터
```

BC 간 통신은 `application/ports.py`의 인터페이스를 통해서만 허용된다.
다른 BC의 `domain/` 또는 `infrastructure/`를 직접 import하면 안 됨.
"""
