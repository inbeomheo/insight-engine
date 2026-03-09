"""품질 심사-재작성 루프 서비스 — 규칙 기반 평가 + 자동 재작성"""
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class QualityCriteria:
    """품질 평가 기준 (필드명: 최소 점수 0-100)"""
    readability: int = 70
    seo_score: int = 60
    paragraph_count: int = 50
    keyword_density: int = 50


@dataclass
class RewriteIteration:
    """재작성 반복 1회 기록"""
    iteration: int
    scores: dict  # {field: score}
    total_score: int
    passed: bool
    content_snapshot: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class QualityResult:
    """품질 루프 최종 결과"""
    result_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    final_content: str = ""
    best_score: int = 0
    iterations_run: int = 0
    passed: bool = False
    iterations: list = field(default_factory=list)  # List[RewriteIteration]
    criteria_used: dict = field(default_factory=dict)


# ── 규칙 기반 평가 함수들 ──


def _score_readability(content: str) -> int:
    """가독성 점수: 평균 문장 길이 기반 (짧을수록 높음)"""
    sentences = [s.strip() for s in re.split(r'[.!?。\n]', content) if s.strip()]
    if not sentences:
        return 0
    avg_len = sum(len(s) for s in sentences) / len(sentences)
    # 평균 30자 이하 → 100점, 80자 이상 → 0점
    if avg_len <= 30:
        return 100
    if avg_len >= 80:
        return 0
    return max(0, int(100 - (avg_len - 30) * 2))


def _score_seo(content: str) -> int:
    """SEO 점수: 제목(#) 수 + 리스트(- /*) 수 + 링크 수 기반"""
    headings = len(re.findall(r'^#{1,3}\s', content, re.MULTILINE))
    lists = len(re.findall(r'^[\-\*]\s', content, re.MULTILINE))
    links = len(re.findall(r'\[.+?\]\(.+?\)', content))
    # 각 요소당 15점, 최대 100점
    raw = headings * 15 + lists * 10 + links * 10
    return min(100, raw)


def _score_paragraph_count(content: str) -> int:
    """문단 수 점수: 빈 줄로 구분된 문단 개수 기반"""
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', content) if p.strip()]
    count = len(paragraphs)
    # 3개 이상 100점, 1개 이하 0점
    if count >= 3:
        return 100
    if count == 2:
        return 60
    if count == 1:
        return 30
    return 0


def _score_keyword_density(content: str) -> int:
    """키워드 밀도 점수: 고유 단어 비율 기반 (다양할수록 높음)"""
    words = re.findall(r'\w+', content.lower())
    if not words:
        return 0
    unique_ratio = len(set(words)) / len(words)
    # 비율 0.5 이상 → 100점, 0.2 이하 → 0점
    if unique_ratio >= 0.5:
        return 100
    if unique_ratio <= 0.2:
        return 0
    return int((unique_ratio - 0.2) / 0.3 * 100)


_SCORE_FUNCTIONS = {
    'readability': _score_readability,
    'seo_score': _score_seo,
    'paragraph_count': _score_paragraph_count,
    'keyword_density': _score_keyword_density,
}


def evaluate_content(content: str, criteria: dict) -> dict:
    """콘텐츠를 기준별로 평가하여 점수 dict 반환.

    Args:
        content: 평가할 텍스트
        criteria: {필드명: 최소점수} — 필드명은 _SCORE_FUNCTIONS 키와 매칭

    Returns:
        {필드명: 실제 점수}
    """
    scores = {}
    for field_name in criteria:
        scorer = _SCORE_FUNCTIONS.get(field_name)
        if scorer:
            scores[field_name] = scorer(content)
        else:
            scores[field_name] = 0
    return scores


def _check_passed(scores: dict, criteria: dict) -> bool:
    """모든 기준을 충족하는지 확인"""
    return all(scores.get(k, 0) >= v for k, v in criteria.items())


# ── 규칙 기반 재작성 변환 ──


def _rewrite_content(content: str, scores: dict, criteria: dict) -> str:
    """점수가 낮은 항목에 대해 규칙 기반 텍스트 변환 적용"""
    result = content

    # 가독성 점수 미달 → 긴 문장 분리
    if scores.get('readability', 100) < criteria.get('readability', 0):
        result = _split_long_sentences(result)

    # SEO 점수 미달 → 마크다운 구조 보강
    if scores.get('seo_score', 100) < criteria.get('seo_score', 0):
        result = _add_structure(result)

    # 문단 수 점수 미달 → 문단 분리
    if scores.get('paragraph_count', 100) < criteria.get('paragraph_count', 0):
        result = _split_paragraphs(result)

    # 키워드 밀도 점수 미달 → 반복 단어 제거 (연속 중복)
    if scores.get('keyword_density', 100) < criteria.get('keyword_density', 0):
        result = _reduce_repetition(result)

    return result


def _split_long_sentences(content: str) -> str:
    """70자 이상 문장을 쉼표/접속사 기준으로 분리"""
    lines = content.split('\n')
    new_lines = []
    for line in lines:
        if len(line) > 70 and not line.startswith('#'):
            # 쉼표나 접속사 위치에서 분리
            parts = re.split(r'(,\s|;\s|그리고\s|또한\s|그러나\s)', line)
            if len(parts) > 1:
                merged = []
                current = ""
                for part in parts:
                    current += part
                    if len(current) > 30 and re.match(r'.*[,;]\s$', current):
                        merged.append(current.rstrip(', ;'))
                        current = ""
                if current.strip():
                    merged.append(current.strip())
                new_lines.append('. '.join(p.strip() for p in merged if p.strip()))
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    return '\n'.join(new_lines)


def _add_structure(content: str) -> str:
    """마크다운 제목이 없으면 첫 줄을 ## 제목으로 변환"""
    if not re.search(r'^#{1,3}\s', content, re.MULTILINE):
        lines = content.split('\n')
        if lines and lines[0].strip():
            lines[0] = f"## {lines[0].strip()}"
        return '\n'.join(lines)
    return content


def _split_paragraphs(content: str) -> str:
    """200자 이상인 단일 문단을 문장 단위로 분리하여 문단화"""
    paragraphs = content.split('\n\n')
    new_paragraphs = []
    for para in paragraphs:
        if len(para) > 200 and not para.startswith('#'):
            sentences = re.split(r'(?<=[.!?。])\s+', para)
            mid = len(sentences) // 2
            if mid > 0:
                new_paragraphs.append(' '.join(sentences[:mid]))
                new_paragraphs.append(' '.join(sentences[mid:]))
            else:
                new_paragraphs.append(para)
        else:
            new_paragraphs.append(para)
    return '\n\n'.join(new_paragraphs)


def _reduce_repetition(content: str) -> str:
    """연속 중복 단어 제거"""
    return re.sub(r'\b(\w+)(\s+\1)+\b', r'\1', content)


# ── 메인 루프 ──


def run_quality_loop(content: str, criteria: dict, max_iterations: int = 3) -> QualityResult:
    """생성→평가→재작성 루프 실행.

    Args:
        content: 원본 콘텐츠
        criteria: {필드명: 최소점수} (예: {"readability": 70, "seo_score": 60})
        max_iterations: 최대 반복 횟수 (1-10)

    Returns:
        QualityResult — 최종 결과 + 반복 이력

    Raises:
        ValueError: content가 비어있거나, criteria가 비어있거나, max_iterations 범위 초과
    """
    if not content or not content.strip():
        raise ValueError("content는 비어있을 수 없습니다")
    if not criteria:
        raise ValueError("criteria는 비어있을 수 없습니다")
    if not isinstance(max_iterations, int) or max_iterations < 1 or max_iterations > 10:
        raise ValueError("max_iterations는 1~10 사이여야 합니다")

    result = QualityResult(criteria_used=dict(criteria))
    current_content = content
    best_content = content
    best_score = 0

    for i in range(1, max_iterations + 1):
        # 평가
        scores = evaluate_content(current_content, criteria)
        total = sum(scores.values()) // max(len(scores), 1)
        passed = _check_passed(scores, criteria)

        iteration = RewriteIteration(
            iteration=i,
            scores=dict(scores),
            total_score=total,
            passed=passed,
            content_snapshot=current_content[:200],
        )
        result.iterations.append(iteration)

        # 최고 점수 갱신
        if total > best_score:
            best_score = total
            best_content = current_content

        # 통과하면 즉시 종료
        if passed:
            result.final_content = current_content
            result.best_score = total
            result.iterations_run = i
            result.passed = True
            return result

        # 마지막 반복이면 재작성 없이 종료
        if i == max_iterations:
            break

        # 재작성
        current_content = _rewrite_content(current_content, scores, criteria)

    # 최대 반복 도달 — 최고 점수 버전 반환
    result.final_content = best_content
    result.best_score = best_score
    result.iterations_run = len(result.iterations)
    result.passed = False
    return result
