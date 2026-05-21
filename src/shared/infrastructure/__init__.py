"""Shared infrastructure adapters — cross-cutting 인프라 모듈 모음.

BC(Bounded Context) 간 공유되는 외부 시스템(Supabase, 캐시, 로그 등) 어댑터.
각 BC는 인터페이스(`application/ports.py`)에만 의존하며 본 모듈을 직접 import하지 않는다.
오직 인프라 어댑터(`infrastructure/*.py`)에서만 본 모듈을 사용한다.
"""
