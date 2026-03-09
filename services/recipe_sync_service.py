"""
요리 동영상 동기화 레시피 서비스

요리 동영상 자막을 분석하여 재료 목록, 단계별 조리법,
도구 목록, 소요 시간 등을 포함한 동기화된 레시피를 생성합니다.
순수 파이썬, 규칙 기반.
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Ingredient:
    """재료 항목"""
    name: str
    amount: str
    unit: str


@dataclass
class RecipeStep:
    """조리 단계"""
    step_number: int
    instruction: str
    duration_minutes: int
    tools: List[str]
    timestamp: str


@dataclass
class SyncedRecipe:
    """동기화된 레시피 — 자막 기반 구조화된 레시피"""
    title: str
    ingredients: List[Ingredient]
    steps: List[RecipeStep]
    total_time_minutes: int
    servings: str


# 단위 패턴 (한국어 + 영문)
_UNITS = [
    'g', 'kg', 'ml', 'l', 'L',
    '큰술', '작은술', 'T', 't', 'tbsp', 'tsp',
    '개', '컵', '줌', '꼬집', '조각', '장', '봉지',
    '스푼', '숟가락', '숟갈', '티스푼',
    '마리', '통', '쪽', '톨', '근', '모',
    '인분', '그램', '밀리리터', '리터', '킬로그램',
]
_UNIT_PATTERN = '|'.join(re.escape(u) for u in _UNITS)

# 재료 패턴 A: 숫자 + 단위 + 명사 (예: "200g 닭가슴살")
_INGREDIENT_PATTERN_A = re.compile(
    rf'(\d+(?:[./]\d+)?)\s*({_UNIT_PATTERN})\s+([가-힣a-zA-Z][가-힣a-zA-Z\s]{{0,20}})'
)

# 재료 패턴 B: 명사 + 숫자 + 단위 (예: "달걀 3개", "소금 1큰술")
_INGREDIENT_PATTERN_B = re.compile(
    rf'([가-힣a-zA-Z]{{1,10}})\s+(\d+(?:[./]\d+)?)\s*({_UNIT_PATTERN})'
)

# 동작 키워드 — 조리 단계 분리 기준
_ACTION_KEYWORDS = [
    '넣', '볶', '끓', '자르', '섞', '굽', '찌',
    '데치', '튀기', '무치', '삶', '졸이',
    '썰', '다지', '채썰', '으깨', '반죽',
    '뿌리', '올리', '담', '부어', '휘저',
    '버무리', '재우', '절이', '말', '감',
    '덮', '뒤집', '식히', '꺼내', '담아',
]

# 도구 키워드
_TOOL_KEYWORDS = [
    '팬', '프라이팬', '냄비', '오븐', '믹서', '믹서기', '블렌더',
    '전자레인지', '에어프라이어', '그릴', '냄비', '솥', '압력솥',
    '젓가락', '주걱', '국자', '뒤집개', '거품기', '체',
    '도마', '칼', '가위', '볼', '그릇', '접시',
    '랩', '호일', '종이타월', '쿠킹시트', '오븐팬',
    '계량컵', '계량스푼', '저울', '온도계',
    '찜기', '찜통', '웍',
]

# 시간 표현 패턴 (분/초)
_TIME_PATTERN = re.compile(
    r'(\d+)\s*(?:분|min|minute)', re.IGNORECASE
)

# 타임스탬프 패턴
_TIMESTAMP_PATTERN = re.compile(
    r'\[(\d{1,2}:\d{2}(?::\d{2})?)\]'
)

# 인분 패턴
_SERVINGS_PATTERN = re.compile(
    r'(\d+)\s*인분'
)


def _extract_title(transcript: str) -> str:
    """자막에서 레시피 제목을 추출합니다."""
    # 첫 줄 또는 "오늘은 ... 만들" 패턴
    lines = [l.strip() for l in transcript.split('\n') if l.strip()]
    if not lines:
        return "레시피"

    # "오늘은/오늘의 ~" 패턴
    for line in lines[:5]:
        match = re.search(r'오늘[은의]?\s+(.+?)(?:을|를)?\s*(?:만들|해볼|소개)', line)
        if match:
            return match.group(1).strip()

    # 첫 줄이 짧으면 제목으로 사용
    if len(lines[0]) < 50:
        return lines[0]

    return "레시피"


def _extract_servings(transcript: str) -> str:
    """인분 정보를 추출합니다."""
    match = _SERVINGS_PATTERN.search(transcript)
    if match:
        return f"{match.group(1)}인분"
    return "2인분"  # 기본값


def extract_ingredients(transcript: str) -> List[Ingredient]:
    """자막에서 재료 목록을 추출합니다.

    Args:
        transcript: 요리 동영상 자막 텍스트

    Returns:
        Ingredient 리스트
    """
    ingredients = []
    seen = set()

    # 패턴 A: 숫자 + 단위 + 명사 (예: "200g 닭가슴살")
    for match in _INGREDIENT_PATTERN_A.finditer(transcript):
        amount = match.group(1)
        unit = match.group(2)
        name = match.group(3).strip()

        if name in seen:
            continue
        seen.add(name)
        ingredients.append(Ingredient(name=name, amount=amount, unit=unit))

    # 패턴 B: 명사 + 숫자 + 단위 (예: "달걀 3개", "소금 1큰술")
    for match in _INGREDIENT_PATTERN_B.finditer(transcript):
        name = match.group(1).strip()
        amount = match.group(2)
        unit = match.group(3)

        if name in seen:
            continue
        seen.add(name)
        ingredients.append(Ingredient(name=name, amount=amount, unit=unit))

    return ingredients


def _find_tools_in_text(text: str) -> List[str]:
    """텍스트에서 도구 키워드를 찾아 반환합니다."""
    tools = []
    text_lower = text.lower()
    for tool in _TOOL_KEYWORDS:
        if tool in text_lower and tool not in tools:
            tools.append(tool)
    return tools


def _estimate_duration(text: str) -> int:
    """텍스트에서 소요 시간(분)을 추정합니다."""
    match = _TIME_PATTERN.search(text)
    if match:
        return int(match.group(1))
    # 시간 언급 없으면 기본 2분
    return 2


def _extract_timestamp_for_line(line: str) -> str:
    """라인에서 타임스탬프를 추출합니다."""
    match = _TIMESTAMP_PATTERN.search(line)
    if match:
        return match.group(1)
    return ""


def _split_into_steps(transcript: str) -> List[RecipeStep]:
    """자막을 동작 키워드 기준으로 조리 단계로 분리합니다."""
    steps = []
    lines = [l.strip() for l in transcript.split('\n') if l.strip()]

    current_instruction = []
    step_number = 0

    for line in lines:
        # 동작 키워드 포함 여부 확인
        has_action = any(kw in line for kw in _ACTION_KEYWORDS)

        if has_action:
            # 이전 단계가 있으면 저장
            if current_instruction:
                combined = ' '.join(current_instruction)
                step_number += 1
                steps.append(RecipeStep(
                    step_number=step_number,
                    instruction=combined,
                    duration_minutes=_estimate_duration(combined),
                    tools=_find_tools_in_text(combined),
                    timestamp=_extract_timestamp_for_line(current_instruction[0]),
                ))
                current_instruction = []
            current_instruction.append(line)
        elif current_instruction:
            # 현재 단계에 추가
            current_instruction.append(line)

    # 마지막 단계 처리
    if current_instruction:
        combined = ' '.join(current_instruction)
        step_number += 1
        steps.append(RecipeStep(
            step_number=step_number,
            instruction=combined,
            duration_minutes=_estimate_duration(combined),
            tools=_find_tools_in_text(combined),
            timestamp=_extract_timestamp_for_line(current_instruction[0]),
        ))

    return steps


def sync_recipe(cooking_transcript: str) -> SyncedRecipe:
    """요리 동영상 자막을 분석하여 동기화된 레시피를 생성합니다.

    Args:
        cooking_transcript: 요리 동영상 자막 전체 텍스트

    Returns:
        SyncedRecipe 데이터클래스 인스턴스
    """
    title = _extract_title(cooking_transcript)
    ingredients = extract_ingredients(cooking_transcript)
    steps = _split_into_steps(cooking_transcript)
    servings = _extract_servings(cooking_transcript)

    # 총 소요 시간: 각 단계 시간 합산
    total_time = sum(s.duration_minutes for s in steps) if steps else 0

    return SyncedRecipe(
        title=title,
        ingredients=ingredients,
        steps=steps,
        total_time_minutes=total_time,
        servings=servings,
    )
