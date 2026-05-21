"""payment 서브 라우트 패키지 — payment_routes.py에서 분리된 모듈들.

서브모듈:
- paddle: F4-16 Paddle 결제 라우트
- crypto: F4-17 암호화폐 결제 (Coinbase Commerce) 라우트
"""
from routes.payment import (  # noqa: F401 — 부수효과 import
    crypto,
    paddle,
)
