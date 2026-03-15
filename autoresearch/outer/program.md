# Autoresearch Frontend — Program.md

## 프로젝트
Insight Engine — YouTube URL로 AI 콘텐츠를 생성하는 Next.js 16 + Tailwind v4 웹 앱

## 개선 목표
**접근성 심화 (WCAG AA)** — 스크린리더, 키보드 내비게이션, 색상 대비, 시맨틱 HTML 완성

## 전략 (Outer Loop Round 3)
error=100, dom=100, form=99, visual=97까지 올라옴.
dom + form 축에서 WCAG AA 수준의 접근성 심화를 목표로 전환.

### 개선 방향
- WCAG AA 준수: 색상 대비 4.5:1 이상, 포커스 표시 명확화
- 스크린리더 지원: aria-live, aria-describedby, aria-expanded 등 보강
- 키보드 내비게이션 완성: Tab 순서, 포커스 트랩 (모달/팝오버)
- 시맨틱 HTML: 올바른 heading 계층, landmark 보강

### 주의사항
- SSR 하이드레이션 에러 회피: 조건부 렌더링 블록 내에서만 변경
- 기존 error=100, dom=100, form=99, visual=97 성과 보존 필수
- 한 번에 하나의 가설만 테스트

## 테스트 URL
- http://localhost:3000 (메인 — URL 입력, 생성, 결과 카드, 설정)

## 핵심 사용자 흐름
1. URL 입력 → Enter로 추가
2. AI 모델/스타일 선택
3. 생성 버튼 클릭
4. 결과 카드 확인 (복사, 내보내기, 더보기 메뉴)
5. 사이드바 탐색 (라이브러리, 캘린더, 설정)

## 접근성 심화 방향 (에이전트가 참고)
- 드롭다운 메뉴 aria-expanded 보강
- 토글 버튼 aria-describedby로 상태 설명 추가
- 카드 접기/펼치기 aria-expanded 연동
- 히스토리 목록에 aria-live="polite" (동적 변경 알림)
- heading 계층 검증 (h1→h2→h3 건너뛰기 없음)
- 이미지/아이콘 aria-hidden 일관성
- 포커스 순서 논리적 정렬

## 수정 가능 파일
- frontend/components/**/*.tsx
- frontend/hooks/**/*.ts
- frontend/app/**/*.tsx
- frontend/stores/**/*.ts

## 수정 불가 파일 (절대 건드리지 않음)
- autoresearch/eval/**
- autoresearch/meta_eval/**
- backend (Python 코드 전체)
- frontend/lib/api.ts (API 통신)

## Inner Loop 설정
- 라운드당 실험 수: 5
- 한 번에 하나의 가설만 테스트
- 모든 변경은 TypeScript 타입체크 통과 필수
