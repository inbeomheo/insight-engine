"""
ALT 텍스트 워크벤치 서비스

이미지 파일명/캡션/페이지 문맥을 기반으로 대체 텍스트를 생성하고
품질을 검증합니다. 규칙 기반 (AI API 호출 없음).
"""
import os
import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AltText:
    """생성된 ALT 텍스트 결과."""
    image_id: str
    alt_text: str
    language: str = 'ko'
    quality_score: float = 0.0
    issues: List[str] = field(default_factory=list)


# 파일명에서 제거할 패턴 (확장자, 숫자 ID, 구분자)
_EXTENSION_PATTERN = re.compile(r'\.[a-zA-Z]{2,4}$')
_SEPARATOR_PATTERN = re.compile(r'[-_]+')
_NOISE_PATTERN = re.compile(r'\b(?:img|image|photo|pic|screenshot|untitled|dsc|dcim)\b', re.IGNORECASE)
_NUMBER_ONLY_PATTERN = re.compile(r'^\d+$')

# ALT 텍스트 품질 검증 규칙
_MIN_LENGTH = 10
_MAX_LENGTH = 125
_BAD_PREFIXES = ('이미지', '사진', '그림', 'image of', 'picture of', 'photo of')

# 파일명 키워드 → 설명 매핑
_KEYWORD_MAP = {
    'chart': '차트',
    'graph': '그래프',
    'diagram': '다이어그램',
    'logo': '로고',
    'icon': '아이콘',
    'banner': '배너',
    'header': '헤더',
    'footer': '푸터',
    'profile': '프로필',
    'avatar': '아바타',
    'thumbnail': '썸네일',
    'map': '지도',
    'table': '표',
    'flow': '흐름도',
    'architecture': '아키텍처',
    'screenshot': '화면 캡처',
    'cover': '표지',
    'infographic': '인포그래픽',
    'background': '배경',
    'button': '버튼',
}


def _extract_keywords_from_filename(filename: str) -> List[str]:
    """파일명에서 의미 있는 키워드를 추출합니다."""
    # 확장자 제거
    name = _EXTENSION_PATTERN.sub('', filename)
    # 구분자를 공백으로 변환
    name = _SEPARATOR_PATTERN.sub(' ', name)
    # 노이즈 단어 제거
    name = _NOISE_PATTERN.sub('', name)
    # 공백 정리
    tokens = name.split()
    # 순수 숫자 토큰 제거
    keywords = [t for t in tokens if t.strip() and not _NUMBER_ONLY_PATTERN.match(t)]
    return keywords


def _find_relevant_context(page_context: str, keywords: List[str]) -> Optional[str]:
    """페이지 문맥에서 키워드와 관련된 문장을 찾습니다."""
    if not page_context or not keywords:
        return None

    sentences = re.split(r'[.!?。]\s*', page_context)
    best_sentence = None
    best_score = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 5:
            continue
        score = sum(1 for kw in keywords if kw.lower() in sentence.lower())
        if score > best_score:
            best_score = score
            best_sentence = sentence

    if best_score > 0 and best_sentence:
        # 너무 긴 문장은 잘라냄
        if len(best_sentence) > 100:
            best_sentence = best_sentence[:100].rsplit(' ', 1)[0] + '...'
        return best_sentence
    return None


def _build_alt_text(image: dict, page_context: str = '') -> str:
    """이미지 정보와 문맥을 조합해 ALT 텍스트를 생성합니다."""
    caption = image.get('caption', '').strip()
    filename = image.get('filename', '').strip()

    # 캡션이 있으면 우선 사용
    if caption:
        alt = caption
        # 캡션이 너무 짧으면 파일명 키워드 보충
        if len(alt) < _MIN_LENGTH and filename:
            keywords = _extract_keywords_from_filename(filename)
            mapped = [_KEYWORD_MAP.get(kw.lower(), kw) for kw in keywords]
            if mapped:
                alt = f"{alt} — {' '.join(mapped)}"
        return alt.strip()

    # 캡션이 없으면 파일명에서 추출
    keywords = _extract_keywords_from_filename(filename) if filename else []
    mapped_keywords = [_KEYWORD_MAP.get(kw.lower(), kw) for kw in keywords]

    # 페이지 문맥에서 관련 문장 탐색
    context_sentence = _find_relevant_context(page_context, keywords + mapped_keywords)

    if context_sentence and mapped_keywords:
        alt = f"{' '.join(mapped_keywords)}: {context_sentence}"
    elif context_sentence:
        alt = context_sentence
    elif mapped_keywords:
        alt = ' '.join(mapped_keywords)
    else:
        alt = '설명 없는 이미지'

    # 길이 제한
    if len(alt) > _MAX_LENGTH:
        alt = alt[:_MAX_LENGTH - 3].rsplit(' ', 1)[0] + '...'

    return alt.strip()


def validate_alt_text(alt: str) -> List[str]:
    """ALT 텍스트 품질을 검증합니다.

    Args:
        alt: 검증할 ALT 텍스트

    Returns:
        발견된 문제 목록 (비어있으면 문제 없음)
    """
    issues = []

    if not alt or not alt.strip():
        issues.append('ALT 텍스트가 비어 있습니다')
        return issues

    alt_stripped = alt.strip()

    if len(alt_stripped) < _MIN_LENGTH:
        issues.append(f'ALT 텍스트가 너무 짧습니다 ({len(alt_stripped)}자, 최소 {_MIN_LENGTH}자)')

    if len(alt_stripped) > _MAX_LENGTH:
        issues.append(f'ALT 텍스트가 너무 깁니다 ({len(alt_stripped)}자, 최대 {_MAX_LENGTH}자)')

    alt_lower = alt_stripped.lower()
    for prefix in _BAD_PREFIXES:
        if alt_lower.startswith(prefix.lower()):
            issues.append(f'"{prefix}"로 시작하면 스크린 리더에서 중복 읽힘 (이미 "이미지"라고 안내)')
            break

    # 파일 확장자가 그대로 포함된 경우
    if re.search(r'\.(png|jpg|jpeg|gif|svg|webp|bmp)\b', alt_lower):
        issues.append('파일 확장자가 포함되어 있습니다')

    # 의미 없는 텍스트 감지
    meaningless = {'image', 'img', 'photo', 'picture', 'untitled', '이미지', '사진'}
    if alt_stripped.lower().strip() in meaningless:
        issues.append('의미 없는 대체 텍스트입니다')

    return issues


def _calculate_quality_score(alt: str, issues: List[str]) -> float:
    """ALT 텍스트 품질 점수를 계산합니다 (0~100)."""
    if not alt or not alt.strip():
        return 0.0

    score = 100.0

    # 이슈 하나당 -20점
    score -= len(issues) * 20

    alt_len = len(alt.strip())

    # 길이 기반 보정
    if alt_len < _MIN_LENGTH:
        score -= ((_MIN_LENGTH - alt_len) * 3)
    elif alt_len > _MAX_LENGTH:
        score -= ((alt_len - _MAX_LENGTH) * 2)

    # 적절한 길이 보너스 (30~80자)
    if 30 <= alt_len <= 80:
        score += 5

    # 구체적 키워드 포함 시 보너스
    descriptive_keywords = ['차트', '그래프', '표', '로고', '다이어그램', '화면', '구조']
    if any(kw in alt for kw in descriptive_keywords):
        score += 5

    return max(0.0, min(100.0, round(score, 1)))


def generate_alt_texts(images: List[dict], page_context: str = '') -> List[AltText]:
    """이미지 목록에 대해 문맥 인지형 대체 텍스트를 생성합니다.

    Args:
        images: 이미지 정보 리스트 [{"id": "img1", "filename": "chart.png", "caption": "매출 그래프"}]
        page_context: 이미지가 포함된 페이지의 텍스트 (선택)

    Returns:
        AltText 객체 리스트
    """
    if not images:
        return []

    results = []
    for image in images:
        image_id = image.get('id', '')
        alt_text = _build_alt_text(image, page_context)
        issues = validate_alt_text(alt_text)
        quality_score = _calculate_quality_score(alt_text, issues)

        results.append(AltText(
            image_id=image_id,
            alt_text=alt_text,
            language='ko',
            quality_score=quality_score,
            issues=issues,
        ))

    return results
