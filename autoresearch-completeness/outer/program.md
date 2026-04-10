# Autoresearch Program: 완성도 높이기

## 목표
복합 점수 100/100 달성 (현재 ~89.7)

## 현재 문제점 (베이스라인 2026-04-10)
1. pytest 에러 13개 (collection 1 + runtime 12)
   - test_research_agent.py: collection 에러 (import 문제)
   - test_credit_service.py: 3개 에러 (tmp_path 관련)
   - test_multi_source_cleanup.py: 1개 에러 (tmp_path)
   - test_whisper_cleanup.py: 2개 에러 (tmp_path)
   - test_whisper_download_audio.py: 3개 에러 (tmp_path)
2. TypeScript: 0 에러 (클린)
3. Next.js 빌드: 성공
4. Python 문법: 0 에러

## 우선순위
1. **P0**: pytest 에러 13개 → 0개 (가장 큰 점수 향상)
2. **P1**: pytest failed 테스트 수정 (있다면)
3. **P2**: 미커버 서비스에 대한 기본 테스트 추가
4. **P3**: 코드 품질 경고 제거

## 수정 범위 제한
- target 파일만 수정 (tests/, services/, routes/)
- eval/measure.py 절대 수정 금지
- 기존 동작하는 코드를 깨뜨리지 않을 것

## 실험 전략
- 한 번에 1-2개 테스트 파일 수정
- 수정 후 반드시 pytest 재실행으로 검증
- 회귀 발생 시 즉시 revert
