# 콘텐츠 퓨전 엔진 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 같은 주제의 영상 N개 + AI 자동 검색 외부 소스 + 댓글 심층 분석을 융합하여 최종 1편의 완벽한 글을 생성하는 3단계 파이프라인 구현

**Architecture:** 3단계 파이프라인 — Phase 1(소스 수집, 병렬) → Phase 2(분석/압축, 병렬) → Phase 3(융합 생성). 기존 ThreadPoolExecutor 병렬 패턴과 LiteLLM AI 호출 패턴을 재사용. 각 단계 결과는 SQLite 캐시.

**Tech Stack:** Flask, LiteLLM, trafilatura(웹 크롤링), duckduckgo-search(검색), Next.js/React/Zustand(프론트엔드)

**Design Doc:** `docs/plans/2026-02-19-content-fusion-engine-design.md`

---

## Task 1: 의존성 추가

**Files:**
- Modify: `requirements.txt`

**Step 1: requirements.txt에 신규 패키지 추가**

```
trafilatura>=1.6.0
duckduckgo-search>=4.0.0
```

`requirements.txt` 맨 끝에 추가한다.

**Step 2: 패키지 설치**

Run: `pip install trafilatura>=1.6.0 duckduckgo-search>=4.0.0`
Expected: Successfully installed

**Step 3: 설치 확인**

Run: `python -c "import trafilatura; print(trafilatura.__version__)" && python -c "from duckduckgo_search import DDGS; print('DDGS OK')"`
Expected: 버전 출력 + "DDGS OK"

**Step 4: 커밋**

```bash
git add requirements.txt
git commit -m "deps: trafilatura, duckduckgo-search 추가 (퓨전 엔진용)"
```

---

## Task 2: 댓글 심층 분석 프롬프트

**Files:**
- Create: `prompts/fusion/__init__.py`
- Create: `prompts/fusion/comment_analyzer.py`

**Step 1: 실패하는 테스트 작성**

Create: `tests/test_fusion_prompts.py`

```python
"""퓨전 프롬프트 모듈 테스트"""
import unittest


class TestCommentAnalyzerPrompt(unittest.TestCase):

    def test_comment_analyzer_prompt_exists(self):
        from prompts.fusion.comment_analyzer import COMMENT_ANALYZER_PROMPT
        self.assertIsInstance(COMMENT_ANALYZER_PROMPT, str)
        self.assertIn('인사이트', COMMENT_ANALYZER_PROMPT)
        self.assertIn('질문', COMMENT_ANALYZER_PROMPT)
        self.assertIn('반론', COMMENT_ANALYZER_PROMPT)

    def test_comment_analyzer_prompt_has_output_format(self):
        from prompts.fusion.comment_analyzer import COMMENT_ANALYZER_PROMPT
        self.assertIn('JSON', COMMENT_ANALYZER_PROMPT)


if __name__ == '__main__':
    unittest.main()
```

**Step 2: 테스트 실패 확인**

Run: `pytest tests/test_fusion_prompts.py -v`
Expected: FAIL (ModuleNotFoundError)

**Step 3: 프롬프트 구현**

Create: `prompts/fusion/__init__.py`

```python
"""퓨전 엔진 전용 프롬프트 모듈"""
from .comment_analyzer import COMMENT_ANALYZER_PROMPT

__all__ = ['COMMENT_ANALYZER_PROMPT']
```

Create: `prompts/fusion/comment_analyzer.py`

```python
"""댓글 심층 분석 프롬프트 — 댓글을 4가지 카테고리로 분류"""

COMMENT_ANALYZER_PROMPT = '''
# 역할: 시청자 댓글 심층 분석가

당신은 YouTube 영상의 댓글을 분석하여 4가지 카테고리로 분류하는 전문가입니다.

## 분류 기준

### 1. insights (인사이트)
- 영상에 없는 추가 정보, 실제 사용 경험, 전문가 의견
- 예: "실제로 써봤는데 A보다 B가 더 좋았어요"

### 2. questions (질문)
- 시청자가 자주 묻는 궁금증, 추가 설명이 필요한 부분
- 비슷한 질문은 대표 1개로 통합
- 예: "그러면 C 환경에서도 동작하나요?"

### 3. fact_checks (반론/지적)
- 영상 내용에 대한 반대 의견, 오류 지적, 정정 사항
- 근거가 있는 지적만 포함 (단순 비난 제외)
- 예: "영상에서 X라고 했는데 공식 문서에는 Y라고 되어 있어요"

### 4. sentiments (감상)
- 단순 호응, 감상, 칭찬, 기대감
- 핵심 감상만 대표적으로 2~3개

## 규칙
1. 스팸, 욕설, 광고 댓글은 제외
2. 좋아요 수가 많은 댓글에 가중치 부여
3. 한국어로 작성
4. 각 카테고리는 비어있을 수 있음

## 금지 표현
놀라운, 혁신적, 획기적, 최고의, 게임체인저, 압도적, 경이로운, 드디어, 탁월한, 인상적, 뛰어난

## 출력 형식 (JSON)

```json
{
  "insights": [
    "실제 경험에 기반한 인사이트 1",
    "전문가 의견 기반 인사이트 2"
  ],
  "questions": [
    "자주 묻는 질문 1",
    "자주 묻는 질문 2"
  ],
  "fact_checks": [
    "영상의 X 주장에 대해 Y라는 반론이 있음 (근거: Z)"
  ],
  "sentiments": [
    "대표적인 감상 1",
    "대표적인 감상 2"
  ]
}
```

반드시 유효한 JSON만 출력하세요. 다른 텍스트는 포함하지 마세요.
'''
```

**Step 4: 테스트 통과 확인**

Run: `pytest tests/test_fusion_prompts.py -v`
Expected: PASS (2 tests)

**Step 5: 커밋**

```bash
git add prompts/fusion/ tests/test_fusion_prompts.py
git commit -m "feat: 댓글 심층 분석 프롬프트 추가 (4가지 분류: 인사이트/질문/반론/감상)"
```

---

## Task 3: 퓨전 통합 프롬프트

**Files:**
- Create: `prompts/fusion/fusion_prompt.py`
- Modify: `prompts/fusion/__init__.py`
- Modify: `tests/test_fusion_prompts.py`

**Step 1: 실패하는 테스트 작성**

`tests/test_fusion_prompts.py`에 추가:

```python
class TestFusionPrompt(unittest.TestCase):

    def test_fusion_prompt_exists(self):
        from prompts.fusion.fusion_prompt import FUSION_PROMPT
        self.assertIsInstance(FUSION_PROMPT, str)
        self.assertIn('융합', FUSION_PROMPT)

    def test_build_fusion_context(self):
        from prompts.fusion.fusion_prompt import build_fusion_context
        ctx = build_fusion_context(
            video_summaries=[{'title': 'V1', 'summary': 'S1'}],
            comment_analysis={'insights': ['I1'], 'questions': ['Q1'],
                              'fact_checks': [], 'sentiments': []},
            web_sources=[{'title': 'W1', 'summary': 'WS1', 'url': 'http://ex.com'}]
        )
        self.assertIn('V1', ctx)
        self.assertIn('I1', ctx)
        self.assertIn('W1', ctx)

    def test_build_fusion_context_empty_optional(self):
        from prompts.fusion.fusion_prompt import build_fusion_context
        ctx = build_fusion_context(
            video_summaries=[{'title': 'V1', 'summary': 'S1'}],
            comment_analysis=None,
            web_sources=None
        )
        self.assertIn('V1', ctx)
        self.assertNotIn('[댓글 분석]', ctx)
```

**Step 2: 테스트 실패 확인**

Run: `pytest tests/test_fusion_prompts.py::TestFusionPrompt -v`
Expected: FAIL

**Step 3: 퓨전 프롬프트 구현**

Create: `prompts/fusion/fusion_prompt.py`

```python
"""퓨전 통합 프롬프트 — 여러 소스를 융합하여 최종 글 생성"""

FUSION_PROMPT = '''
# 역할: 다중 소스 융합 에디터

당신은 여러 YouTube 영상, 시청자 댓글, 외부 기사의 정보를 융합하여
하나의 완벽한 글을 작성하는 전문 에디터입니다.

## 핵심 원칙

1. **중복 제거, 고유 관점 보존**: 영상마다 겹치는 내용은 한 번만, 각 영상만의 고유한 인사이트는 반드시 포함
2. **댓글 인사이트 녹여내기**: "시청자들의 실제 경험에 따르면...", "댓글에서 자주 언급된 바와 같이..." 형태로 본문 중간에 자연스럽게 반영
3. **팩트체크 인라인 표시**: 댓글에서 지적된 오류는 본문 해당 위치에 "> ⚠️ **팩트체크**: ..." 형태로 표시
4. **FAQ 섹션**: 댓글의 질문들을 정리하여 글 말미에 "## 자주 묻는 질문" 섹션으로 구성 (Q&A 형식)
5. **출처 표시**: 외부 소스 정보 사용 시 "[출처: 기사제목]" 형태로 인라인 표시
6. **참고 소스 목록**: 글 맨 끝에 "## 참고 소스" 섹션으로 모든 소스 나열

## 금지 사항
- 소스에 없는 정보 창작/추측 절대 금지
- 금지 표현: 놀라운, 혁신적, 획기적, 최고의, 게임체인저, 압도적, 경이로운, 드디어, 탁월한, 인상적, 뛰어난, 강력한
- 댓글 섹션이 입력에 없으면 시청자 반응 절대 언급 금지

## 출력 형식
- 마크다운
- 제목은 # 하나만
- 본문 → FAQ(있으면) → 참고 소스 순서
'''


def build_fusion_context(video_summaries, comment_analysis=None, web_sources=None):
    """Phase 1~2 결과를 Phase 3 입력용 컨텍스트 문자열로 조합

    Args:
        video_summaries: [{'title': str, 'summary': str}, ...]
        comment_analysis: {'insights': [...], 'questions': [...],
                           'fact_checks': [...], 'sentiments': [...]} 또는 None
        web_sources: [{'title': str, 'summary': str, 'url': str}, ...] 또는 None

    Returns:
        str: 통합 컨텍스트 문자열
    """
    parts = []

    # 영상 요약
    parts.append('[영상 요약]')
    for i, v in enumerate(video_summaries, 1):
        parts.append(f'\n### 영상 {i}: {v["title"]}\n{v["summary"]}')

    # 댓글 분석
    if comment_analysis:
        parts.append('\n\n[댓글 분석]')
        if comment_analysis.get('insights'):
            parts.append('\n#### 인사이트 (본문에 녹여내기)')
            for item in comment_analysis['insights']:
                parts.append(f'- {item}')
        if comment_analysis.get('questions'):
            parts.append('\n#### 질문 (FAQ 섹션용)')
            for item in comment_analysis['questions']:
                parts.append(f'- {item}')
        if comment_analysis.get('fact_checks'):
            parts.append('\n#### 팩트체크 (인라인 표시)')
            for item in comment_analysis['fact_checks']:
                parts.append(f'- {item}')
        if comment_analysis.get('sentiments'):
            parts.append('\n#### 감상')
            for item in comment_analysis['sentiments']:
                parts.append(f'- {item}')

    # 외부 소스
    if web_sources:
        parts.append('\n\n[외부 소스]')
        for ws in web_sources:
            parts.append(f'\n#### {ws["title"]} ({ws["url"]})\n{ws["summary"]}')

    return '\n'.join(parts)
```

`prompts/fusion/__init__.py` 업데이트:

```python
"""퓨전 엔진 전용 프롬프트 모듈"""
from .comment_analyzer import COMMENT_ANALYZER_PROMPT
from .fusion_prompt import FUSION_PROMPT, build_fusion_context

__all__ = ['COMMENT_ANALYZER_PROMPT', 'FUSION_PROMPT', 'build_fusion_context']
```

**Step 4: 테스트 통과 확인**

Run: `pytest tests/test_fusion_prompts.py -v`
Expected: PASS (5 tests)

**Step 5: 커밋**

```bash
git add prompts/fusion/ tests/test_fusion_prompts.py
git commit -m "feat: 퓨전 통합 프롬프트 + build_fusion_context 헬퍼 추가"
```

---

## Task 4: 댓글 심층 분석 서비스

**Files:**
- Create: `services/comment_analyzer_service.py`
- Create: `tests/test_comment_analyzer_service.py`

**Step 1: 실패하는 테스트 작성**

Create: `tests/test_comment_analyzer_service.py`

```python
"""댓글 심층 분석 서비스 테스트"""
import unittest
from unittest.mock import patch, MagicMock


class TestCommentAnalyzerService(unittest.TestCase):

    @patch('services.comment_analyzer_service.ai_service')
    def test_analyze_comments_returns_structured_result(self, mock_ai):
        mock_ai.create_content.return_value = {
            'content': '{"insights":["I1"],"questions":["Q1"],"fact_checks":[],"sentiments":["S1"]}',
            'usage': {'total_tokens': 100}
        }
        from services.comment_analyzer_service import analyze_comments
        result = analyze_comments(
            comments=['좋은 영상입니다', '실제로 써봤는데 좋았어요'],
            model='gemini/gemini-3-flash-preview'
        )
        self.assertIn('insights', result)
        self.assertIn('questions', result)
        self.assertIn('fact_checks', result)
        self.assertIn('sentiments', result)
        self.assertEqual(result['insights'], ['I1'])

    @patch('services.comment_analyzer_service.ai_service')
    def test_analyze_comments_empty_list(self, mock_ai):
        from services.comment_analyzer_service import analyze_comments
        result = analyze_comments(comments=[], model='gemini/gemini-3-flash-preview')
        self.assertIsNone(result)
        mock_ai.create_content.assert_not_called()

    @patch('services.comment_analyzer_service.ai_service')
    def test_analyze_comments_ai_failure_returns_none(self, mock_ai):
        mock_ai.create_content.side_effect = Exception('AI error')
        from services.comment_analyzer_service import analyze_comments
        result = analyze_comments(
            comments=['test comment'],
            model='gemini/gemini-3-flash-preview'
        )
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
```

**Step 2: 테스트 실패 확인**

Run: `pytest tests/test_comment_analyzer_service.py -v`
Expected: FAIL (ModuleNotFoundError)

**Step 3: 서비스 구현**

Create: `services/comment_analyzer_service.py`

```python
"""댓글 심층 분석 서비스 — 댓글을 인사이트/질문/반론/감상으로 분류"""
import json
import logging

from services import ai_service
from prompts.fusion.comment_analyzer import COMMENT_ANALYZER_PROMPT

logger = logging.getLogger(__name__)


def analyze_comments(comments, model):
    """댓글 리스트를 AI로 심층 분석하여 4가지 카테고리로 분류

    Args:
        comments: 댓글 문자열 리스트
        model: LiteLLM 모델 ID

    Returns:
        dict: {'insights': [...], 'questions': [...],
               'fact_checks': [...], 'sentiments': [...]}
        None: 댓글이 없거나 분석 실패 시
    """
    if not comments:
        return None

    comments_text = '\n'.join(f'- {c}' for c in comments[:50])
    content = f'다음 댓글들을 분석해주세요:\n\n{comments_text}'

    try:
        result = ai_service.create_content(
            content=content,
            model=model,
            style_prompt=COMMENT_ANALYZER_PROMPT,
            style_id='comment_summary'
        )
        raw = result.get('content', '')
        # JSON 블록 추출 (```json ... ``` 형태 처리)
        if '```json' in raw:
            raw = raw.split('```json')[1].split('```')[0]
        elif '```' in raw:
            raw = raw.split('```')[1].split('```')[0]
        parsed = json.loads(raw.strip())
        return {
            'insights': parsed.get('insights', []),
            'questions': parsed.get('questions', []),
            'fact_checks': parsed.get('fact_checks', []),
            'sentiments': parsed.get('sentiments', []),
            'usage': result.get('usage', {})
        }
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning('댓글 분석 JSON 파싱 실패: %s', e)
        return None
    except Exception as e:
        logger.error('댓글 심층 분석 실패: %s', e)
        return None
```

**Step 4: 테스트 통과 확인**

Run: `pytest tests/test_comment_analyzer_service.py -v`
Expected: PASS (3 tests)

**Step 5: 커밋**

```bash
git add services/comment_analyzer_service.py tests/test_comment_analyzer_service.py
git commit -m "feat: 댓글 심층 분석 서비스 (인사이트/질문/반론/감상 4분류)"
```

---

## Task 5: 웹 리서치 서비스

**Files:**
- Create: `services/web_research_service.py`
- Create: `tests/test_web_research_service.py`

**Step 1: 실패하는 테스트 작성**

Create: `tests/test_web_research_service.py`

```python
"""웹 리서치 서비스 테스트"""
import unittest
from unittest.mock import patch, MagicMock


class TestExtractKeywords(unittest.TestCase):

    @patch('services.web_research_service.ai_service')
    def test_extract_keywords(self, mock_ai):
        mock_ai.create_content.return_value = {
            'content': 'React, 상태관리, Zustand, 성능최적화',
            'usage': {'total_tokens': 50}
        }
        from services.web_research_service import extract_keywords
        keywords = extract_keywords(
            transcripts=['React 19의 새로운 기능에 대해 알아봅시다'],
            model='gemini/gemini-3-flash-preview'
        )
        self.assertIsInstance(keywords, list)
        self.assertTrue(len(keywords) > 0)


class TestSearchWeb(unittest.TestCase):

    @patch('services.web_research_service.DDGS')
    def test_search_web(self, mock_ddgs_cls):
        mock_instance = MagicMock()
        mock_instance.text.return_value = [
            {'title': 'Article 1', 'href': 'http://ex.com/1', 'body': 'desc 1'},
            {'title': 'Article 2', 'href': 'http://ex.com/2', 'body': 'desc 2'},
        ]
        mock_ddgs_cls.return_value.__enter__ = MagicMock(return_value=mock_instance)
        mock_ddgs_cls.return_value.__exit__ = MagicMock(return_value=False)

        from services.web_research_service import search_web
        results = search_web(['React 상태관리'])
        self.assertIsInstance(results, list)


class TestCrawlArticle(unittest.TestCase):

    @patch('services.web_research_service.trafilatura')
    def test_crawl_article_success(self, mock_traf):
        mock_traf.fetch_url.return_value = '<html>...</html>'
        mock_traf.extract.return_value = '기사 본문 내용입니다.'
        from services.web_research_service import crawl_article
        text = crawl_article('http://example.com/article')
        self.assertEqual(text, '기사 본문 내용입니다.')

    @patch('services.web_research_service.trafilatura')
    def test_crawl_article_failure(self, mock_traf):
        mock_traf.fetch_url.return_value = None
        from services.web_research_service import crawl_article
        text = crawl_article('http://example.com/blocked')
        self.assertIsNone(text)


class TestResearchTopic(unittest.TestCase):

    @patch('services.web_research_service.crawl_article')
    @patch('services.web_research_service.search_web')
    @patch('services.web_research_service.extract_keywords')
    @patch('services.web_research_service.ai_service')
    def test_research_topic_full_pipeline(self, mock_ai, mock_kw, mock_search, mock_crawl):
        mock_kw.return_value = ['React', '상태관리']
        mock_search.return_value = [
            {'title': 'Art1', 'url': 'http://ex.com/1'},
        ]
        mock_crawl.return_value = '기사 본문'
        mock_ai.create_content.return_value = {
            'content': '기사 요약 내용',
            'usage': {'total_tokens': 100}
        }
        from services.web_research_service import research_topic
        result = research_topic(
            transcripts=['자막 내용'],
            model='gemini/gemini-3-flash-preview'
        )
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)
        self.assertIn('title', result[0])
        self.assertIn('summary', result[0])
        self.assertIn('url', result[0])

    @patch('services.web_research_service.extract_keywords')
    def test_research_topic_no_keywords(self, mock_kw):
        mock_kw.return_value = []
        from services.web_research_service import research_topic
        result = research_topic(
            transcripts=['짧은 자막'],
            model='gemini/gemini-3-flash-preview'
        )
        self.assertEqual(result, [])


if __name__ == '__main__':
    unittest.main()
```

**Step 2: 테스트 실패 확인**

Run: `pytest tests/test_web_research_service.py -v`
Expected: FAIL (ModuleNotFoundError)

**Step 3: 서비스 구현**

Create: `services/web_research_service.py`

```python
"""웹 리서치 서비스 — 주제 키워드 검색 → 기사 크롤링 → AI 요약"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import trafilatura
from duckduckgo_search import DDGS

from services import ai_service

logger = logging.getLogger(__name__)

MAX_SEARCH_RESULTS = 5
MAX_ARTICLE_LENGTH = 5000  # 크롤링 본문 최대 글자수


def extract_keywords(transcripts, model):
    """자막들에서 핵심 검색 키워드 3~5개 추출

    Args:
        transcripts: 자막 텍스트 리스트
        model: LiteLLM 모델 ID

    Returns:
        list[str]: 키워드 리스트 (빈 리스트 가능)
    """
    combined = '\n---\n'.join(t[:2000] for t in transcripts)
    prompt = (
        '다음 자막들의 핵심 주제를 나타내는 검색 키워드를 3~5개 추출하세요.\n'
        '쉼표로 구분하여 키워드만 출력하세요. 다른 텍스트는 포함하지 마세요.\n\n'
        f'{combined}'
    )
    try:
        result = ai_service.create_content(
            content=prompt, model=model,
            style_prompt='키워드만 쉼표로 구분하여 출력하세요.',
            style_id='summary'
        )
        raw = result.get('content', '')
        keywords = [k.strip() for k in raw.split(',') if k.strip()]
        return keywords[:5]
    except Exception as e:
        logger.error('키워드 추출 실패: %s', e)
        return []


def search_web(keywords, max_results=MAX_SEARCH_RESULTS):
    """DuckDuckGo로 키워드 검색

    Args:
        keywords: 검색 키워드 리스트
        max_results: 최대 검색 결과 수

    Returns:
        list[dict]: [{'title': str, 'url': str}, ...]
    """
    query = ' '.join(keywords)
    try:
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results))
        return [
            {'title': r.get('title', ''), 'url': r.get('href', '')}
            for r in raw_results if r.get('href')
        ]
    except Exception as e:
        logger.error('웹 검색 실패: %s', e)
        return []


def crawl_article(url):
    """trafilatura로 기사 본문 추출

    Args:
        url: 기사 URL

    Returns:
        str 또는 None: 본문 텍스트
    """
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None
        text = trafilatura.extract(downloaded)
        if text:
            return text[:MAX_ARTICLE_LENGTH]
        return None
    except Exception as e:
        logger.warning('기사 크롤링 실패 (%s): %s', url, e)
        return None


def research_topic(transcripts, model, max_sources=MAX_SEARCH_RESULTS):
    """전체 웹 리서치 파이프라인: 키워드 추출 → 검색 → 크롤링 → 요약

    Args:
        transcripts: 자막 텍스트 리스트
        model: LiteLLM 모델 ID
        max_sources: 최대 외부 소스 수

    Returns:
        list[dict]: [{'title': str, 'summary': str, 'url': str}, ...]
    """
    # 1. 키워드 추출
    keywords = extract_keywords(transcripts, model)
    if not keywords:
        return []

    # 2. 웹 검색
    search_results = search_web(keywords, max_results=max_sources)
    if not search_results:
        return []

    # 3. 기사 크롤링 (병렬)
    articles = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_map = {
            executor.submit(crawl_article, sr['url']): sr
            for sr in search_results
        }
        for future in as_completed(future_map):
            sr = future_map[future]
            text = future.result()
            if text:
                articles.append({**sr, 'text': text})

    if not articles:
        return []

    # 4. 각 기사 AI 요약 (병렬)
    sources = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_map = {}
        for art in articles:
            prompt = (
                f'다음 기사를 200자 이내로 핵심만 요약하세요:\n\n{art["text"][:3000]}'
            )
            fut = executor.submit(
                ai_service.create_content,
                content=prompt, model=model,
                style_prompt='200자 이내 핵심 요약만 출력하세요.',
                style_id='summary'
            )
            future_map[fut] = art

        for future in as_completed(future_map):
            art = future_map[future]
            try:
                result = future.result()
                sources.append({
                    'title': art['title'],
                    'url': art['url'],
                    'summary': result.get('content', '')
                })
            except Exception as e:
                logger.warning('기사 요약 실패 (%s): %s', art['url'], e)

    return sources
```

**Step 4: 테스트 통과 확인**

Run: `pytest tests/test_web_research_service.py -v`
Expected: PASS (5 tests)

**Step 5: 커밋**

```bash
git add services/web_research_service.py tests/test_web_research_service.py
git commit -m "feat: 웹 리서치 서비스 (키워드 추출 → DuckDuckGo 검색 → 크롤링 → AI 요약)"
```

---

## Task 6: 퓨전 오케스트레이터 서비스

**Files:**
- Create: `services/fusion_service.py`
- Create: `tests/test_fusion_service.py`

**Step 1: 실패하는 테스트 작성**

Create: `tests/test_fusion_service.py`

```python
"""퓨전 오케스트레이터 서비스 테스트"""
import unittest
from unittest.mock import patch, MagicMock


class TestFusionService(unittest.TestCase):

    @patch('services.fusion_service.ai_service')
    @patch('services.fusion_service.comment_analyzer_service')
    @patch('services.fusion_service.web_research_service')
    @patch('services.fusion_service.content_service')
    def test_generate_fusion_full(self, mock_cs, mock_wr, mock_ca, mock_ai):
        # Phase 1: 소스 수집 mock
        mock_cs.get_video_id.return_value = 'vid1'
        mock_cs.get_transcript.return_value = {'text': '자막1', 'source': 'api'}
        mock_cs.get_top_comments.return_value = ['댓글1', '댓글2']

        # Phase 2: 분석 mock
        mock_ai.create_content.return_value = {
            'title': '퓨전 제목',
            'content': '# 퓨전 본문\n내용',
            'html': '<h1>퓨전 본문</h1>',
            'usage': {'prompt_tokens': 100, 'completion_tokens': 200, 'total_tokens': 300}
        }
        mock_ca.analyze_comments.return_value = {
            'insights': ['인사이트1'], 'questions': ['질문1'],
            'fact_checks': [], 'sentiments': ['감상1'],
            'usage': {'total_tokens': 50}
        }
        mock_wr.research_topic.return_value = [
            {'title': 'Art1', 'url': 'http://ex.com', 'summary': '요약1'}
        ]

        from services.fusion_service import generate_fusion
        result = generate_fusion(
            urls=['https://youtube.com/watch?v=vid1', 'https://youtube.com/watch?v=vid2'],
            style_id='blog_seo',
            model='gemini/gemini-3-flash-preview',
            modifiers={'length': 'long'},
            enable_web_research=True,
            enable_deep_comments=True
        )
        self.assertIn('title', result)
        self.assertIn('content', result)
        self.assertIn('fusion_meta', result)
        self.assertIn('videos_analyzed', result['fusion_meta'])

    @patch('services.fusion_service.ai_service')
    @patch('services.fusion_service.content_service')
    def test_generate_fusion_without_optional(self, mock_cs, mock_ai):
        mock_cs.get_video_id.return_value = 'vid1'
        mock_cs.get_transcript.return_value = {'text': '자막1', 'source': 'api'}
        mock_cs.get_top_comments.return_value = []
        mock_ai.create_content.return_value = {
            'title': '제목', 'content': '내용', 'html': '<p>내용</p>',
            'usage': {'prompt_tokens': 50, 'completion_tokens': 100, 'total_tokens': 150}
        }

        from services.fusion_service import generate_fusion
        result = generate_fusion(
            urls=['https://youtube.com/watch?v=vid1', 'https://youtube.com/watch?v=vid2'],
            style_id='blog_seo',
            model='gemini/gemini-3-flash-preview',
            modifiers={},
            enable_web_research=False,
            enable_deep_comments=False
        )
        self.assertIn('title', result)

    def test_generate_fusion_too_few_urls(self):
        from services.fusion_service import generate_fusion
        with self.assertRaises(ValueError):
            generate_fusion(
                urls=['https://youtube.com/watch?v=vid1'],
                style_id='blog_seo', model='m', modifiers={},
                enable_web_research=False, enable_deep_comments=False
            )


if __name__ == '__main__':
    unittest.main()
```

**Step 2: 테스트 실패 확인**

Run: `pytest tests/test_fusion_service.py -v`
Expected: FAIL

**Step 3: 서비스 구현**

Create: `services/fusion_service.py`

```python
"""퓨전 오케스트레이터 — 3단계 파이프라인으로 다중 소스 융합 콘텐츠 생성"""
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from services import ai_service, content_service
from services import comment_analyzer_service, web_research_service
from prompts import build_full_prompt
from prompts.fusion.fusion_prompt import FUSION_PROMPT, build_fusion_context

logger = logging.getLogger(__name__)

MAX_URLS = 5
MIN_URLS = 2
MAX_COMMENTS_PER_VIDEO = 50


def generate_fusion(urls, style_id, model, modifiers,
                    enable_web_research=True, enable_deep_comments=True):
    """퓨전 파이프라인 실행: Phase 1(수집) → Phase 2(분석) → Phase 3(생성)

    Args:
        urls: YouTube URL 리스트 (2~5개)
        style_id: 스타일 ID
        model: LiteLLM 모델 ID
        modifiers: {'length': str, 'writing_style': str}
        enable_web_research: 웹 리서치 활성화
        enable_deep_comments: 댓글 심층 분석 활성화

    Returns:
        dict: {title, content, html, sections, fusion_meta, usage}

    Raises:
        ValueError: URL이 2개 미만이거나 5개 초과 시
    """
    if len(urls) < MIN_URLS:
        raise ValueError(f'퓨전 분석은 최소 {MIN_URLS}개 URL이 필요합니다')
    if len(urls) > MAX_URLS:
        raise ValueError(f'퓨전 분석은 최대 {MAX_URLS}개 URL까지 가능합니다')

    start_time = time.time()
    total_tokens = 0
    total_comments = 0

    # ── Phase 1: 소스 수집 (병렬) ──
    transcripts = []
    all_comments = []
    failed_urls = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        # 자막 + 댓글 동시 수집
        transcript_futures = {}
        comment_futures = {}

        for url in urls:
            vid = content_service.get_video_id(url)
            if not vid:
                failed_urls.append(url)
                continue
            transcript_futures[executor.submit(
                content_service.get_transcript, vid
            )] = (vid, url)
            comment_futures[executor.submit(
                content_service.get_top_comments, vid, MAX_COMMENTS_PER_VIDEO
            )] = vid

        for future in as_completed(transcript_futures):
            vid, url = transcript_futures[future]
            try:
                result = future.result()
                if result and result.get('text'):
                    transcripts.append({'video_id': vid, 'url': url, 'text': result['text']})
                else:
                    failed_urls.append(url)
            except Exception as e:
                logger.warning('자막 추출 실패 (%s): %s', url, e)
                failed_urls.append(url)

        for future in as_completed(comment_futures):
            try:
                comments = future.result()
                if comments:
                    all_comments.extend(comments)
                    total_comments += len(comments)
            except Exception:
                pass

    if not transcripts:
        raise ValueError('모든 영상의 자막 추출에 실패했습니다')

    # ── Phase 2: 분석 & 압축 (병렬) ──
    video_summaries = []
    comment_analysis = None
    web_sources = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}

        # 2a. 영상별 요약
        for t in transcripts:
            fut = executor.submit(
                _summarize_transcript, t['text'], t['video_id'], model
            )
            futures[fut] = ('summary', t)

        # 2b. 댓글 심층 분석
        if enable_deep_comments and all_comments:
            fut = executor.submit(
                comment_analyzer_service.analyze_comments, all_comments, model
            )
            futures[fut] = ('comments', None)

        # 2c. 웹 리서치
        if enable_web_research:
            transcript_texts = [t['text'] for t in transcripts]
            fut = executor.submit(
                web_research_service.research_topic, transcript_texts, model
            )
            futures[fut] = ('web', None)

        for future in as_completed(futures):
            task_type, meta = futures[future]
            try:
                result = future.result()
                if task_type == 'summary' and result:
                    video_summaries.append({
                        'title': result.get('title', meta['video_id']),
                        'summary': result.get('content', ''),
                        'url': meta['url']
                    })
                    total_tokens += result.get('usage', {}).get('total_tokens', 0)
                elif task_type == 'comments' and result:
                    comment_analysis = result
                    total_tokens += result.get('usage', {}).get('total_tokens', 0)
                elif task_type == 'web' and result:
                    web_sources = result
            except Exception as e:
                logger.warning('Phase 2 작업 실패 (%s): %s', task_type, e)

    # ── Phase 3: 융합 & 생성 ──
    style_prompt = build_full_prompt(style_id, modifiers)
    fusion_context = build_fusion_context(video_summaries, comment_analysis, web_sources)
    combined_prompt = f'{FUSION_PROMPT}\n\n{style_prompt}'

    final_result = ai_service.create_content(
        content=fusion_context,
        model=model,
        style_prompt=combined_prompt,
        modifiers=modifiers,
        style_id=style_id
    )
    total_tokens += final_result.get('usage', {}).get('total_tokens', 0)

    # 응답 조합
    sections = {
        'faq': '',
        'fact_checks': [],
        'sources_used': []
    }

    if comment_analysis:
        if comment_analysis.get('fact_checks'):
            sections['fact_checks'] = comment_analysis['fact_checks']

    for t in transcripts:
        sections['sources_used'].append({
            'type': 'youtube', 'title': t['video_id'], 'url': t['url']
        })
    for ws in web_sources:
        sections['sources_used'].append({
            'type': 'web', 'title': ws['title'], 'url': ws['url']
        })

    processing_time = round(time.time() - start_time, 1)

    return {
        'title': final_result.get('title', ''),
        'content': final_result.get('content', ''),
        'html': final_result.get('html', ''),
        'sections': sections,
        'fusion_meta': {
            'videos_analyzed': len(transcripts),
            'comments_analyzed': total_comments,
            'web_sources_found': len(web_sources),
            'total_tokens': total_tokens,
            'processing_time': processing_time,
            'failed_urls': failed_urls
        },
        'usage': final_result.get('usage', {})
    }


def _summarize_transcript(text, video_id, model):
    """개별 영상 자막을 구조화된 요약으로 변환"""
    prompt = (
        '다음 YouTube 영상 자막을 500자 이내로 구조화하여 요약하세요.\n'
        '핵심 주장, 근거, 결론을 구분하여 정리하세요.\n'
        '제목도 한 줄로 작성하세요.\n\n'
        f'{text[:8000]}'
    )
    return ai_service.create_content(
        content=prompt, model=model,
        style_prompt='구조화된 요약. 제목 + 핵심 주장 + 근거 + 결론.',
        style_id='summary'
    )
```

**Step 4: 테스트 통과 확인**

Run: `pytest tests/test_fusion_service.py -v`
Expected: PASS (3 tests)

**Step 5: 커밋**

```bash
git add services/fusion_service.py tests/test_fusion_service.py
git commit -m "feat: 퓨전 오케스트레이터 서비스 (3단계 파이프라인)"
```

---

## Task 7: 퓨전 API 라우트

**Files:**
- Modify: `routes/blog_routes.py`
- Modify: `tests/test_routes_smoke.py`

**Step 1: 실패하는 테스트 작성**

`tests/test_routes_smoke.py`에 추가:

```python
@patch('services.supabase_service.is_supabase_enabled', return_value=False)
def test_generate_fusion_smoke(self, mock_enabled):
    """퓨전 생성 엔드포인트 스모크 테스트"""
    fake_result = {
        'title': '퓨전 제목',
        'content': '퓨전 본문',
        'html': '<p>퓨전 본문</p>',
        'sections': {
            'faq': '', 'fact_checks': [],
            'sources_used': [{'type': 'youtube', 'title': 'v1', 'url': 'http://y.com'}]
        },
        'fusion_meta': {
            'videos_analyzed': 2, 'comments_analyzed': 10,
            'web_sources_found': 1, 'total_tokens': 500,
            'processing_time': 5.0, 'failed_urls': []
        },
        'usage': {'total_tokens': 500}
    }
    with patch('routes.blog_routes.fusion_service.generate_fusion', return_value=fake_result):
        res = self.client.post('/api/generate-fusion', json={
            'urls': ['https://youtube.com/watch?v=a', 'https://youtube.com/watch?v=b'],
            'style': 'blog_seo',
            'model': 'gemini/gemini-3-flash-preview',
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('fusion_meta', data)
        self.assertEqual(data['fusion_meta']['videos_analyzed'], 2)

@patch('services.supabase_service.is_supabase_enabled', return_value=False)
def test_generate_fusion_too_few_urls(self, mock_enabled):
    """퓨전: URL 1개면 에러"""
    res = self.client.post('/api/generate-fusion', json={
        'urls': ['https://youtube.com/watch?v=a'],
        'style': 'blog_seo',
        'model': 'gemini/gemini-3-flash-preview',
    })
    self.assertEqual(res.status_code, 400)
```

**Step 2: 테스트 실패 확인**

Run: `pytest tests/test_routes_smoke.py::TestRoutesSmoke::test_generate_fusion_smoke -v`
Expected: FAIL (404)

**Step 3: 라우트 구현**

`routes/blog_routes.py` 상단 import에 추가:

```python
from services import fusion_service
```

`routes/blog_routes.py`에 새 라우트 추가 (기존 라우트들 아래에):

```python
@blog_bp.route('/api/generate-fusion', methods=['POST'])
@check_usage
def generate_fusion():
    """퓨전 생성: N개 URL → 융합 1편"""
    data = request.get_json()
    urls = data.get('urls', [])
    style_id = data.get('style', 'blog_seo')
    model = data.get('model', '')
    modifiers = data.get('modifiers', {})
    enable_web_research = data.get('enable_web_research', True)
    enable_deep_comments = data.get('enable_deep_comments', True)

    if not urls or len(urls) < 2:
        return jsonify({'error': '[입력 오류] 퓨전 분석은 최소 2개 URL이 필요합니다'}), 400
    if len(urls) > 5:
        return jsonify({'error': '[입력 오류] 퓨전 분석은 최대 5개 URL까지 가능합니다'}), 400
    if not model:
        return jsonify({'error': '[입력 오류] 모델을 선택해주세요'}), 400

    try:
        result = fusion_service.generate_fusion(
            urls=urls,
            style_id=style_id,
            model=model,
            modifiers=modifiers,
            enable_web_research=enable_web_research,
            enable_deep_comments=enable_deep_comments
        )

        # 사용량 차감 (1회)
        if hasattr(g, 'usage') and g.usage:
            from services.usage import UsageService
            UsageService.decrement(g.usage.get('user_id'))

        return jsonify(result)

    except ValueError as e:
        return jsonify({'error': f'[입력 오류] {str(e)}'}), 400
    except Exception as e:
        logger.error('퓨전 생성 실패: %s', e, exc_info=True)
        return jsonify({'error': f'[생성 실패] {str(e)}'}), 500
```

**Step 4: 테스트 통과 확인**

Run: `pytest tests/test_routes_smoke.py::TestRoutesSmoke::test_generate_fusion_smoke tests/test_routes_smoke.py::TestRoutesSmoke::test_generate_fusion_too_few_urls -v`
Expected: PASS (2 tests)

**Step 5: 기존 테스트 깨지지 않음 확인**

Run: `pytest tests/test_routes_smoke.py -v`
Expected: 모든 테스트 PASS

**Step 6: 커밋**

```bash
git add routes/blog_routes.py tests/test_routes_smoke.py
git commit -m "feat: POST /api/generate-fusion 엔드포인트 추가"
```

---

## Task 8: 프론트엔드 API 함수

**Files:**
- Modify: `frontend/lib/api.ts`

**Step 1: api.ts에 generateFusion 함수 추가**

```typescript
export interface FusionRequest {
  urls: string[];
  style: string;
  model: string;
  modifiers?: Modifiers;
  enable_web_research?: boolean;
  enable_deep_comments?: boolean;
}

export interface FusionMeta {
  videos_analyzed: number;
  comments_analyzed: number;
  web_sources_found: number;
  total_tokens: number;
  processing_time: number;
  failed_urls: string[];
}

export interface FusionResponse {
  title: string;
  content: string;
  html: string;
  sections: {
    faq: string;
    fact_checks: string[];
    sources_used: Array<{ type: string; title: string; url: string }>;
  };
  fusion_meta: FusionMeta;
  usage: { prompt_tokens: number; completion_tokens: number; total_tokens: number };
}

export async function generateFusion(req: FusionRequest): Promise<FusionResponse> {
  return request('/api/generate-fusion', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}
```

**Step 2: 커밋**

```bash
git add frontend/lib/api.ts
git commit -m "feat: generateFusion API 함수 + 타입 정의 추가"
```

---

## Task 9: settingsStore에 퓨전 모드 상태 추가

**Files:**
- Modify: `frontend/stores/settingsStore.ts`

**Step 1: settingsStore에 퓨전 관련 상태 추가**

기존 상태에 추가:

```typescript
// 기존 타입에 추가
type GenerationMode = 'individual' | 'combined' | 'fusion';

// store에 추가할 상태
generationMode: GenerationMode;
enableWebResearch: boolean;
enableDeepComments: boolean;

// store에 추가할 액션
setGenerationMode: (mode: GenerationMode) => void;
setEnableWebResearch: (v: boolean) => void;
setEnableDeepComments: (v: boolean) => void;
```

초기값:
```typescript
generationMode: 'individual',
enableWebResearch: true,
enableDeepComments: true,
```

액션:
```typescript
setGenerationMode: (mode) => set({ generationMode: mode }),
setEnableWebResearch: (v) => set({ enableWebResearch: v }),
setEnableDeepComments: (v) => set({ enableDeepComments: v }),
```

**Step 2: 커밋**

```bash
git add frontend/stores/settingsStore.ts
git commit -m "feat: settingsStore에 퓨전 모드 상태 추가 (generationMode, webResearch, deepComments)"
```

---

## Task 10: useGenerate 훅에 퓨전 생성 로직 추가

**Files:**
- Modify: `frontend/hooks/useGenerate.ts`

**Step 1: generateFusion 함수를 useGenerate 훅에 추가**

기존 `generateBatchUrls` 옆에 `generateFusionUrls` 추가:

```typescript
import { generateFusion as apiFusion, FusionResponse } from '@/lib/api';

const generateFusionUrls = useCallback(
  async (urls: string[]) => {
    if (urls.length < 2) {
      setState(s => ({ ...s, error: '퓨전 분석은 최소 2개 URL이 필요합니다' }));
      return;
    }
    setState(s => ({ ...s, isLoading: true, error: null }));

    try {
      const { enableWebResearch, enableDeepComments } = useSettingsStore.getState();
      const result: FusionResponse = await apiFusion({
        urls,
        style: selectedStyle,
        model: selectedModel,
        modifiers,
        enable_web_research: enableWebResearch,
        enable_deep_comments: enableDeepComments,
      });

      addReport({
        id: crypto.randomUUID(),
        title: result.title,
        content: result.content,
        html: result.html,
        style: selectedStyle,
        model: selectedModel,
        createdAt: new Date().toISOString(),
        isFusion: true,
        fusionMeta: result.fusion_meta,
        sections: result.sections,
        usage: result.usage,
      });

      setState(s => ({ ...s, isLoading: false }));
    } catch (err: any) {
      setState(s => ({ ...s, isLoading: false, error: err.message }));
    }
  },
  [selectedModel, selectedStyle, modifiers, addReport]
);

// return에 추가
return { state, generateSingle, generateBatchUrls, generateFusionUrls, ... };
```

**Step 2: 커밋**

```bash
git add frontend/hooks/useGenerate.ts
git commit -m "feat: useGenerate 훅에 generateFusionUrls 추가"
```

---

## Task 11: 퓨전 분석 탭 UI 컴포넌트

**Files:**
- Create: `frontend/components/input/GenerationModeSelector.tsx`
- Create: `frontend/components/input/FusionOptions.tsx`

**Step 1: 생성 모드 선택 컴포넌트**

Create: `frontend/components/input/GenerationModeSelector.tsx`

```tsx
'use client';

import { useSettingsStore } from '@/stores/settingsStore';

const modes = [
  { key: 'individual' as const, label: '개별 분석' },
  { key: 'combined' as const, label: '합쳐서 분석' },
  { key: 'fusion' as const, label: '퓨전 분석' },
];

export default function GenerationModeSelector() {
  const { generationMode, setGenerationMode } = useSettingsStore();

  return (
    <div className="flex gap-1 rounded-lg bg-[var(--surface-secondary)] p-1">
      {modes.map((m) => (
        <button
          key={m.key}
          onClick={() => setGenerationMode(m.key)}
          className={`flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
            generationMode === m.key
              ? 'bg-[var(--accent-primary)] text-white'
              : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
          }`}
        >
          {m.label}
        </button>
      ))}
    </div>
  );
}
```

Create: `frontend/components/input/FusionOptions.tsx`

```tsx
'use client';

import { useSettingsStore } from '@/stores/settingsStore';

export default function FusionOptions() {
  const {
    generationMode,
    enableWebResearch, setEnableWebResearch,
    enableDeepComments, setEnableDeepComments,
  } = useSettingsStore();

  if (generationMode !== 'fusion') return null;

  return (
    <div className="mt-2 space-y-2 rounded-lg border border-[var(--border-primary)] p-3">
      <p className="text-xs font-medium text-[var(--text-secondary)]">퓨전 옵션</p>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={enableWebResearch}
          onChange={(e) => setEnableWebResearch(e.target.checked)}
          className="rounded"
        />
        <span>웹 리서치 (관련 기사 자동 검색)</span>
      </label>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={enableDeepComments}
          onChange={(e) => setEnableDeepComments(e.target.checked)}
          className="rounded"
        />
        <span>댓글 심층 분석 (FAQ, 팩트체크 포함)</span>
      </label>
      <p className="text-xs text-[var(--text-tertiary)]">
        퓨전 분석은 2~5개 URL이 필요합니다
      </p>
    </div>
  );
}
```

**Step 2: 기존 입력 영역에 통합**

기존 URL 입력 영역 컴포넌트(확인 필요)에 `GenerationModeSelector`와 `FusionOptions`를 추가한다.

**Step 3: 커밋**

```bash
git add frontend/components/input/GenerationModeSelector.tsx frontend/components/input/FusionOptions.tsx
git commit -m "feat: 퓨전 분석 탭 UI (GenerationModeSelector + FusionOptions)"
```

---

## Task 12: 퓨전 결과 카드 확장

**Files:**
- Create: `frontend/components/result/FusionSections.tsx`

**Step 1: FAQ + 소스 + 팩트체크 표시 컴포넌트**

Create: `frontend/components/result/FusionSections.tsx`

```tsx
'use client';

import { useState } from 'react';

interface FusionSectionsProps {
  sections?: {
    faq: string;
    fact_checks: string[];
    sources_used: Array<{ type: string; title: string; url: string }>;
  };
  fusionMeta?: {
    videos_analyzed: number;
    comments_analyzed: number;
    web_sources_found: number;
    processing_time: number;
  };
}

export default function FusionSections({ sections, fusionMeta }: FusionSectionsProps) {
  const [faqOpen, setFaqOpen] = useState(false);
  const [sourcesOpen, setSourcesOpen] = useState(false);

  if (!sections) return null;

  return (
    <div className="mt-4 space-y-3">
      {/* 퓨전 메타 칩 */}
      {fusionMeta && (
        <div className="flex flex-wrap gap-2 text-xs">
          <span className="rounded-full bg-blue-500/10 px-2 py-0.5 text-blue-400">
            영상 {fusionMeta.videos_analyzed}개
          </span>
          {fusionMeta.comments_analyzed > 0 && (
            <span className="rounded-full bg-green-500/10 px-2 py-0.5 text-green-400">
              댓글 {fusionMeta.comments_analyzed}개
            </span>
          )}
          {fusionMeta.web_sources_found > 0 && (
            <span className="rounded-full bg-purple-500/10 px-2 py-0.5 text-purple-400">
              외부소스 {fusionMeta.web_sources_found}개
            </span>
          )}
        </div>
      )}

      {/* 팩트체크 */}
      {sections.fact_checks.length > 0 && (
        <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/5 p-3">
          <p className="mb-2 text-sm font-medium text-yellow-400">팩트체크</p>
          <ul className="space-y-1 text-sm">
            {sections.fact_checks.map((fc, i) => (
              <li key={i} className="text-[var(--text-secondary)]">⚠️ {fc}</li>
            ))}
          </ul>
        </div>
      )}

      {/* FAQ 섹션 (접기/펼치기) */}
      {sections.faq && (
        <div className="rounded-lg border border-[var(--border-primary)]">
          <button
            onClick={() => setFaqOpen(!faqOpen)}
            className="flex w-full items-center justify-between p-3 text-sm font-medium"
          >
            <span>자주 묻는 질문 (FAQ)</span>
            <span>{faqOpen ? '▲' : '▼'}</span>
          </button>
          {faqOpen && (
            <div className="border-t border-[var(--border-primary)] p-3 text-sm"
                 dangerouslySetInnerHTML={{ __html: sections.faq }} />
          )}
        </div>
      )}

      {/* 참고 소스 (접기/펼치기) */}
      {sections.sources_used.length > 0 && (
        <div className="rounded-lg border border-[var(--border-primary)]">
          <button
            onClick={() => setSourcesOpen(!sourcesOpen)}
            className="flex w-full items-center justify-between p-3 text-sm font-medium"
          >
            <span>참고 소스 ({sections.sources_used.length}개)</span>
            <span>{sourcesOpen ? '▲' : '▼'}</span>
          </button>
          {sourcesOpen && (
            <div className="border-t border-[var(--border-primary)] p-3">
              <ul className="space-y-1 text-sm">
                {sections.sources_used.map((s, i) => (
                  <li key={i}>
                    <span className="mr-1 text-xs text-[var(--text-tertiary)]">
                      {s.type === 'youtube' ? '🎬' : '📰'}
                    </span>
                    <a href={s.url} target="_blank" rel="noopener noreferrer"
                       className="text-[var(--accent-primary)] hover:underline">
                      {s.title}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

**Step 2: 기존 결과 카드 컴포넌트에 FusionSections 통합**

기존 ReportCard 컴포넌트에서 `report.isFusion`일 때 `<FusionSections>` 렌더링 추가.

**Step 3: 커밋**

```bash
git add frontend/components/result/FusionSections.tsx
git commit -m "feat: 퓨전 결과 카드 확장 (FAQ, 팩트체크, 참고 소스 섹션)"
```

---

## Task 13: 퓨전 진행 상태 표시

**Files:**
- Create: `frontend/components/result/FusionProgress.tsx`

**Step 1: 진행 상태 컴포넌트**

Create: `frontend/components/result/FusionProgress.tsx`

```tsx
'use client';

interface FusionProgressProps {
  isLoading: boolean;
  isFusion: boolean;
}

const steps = [
  { label: '자막 수집 중...', duration: 5000 },
  { label: '댓글 분석 중...', duration: 8000 },
  { label: '웹 리서치 중...', duration: 10000 },
  { label: '최종 글 생성 중...', duration: 15000 },
];

export default function FusionProgress({ isLoading, isFusion }: FusionProgressProps) {
  if (!isLoading || !isFusion) return null;

  // 간단한 시간 기반 단계 표시 (실제 SSE 연동은 추후)
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    if (!isLoading) { setCurrentStep(0); return; }
    const timers = steps.map((_, i) =>
      setTimeout(() => setCurrentStep(i), steps.slice(0, i).reduce((a, s) => a + s.duration, 0))
    );
    return () => timers.forEach(clearTimeout);
  }, [isLoading]);

  return (
    <div className="my-4 rounded-lg border border-[var(--border-primary)] p-4">
      <p className="mb-3 text-sm font-medium">퓨전 분석 진행 중...</p>
      <div className="space-y-2">
        {steps.map((step, i) => (
          <div key={i} className="flex items-center gap-2 text-sm">
            <span className={i <= currentStep ? 'text-green-400' : 'text-[var(--text-tertiary)]'}>
              {i < currentStep ? '✓' : i === currentStep ? '●' : '○'}
            </span>
            <span className={i <= currentStep ? 'text-[var(--text-primary)]' : 'text-[var(--text-tertiary)]'}>
              {step.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

**Step 2: 커밋**

```bash
git add frontend/components/result/FusionProgress.tsx
git commit -m "feat: 퓨전 진행 상태 표시 컴포넌트"
```

---

## Task 14: 통합 테스트 & 최종 검증

**Step 1: 전체 백엔드 테스트 실행**

Run: `pytest tests/ -v --ignore=tests/test_ui_comprehensive.py --ignore=tests/e2e`
Expected: 모든 테스트 PASS

**Step 2: 프론트엔드 빌드 확인**

Run: `cd frontend && npm run build`
Expected: 빌드 성공 (에러 없음)

**Step 3: 수동 통합 테스트**

1. `python app.py` 실행
2. 프론트엔드에서 "퓨전 분석" 탭 선택
3. YouTube URL 2개 입력
4. "웹 리서치" + "댓글 심층 분석" 옵션 확인
5. 생성 실행 → 결과 카드에 FAQ, 팩트체크, 참고 소스 확인

**Step 4: 최종 커밋**

```bash
git add -A
git commit -m "feat: 콘텐츠 퓨전 엔진 통합 완료"
```

---

## 구현 순서 요약

| Task | 내용 | 의존성 |
|------|------|--------|
| 1 | 의존성 추가 | 없음 |
| 2 | 댓글 분석 프롬프트 | 없음 |
| 3 | 퓨전 통합 프롬프트 | Task 2 |
| 4 | 댓글 분석 서비스 | Task 2 |
| 5 | 웹 리서치 서비스 | Task 1 |
| 6 | 퓨전 오케스트레이터 | Task 3, 4, 5 |
| 7 | API 라우트 | Task 6 |
| 8 | 프론트 API 함수 | Task 7 |
| 9 | settingsStore 확장 | 없음 |
| 10 | useGenerate 훅 확장 | Task 8, 9 |
| 11 | 퓨전 탭 UI | Task 9 |
| 12 | 결과 카드 확장 | Task 10 |
| 13 | 진행 상태 표시 | Task 10 |
| 14 | 통합 테스트 | Task 1~13 |

**병렬 가능:** Task 1+2+9 동시, Task 4+5 동시, Task 11+12+13 동시
