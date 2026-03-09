"""녹화 영상 자막에서 단계별 가이드를 추출하는 서비스

화면 녹화/동작 설명 자막을 분석하여 사용자 조작을 단계별 가이드로 변환한다.
순수 Python 텍스트 파싱 — AI 호출 없음.
"""
import re
from dataclasses import dataclass, field


# ── 동작 키워드 매핑 (한국어 + 영어) ──────────────────────────
_ACTION_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r'클릭|click|눌러|누르|press|tap', re.IGNORECASE), '클릭'),
    (re.compile(r'입력|타이핑|typing|type|작성|적어|적고|써|write', re.IGNORECASE), '입력'),
    (re.compile(r'선택|select|choose|고르|골라', re.IGNORECASE), '선택'),
    (re.compile(r'드래그|drag|끌어|끌고|옮기|move', re.IGNORECASE), '드래그'),
    (re.compile(r'스크롤|scroll|내려|올려', re.IGNORECASE), '스크롤'),
    (re.compile(r'열어|열기|open|실행|launch|시작', re.IGNORECASE), '열기'),
    (re.compile(r'닫기|닫아|close|종료', re.IGNORECASE), '닫기'),
    (re.compile(r'복사|copy|붙여넣기|paste|ctrl\+c|ctrl\+v', re.IGNORECASE), '복사/붙여넣기'),
    (re.compile(r'삭제|delete|지워|지우|remove', re.IGNORECASE), '삭제'),
    (re.compile(r'저장|save|확인|confirm|완료|done|submit', re.IGNORECASE), '확인'),
    (re.compile(r'검색|search|찾아|찾기|find', re.IGNORECASE), '검색'),
    (re.compile(r'설정|setting|옵션|option|configure', re.IGNORECASE), '설정'),
    (re.compile(r'다운로드|download|내려받|업로드|upload|올려', re.IGNORECASE), '다운로드/업로드'),
    (re.compile(r'로그인|login|sign.?in|접속', re.IGNORECASE), '로그인'),
    (re.compile(r'전환|switch|변경|change|toggle|바꿔|바꾸', re.IGNORECASE), '전환'),
]

# 사전 조건 힌트 키워드
_PREREQ_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r'로그인|login|sign.?in|접속', re.IGNORECASE), '해당 서비스에 로그인'),
    (re.compile(r'설치|install', re.IGNORECASE), '필요한 프로그램 설치'),
    (re.compile(r'브라우저|browser|chrome|firefox', re.IGNORECASE), '웹 브라우저 실행'),
    (re.compile(r'계정|account|가입', re.IGNORECASE), '계정 생성/준비'),
]

# 대상 요소 추출 패턴 (따옴표/괄호 안 텍스트, 또는 버튼/메뉴/탭 뒤 명사)
_TARGET_PATTERNS: list[re.Pattern] = [
    re.compile(r'["\']([^"\']+)["\']'),                        # "저장" 버튼
    re.compile(r'[「」]([^「」]+)[」]'),                         # 「설정」
    re.compile(r'【([^】]+)】'),                                 # 【확인】
    re.compile(r'(?:버튼|button|메뉴|menu|탭|tab|링크|link)\s*[:\-]?\s*(\S+)', re.IGNORECASE),
]

# 팁 키워드
_TIP_PATTERN = re.compile(
    r'(?:참고|tip|hint|주의|note|중요|팁|참조|알아두|잊지)[:\-\s]*(.*)',
    re.IGNORECASE,
)


@dataclass
class GuideStep:
    """단계별 가이드의 개별 단계"""
    step_number: int
    action: str             # "클릭", "입력", "선택" 등
    target: str             # 대상 요소
    description: str
    tip: str | None = None


@dataclass
class StepGuide:
    """단계별 가이드 전체 결과"""
    title: str
    total_steps: int        # 5개+
    steps: list[GuideStep] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    estimated_time: str = ''


def recording_to_guide(transcript: str) -> StepGuide:
    """화면 녹화 자막에서 단계별 가이드를 생성한다.

    Args:
        transcript: 녹화 영상의 자막 텍스트

    Returns:
        StepGuide: 5단계 이상의 가이드

    Raises:
        ValueError: 자막이 비어있는 경우
    """
    if not transcript or not transcript.strip():
        raise ValueError('자막 텍스트가 비어있습니다')

    lines = _split_lines(transcript)

    # 1) 동작 문장 선별
    raw_steps = _extract_action_lines(lines)

    # 2) 중복 제거 (연속으로 같은 action+target이면 병합)
    deduped = _deduplicate_steps(raw_steps)

    # 3) 5단계 미만이면 일반 문장도 포함하여 보강
    if len(deduped) < 5:
        deduped = _pad_steps(deduped, lines)

    # 4) 번호 부여
    steps: list[GuideStep] = []
    for i, raw in enumerate(deduped, 1):
        steps.append(GuideStep(
            step_number=i,
            action=raw['action'],
            target=raw['target'],
            description=raw['description'],
            tip=raw.get('tip'),
        ))

    # 5) 사전 조건 추출
    prerequisites = _extract_prerequisites(transcript)

    # 6) 제목 생성
    title = _generate_title(steps)

    # 7) 예상 시간 계산 (단계당 약 30초)
    total_seconds = len(steps) * 30
    estimated_time = _format_duration(total_seconds)

    return StepGuide(
        title=title,
        total_steps=len(steps),
        steps=steps,
        prerequisites=prerequisites,
        estimated_time=estimated_time,
    )


# ── 내부 함수 ────────────────────────────────────────────────

def _split_lines(text: str) -> list[str]:
    """텍스트를 문장 단위로 분리

    팁/참고 키워드 앞에서는 분리하지 않는다 (팁이 동작 문장에 붙어있어야 함).
    """
    # 줄바꿈 기준 분리 후 빈 줄 제거
    raw_lines = text.strip().split('\n')
    result = []
    for line in raw_lines:
        stripped = line.strip()
        if not stripped:
            continue
        # 마침표 뒤에 팁/참고 키워드가 오면 분리하지 않음
        sentences = re.split(r'(?<=[.!?。])\s+(?!(?:참고|tip|hint|주의|note|중요|팁|참조))', stripped)
        result.extend(s.strip() for s in sentences if s.strip())
    return result


def _detect_action(text: str) -> str | None:
    """텍스트에서 동작 키워드를 감지하여 동작명 반환"""
    for pattern, action_name in _ACTION_PATTERNS:
        if pattern.search(text):
            return action_name
    return None


def _extract_target(text: str) -> str:
    """텍스트에서 동작 대상 요소를 추출"""
    for pattern in _TARGET_PATTERNS:
        m = pattern.search(text)
        if m:
            return m.group(1).strip()
    # 패턴 매칭 실패 시 — 핵심 명사구 추출 시도
    # 동사/조사 제거 후 가장 긴 단어 반환
    words = re.findall(r'[가-힣a-zA-Z0-9_]+', text)
    # 동작 키워드 제외
    skip = {'클릭', '입력', '선택', '드래그', '스크롤', '열기', '닫기',
            '저장', '삭제', '확인', '검색', '설정', '전환', '복사', '붙여넣기',
            '그리고', '다음', '먼저', '그다음', '이제', '후에', '합니다',
            '합니다', '하세요', '합니다', '주세요', '버튼을', '메뉴를'}
    candidates = [w for w in words if w not in skip and len(w) > 1]
    if candidates:
        return candidates[0]
    return '화면'


def _extract_tip(text: str) -> str | None:
    """팁/참고 문구 추출"""
    m = _TIP_PATTERN.search(text)
    if m:
        tip_text = m.group(1).strip()
        return tip_text if tip_text else None
    return None


def _extract_action_lines(lines: list[str]) -> list[dict]:
    """동작 키워드가 포함된 문장을 선별"""
    results = []
    for line in lines:
        action = _detect_action(line)
        if action:
            results.append({
                'action': action,
                'target': _extract_target(line),
                'description': line.strip(),
                'tip': _extract_tip(line),
            })
    return results


def _deduplicate_steps(steps: list[dict]) -> list[dict]:
    """연속 중복 단계 제거 (같은 action + target)"""
    if not steps:
        return steps
    deduped = [steps[0]]
    for step in steps[1:]:
        prev = deduped[-1]
        if step['action'] == prev['action'] and step['target'] == prev['target']:
            # 팁이 있으면 병합
            if step.get('tip') and not prev.get('tip'):
                prev['tip'] = step['tip']
            continue
        deduped.append(step)
    return deduped


def _pad_steps(existing: list[dict], lines: list[str]) -> list[dict]:
    """5단계 미만일 때 일반 문장으로 보강

    이미 포함된 문장은 건너뛰고, 동작이 없는 문장은 '확인' 동작으로 추가.
    """
    existing_descs = {s['description'] for s in existing}
    padded = list(existing)

    for line in lines:
        if len(padded) >= 5:
            break
        if line.strip() in existing_descs:
            continue
        if len(line.strip()) < 5:
            continue
        padded.append({
            'action': '확인',
            'target': _extract_target(line),
            'description': line.strip(),
            'tip': _extract_tip(line),
        })
        existing_descs.add(line.strip())

    return padded


def _extract_prerequisites(text: str) -> list[str]:
    """자막에서 사전 조건 추출"""
    found = []
    seen = set()
    for pattern, prereq in _PREREQ_PATTERNS:
        if pattern.search(text) and prereq not in seen:
            found.append(prereq)
            seen.add(prereq)
    return found


def _generate_title(steps: list[GuideStep]) -> str:
    """단계 목록으로부터 가이드 제목 생성"""
    if not steps:
        return '단계별 가이드'

    # 첫 번째와 마지막 단계의 대상을 조합
    first_target = steps[0].target if steps else ''
    last_target = steps[-1].target if steps else ''

    if first_target and last_target and first_target != last_target:
        return f'{first_target}에서 {last_target}까지 가이드'
    elif first_target:
        return f'{first_target} 사용 가이드'
    return '단계별 가이드'


def _format_duration(seconds: int) -> str:
    """초를 사람이 읽기 쉬운 시간 문자열로 변환"""
    if seconds < 60:
        return f'약 {seconds}초'
    minutes = seconds // 60
    remainder = seconds % 60
    if remainder == 0:
        return f'약 {minutes}분'
    return f'약 {minutes}분 {remainder}초'
