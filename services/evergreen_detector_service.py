"""
에버그린 감지 서비스

콘텐츠에서 날짜/통계/제품명/버전/이벤트 등 시간이 지나면 만료될 수 있는
변동 요소(Expiry Signal)를 감지하고, 에버그린 콘텐츠 여부를 판단합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from dataclasses import dataclass, field
from typing import List


# ── 데이터 클래스 ──

@dataclass
class ExpirySignal:
    """만료 가능 신호"""
    text: str                # 감지된 텍스트
    signal_type: str         # "date" | "statistic" | "product_name" | "version" | "event"
    position: int            # 콘텐츠 내 문자 위치
    severity: str            # "high" | "medium" | "low"


# ── 날짜 패턴 (한국어 + 영어) ──

# "2024년", "2024년 3월", "2024.03", "2024-03-15", "March 2024"
_DATE_PATTERNS = [
    # 한국어: 20XX년 (월/일 선택)
    re.compile(r'20[0-9]{2}년(?:\s*\d{1,2}월)?(?:\s*\d{1,2}일)?'),
    # ISO / 점 구분: 2024-03-15, 2024.03.15, 2024/03/15
    re.compile(r'20[0-9]{2}[-./]\d{1,2}(?:[-./]\d{1,2})?'),
    # 영어 월 + 연도: March 2024, Jan 2025
    re.compile(
        r'(?:January|February|March|April|May|June|July|August|September|'
        r'October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
        r'\s+20[0-9]{2}',
        re.IGNORECASE,
    ),
    # "올해", "작년", "내년", "지난달", "이번 분기"
    re.compile(r'(?:올해|작년|내년|지난\s*(?:달|해|주)|이번\s*(?:달|분기|해))'),
    # "최근 N일/주/개월/년"
    re.compile(r'최근\s+\d+\s*(?:일|주|개월|년)'),
    # "this year", "last year", "last month"
    re.compile(r'\b(?:this|last|next)\s+(?:year|month|quarter|week)\b', re.IGNORECASE),
]

# ── 통계 패턴 ──

_STATISTIC_PATTERNS = [
    # 숫자 + % (예: "78%", "3.5%")
    re.compile(r'\d+(?:\.\d+)?%'),
    # "N명", "N건", "N억", "N만", "N조"
    re.compile(r'\d[\d,]*\s*(?:명|건|억|만|조|원|달러|달러)'),
    # 영어 단위: "1.5 million", "$500 billion", "100K users"
    re.compile(r'\$?\d[\d,.]*\s*(?:million|billion|trillion|K|M|B)\b', re.IGNORECASE),
    # "XX% 증가/감소/성장"
    re.compile(r'\d+(?:\.\d+)?%\s*(?:증가|감소|성장|하락|상승)'),
    # "보고서에 따르면", "조사에 따르면"
    re.compile(r'(?:보고서|조사|연구|설문|통계)에\s*따르면'),
    # "according to", "study shows"
    re.compile(r'\baccording\s+to\b', re.IGNORECASE),
]

# ── 제품명/서비스명 패턴 ──

_PRODUCT_PATTERNS = [
    # 제품 + 숫자 (예: "iPhone 15", "Galaxy S24", "Pixel 8")
    re.compile(r'\b(?:iPhone|Galaxy|Pixel|iPad|MacBook|Surface|PlayStation|Xbox)\s*\d+\S*', re.IGNORECASE),
    # Windows XX, macOS XX, Android XX, iOS XX
    re.compile(r'\b(?:Windows|macOS|Android|iOS)\s+\d+\S*', re.IGNORECASE),
    # 한국어 제품명 + 모델
    re.compile(r'(?:갤럭시|아이폰|아이패드|맥북|윈도우)\s*\S*\d+\S*'),
    # "XX 제품 출시", "XX 모델 발표" (제품명 맥락)
    re.compile(r'(?:갤럭시|아이폰|아이패드|맥북|픽셀|서피스)\s*\S*\s*(?:출시|발표|런칭|공개)'),
]

# ── 버전 패턴 ──

_VERSION_PATTERNS = [
    # v1.2.3, V2.0, ver 3.1
    re.compile(r'\b[vV](?:er(?:sion)?)?\s*\.?\d+(?:\.\d+)+'),
    # 소프트웨어 이름 + 버전: "Python 3.12", "React 18", "Node.js 20"
    re.compile(
        r'\b(?:Python|Java|Node\.?js|React|Vue|Angular|TypeScript|'
        r'Swift|Kotlin|Go|Rust|Ruby|PHP|Django|Flask|Spring|'
        r'Next\.?js|Nuxt|Svelte|TensorFlow|PyTorch)\s+\d+(?:\.\d+)*',
        re.IGNORECASE,
    ),
    # "베타", "알파", "RC" + 숫자
    re.compile(r'\b(?:beta|alpha|RC)\s*\d*\b', re.IGNORECASE),
]

# ── 이벤트 패턴 ──

_EVENT_PATTERNS = [
    # 한국어 이벤트
    re.compile(r'(?:컨퍼런스|세미나|행사|박람회|전시회|해커톤|밋업|워크숍)\s*\S*'),
    # 영어 이벤트 (한국어 텍스트 내에서도 매칭되도록 \b 대신 경계 완화)
    re.compile(r'(?:WWDC|CES|MWC|GDC|re:Invent|Build|I/O|Connect)\s*\d{2,4}', re.IGNORECASE),
    # "XX 대회", "XX 발표회"
    re.compile(r'\S+\s*(?:대회|발표회|시상식|어워드)'),
    # "이벤트 기간", "할인 기간"
    re.compile(r'(?:이벤트|할인|프로모션|세일)\s*기간'),
]


# ── 심각도 매핑 ──

_SEVERITY_MAP = {
    'date': 'high',
    'statistic': 'high',
    'product_name': 'medium',
    'version': 'medium',
    'event': 'low',
}

# 패턴 → (signal_type, 패턴 리스트)
_ALL_PATTERNS = [
    ('date', _DATE_PATTERNS),
    ('statistic', _STATISTIC_PATTERNS),
    ('product_name', _PRODUCT_PATTERNS),
    ('version', _VERSION_PATTERNS),
    ('event', _EVENT_PATTERNS),
]


def detect_expiry_signals(content: str) -> List[ExpirySignal]:
    """콘텐츠에서 날짜/통계/제품명 등 변동 가능 요소를 감지합니다.

    Args:
        content: 분석할 콘텐츠 텍스트

    Returns:
        감지된 ExpirySignal 목록 (position 오름차순 정렬)
    """
    if not content or not content.strip():
        return []

    signals: List[ExpirySignal] = []
    # 중복 방지: (position, text) 세트
    seen = set()

    for signal_type, patterns in _ALL_PATTERNS:
        severity = _SEVERITY_MAP[signal_type]
        for pattern in patterns:
            for match in pattern.finditer(content):
                key = (match.start(), match.group())
                if key in seen:
                    continue
                seen.add(key)
                signals.append(ExpirySignal(
                    text=match.group(),
                    signal_type=signal_type,
                    position=match.start(),
                    severity=severity,
                ))

    # position 기준 정렬
    signals.sort(key=lambda s: s.position)
    return signals


def is_evergreen(content: str, threshold: int = 3) -> bool:
    """에버그린 콘텐츠 여부를 판단합니다.

    만료 신호(expiry signals) 수가 threshold 이하이면 에버그린으로 판단합니다.

    Args:
        content: 분석할 콘텐츠 텍스트
        threshold: 만료 신호 허용 최대 개수 (기본 3)

    Returns:
        에버그린 여부 (True = 에버그린)
    """
    signals = detect_expiry_signals(content)
    return len(signals) <= threshold


def get_evergreen_score(content: str) -> float:
    """에버그린 점수를 0~100 범위로 반환합니다.

    만료 신호가 적을수록 높은 점수. 심각도(severity)에 따라 가중 감점합니다.

    Args:
        content: 분석할 콘텐츠 텍스트

    Returns:
        0~100 사이 점수 (100 = 완벽한 에버그린)
    """
    if not content or not content.strip():
        return 100.0

    signals = detect_expiry_signals(content)
    if not signals:
        return 100.0

    # 심각도별 가중치
    weight_map = {'high': 15.0, 'medium': 8.0, 'low': 3.0}
    penalty = sum(weight_map.get(s.severity, 5.0) for s in signals)

    score = max(0.0, 100.0 - penalty)
    return round(score, 1)
