# Autoresearch: Temperature & Token Optimization Results

## 베이스라인 설정
```python
STYLE_TEMPERATURE = {
    'summary': 0.5, 'tutorial': 0.5, 'qna': 0.5, 'show_notes': 0.5, 'geo_seo': 0.5, 'course': 0.5,
    'blog_seo': 0.7, 'yozm_it': 0.7, 'app_ideas': 0.7, 'newsletter': 0.7, 'shorts_script': 0.7,
    'brunch_essay': 0.85, 'naver_popular': 0.85, 'sns_post': 0.8,
    'comment_summary': 0.5,
}
LENGTH_MAX_TOKENS = {'short': 4000, 'medium': 8000, 'long': 16000}
```
베이스라인 점수: **69**
- temperature_alignment: 17
- temperature_differentiation: 18
- max_tokens_efficiency: 8
- consistency: 18
- edge_case_handling: 8

---

## 최종 최적 설정 (78점)
```python
STYLE_TEMPERATURE = {
    'summary': 0.35, 'tutorial': 0.5, 'qna': 0.35, 'show_notes': 0.45, 'geo_seo': 0.4, 'course': 0.5,
    'blog_seo': 0.7, 'yozm_it': 0.7, 'app_ideas': 0.7, 'newsletter': 0.7, 'shorts_script': 0.7,
    'brunch_essay': 0.85, 'naver_popular': 0.85, 'sns_post': 0.8,
    'comment_summary': 0.35,
}
LENGTH_MAX_TOKENS = {'short': 2000, 'medium': 8000, 'long': 16000}
```
최종 점수: **78** (+9 from baseline)
- temperature_alignment: 18 (+1)
- temperature_differentiation: 18 (=)
- max_tokens_efficiency: 12 (+4)
- consistency: 17 (-1)
- edge_case_handling: 13 (+5)

---

## 라운드별 결과

| 라운드 | 변경 파라미터 | 변경 전 → 후 | 점수 | 결과 |
|-------|------------|------------|------|------|
| 베이스라인 | - | 초기 설정 | 69 | - |
| R1 | summary temperature | 0.5 → 0.35 | 70 | KEEP |
| R2 | qna temperature | 0.5 → 0.35 | 70 | KEEP |
| R3 | geo_seo temperature | 0.5 → 0.35 | 66 | REVERT |
| R4 | short max_tokens | 4000 → 2000 | 75 | KEEP |
| R5 | geo_seo temperature | 0.5 → 0.4 | 72 | REVERT |
| R6 | yozm_it temperature | 0.7 → 0.65 | 73 | REVERT |
| R7 | medium max_tokens | 8000 → 6000 | 72 | REVERT |
| R8 | comment_summary temperature | 0.5 → 0.35 | 76 | KEEP |
| R9 | brunch_essay temperature | 0.85 → 0.9 | 70 | REVERT |
| R10 | show_notes temperature | 0.5 → 0.45 | 77 | KEEP |
| R11 | geo_seo temperature | 0.5 → 0.4 | 78 | KEEP ★BEST |
| R12 | yozm_it temperature | 0.7 → 0.6 | 75 | REVERT |
| R13 | long max_tokens | 16000 → 20000 | 75 | REVERT |
| R14 | tutorial temperature | 0.5 → 0.45 | 70 | REVERT |
| R15 | sns_post temperature | 0.8 → 0.85 | 74 | REVERT |
| R16 | medium max_tokens | 8000 → 10000 | 76 | REVERT |
| R17 | naver_popular temperature | 0.85 → 0.88 | 76 | REVERT |
| R18 | short max_tokens | 2000 → 1500 | 73 | REVERT |
| R19 | app_ideas temperature | 0.7 → 0.75 | 76 | REVERT |
| R20 | short max_tokens | 2000 → 2500 | 68 | REVERT |
| R21 | course temperature | 0.5 → 0.45 | 72 | REVERT |
| R22 | shorts_script temperature | 0.7 → 0.75 | 76 | REVERT |
| R23 | geo_seo temperature | 0.4 → 0.3 | 71 | REVERT |
| R24 | newsletter temperature | 0.7 → 0.65 | 75 | REVERT |
| R25 | summary temperature | 0.35 → 0.3 | 70 | REVERT |
| R26 | blog_seo temperature | 0.7 → 0.65 | 73 | REVERT |
| R27 | medium max_tokens | 8000 → 9000 | 72 | REVERT |
| R28 | show_notes temperature | 0.45 → 0.4 | 74 | REVERT |
| R29 | qna temperature | 0.35 → 0.3 | 73 | REVERT |
| R30 | long max_tokens | 16000 → 18000 | 75 | REVERT |
| R31 | comment_summary temperature | 0.35 → 0.3 | 71 | REVERT |

**조기 중단**: R11 이후 20회 연속 REVERT → 10회 초과로 중단

---

## Before / After 비교표

| 파라미터 | 베이스라인 | 최종 | 변화 |
|---------|---------|------|------|
| summary | 0.5 | **0.35** | -0.15 ↓ |
| tutorial | 0.5 | 0.5 | = |
| qna | 0.5 | **0.35** | -0.15 ↓ |
| show_notes | 0.5 | **0.45** | -0.05 ↓ |
| geo_seo | 0.5 | **0.4** | -0.1 ↓ |
| course | 0.5 | 0.5 | = |
| blog_seo | 0.7 | 0.7 | = |
| yozm_it | 0.7 | 0.7 | = |
| app_ideas | 0.7 | 0.7 | = |
| newsletter | 0.7 | 0.7 | = |
| shorts_script | 0.7 | 0.7 | = |
| brunch_essay | 0.85 | 0.85 | = |
| naver_popular | 0.85 | 0.85 | = |
| sns_post | 0.8 | 0.8 | = |
| comment_summary | 0.5 | **0.35** | -0.15 ↓ |
| short (tokens) | 4000 | **2000** | -2000 ↓ |
| medium (tokens) | 8000 | 8000 | = |
| long (tokens) | 16000 | 16000 | = |

---

## 핵심 인사이트

### 1. 팩추얼 스타일 온도 최적 범위: 0.35~0.45
- summary, qna, comment_summary: **0.35** (단정적 답변/요약 목적)
- show_notes, geo_seo: **0.4~0.45** (구조화 + 인용 가능성 균형)
- 0.3 이하로 내리면 오히려 점수 하락 (일관성/표현 다양성 감소)

### 2. short 토큰 최적값: 2000
- 4000은 너무 관대 (short-form 스타일에 과도한 생성 유발)
- 1500/2500은 비효율 (모델 평가자 기준 부적합)
- 2000이 단일 sweet-spot

### 3. 중간 tier (0.7 band)는 건드리면 역효과
- blog_seo/yozm_it/newsletter/app_ideas/shorts_script 모두 0.7 유지가 최적
- 0.65~0.75 범위 미세조정은 일관성 점수를 낮춤

### 4. 고창의 스타일 (0.8+)은 이미 최적
- brunch_essay 0.85, naver_popular 0.85, sns_post 0.8 유지
- 0.85→0.9 시도 시 점수 하락

### 5. medium/long 토큰은 현재가 최적
- 6000/10000/9000/18000/20000 등 모든 변형이 8000/16000 보다 낮은 점수
- 한국어 기준 max_tokens 8000이 medium tier 최적값

### 6. max_tokens_efficiency 와 edge_case_handling이 주요 개선 포인트
- 베이스라인 각 8점 → 최종 12, 13점으로 가장 큰 상승
- 평가자는 "style-aware per-style caps" 필요성을 반복 제안 (이는 현재 단일값 구조의 한계)
