"""
포용적 언어 검사 서비스

콘텐츠에서 배제적/편향적 표현을 감지하고
포용적 대체 표현을 제안합니다.
"""
import re
import logging
from collections import Counter

logger = logging.getLogger(__name__)

# ── 5가지 카테고리별 감지 규칙 ──
# 각 항목: (패턴, 대체 표현, 심각도)
_RULES = {
    'gender': [
        # 한국어
        ('여자답게', '자기다운 방식으로', 'medium'),
        ('남자답게', '자기다운 방식으로', 'medium'),
        ('여자라서', '성별과 무관하게', 'medium'),
        ('남자라서', '성별과 무관하게', 'medium'),
        ('그녀', '그 사람', 'low'),
        ('아줌마', '여성', 'medium'),
        ('아저씨', '남성', 'low'),
        # 영어
        ('chairman', 'chairperson', 'medium'),
        ('manpower', 'workforce', 'medium'),
        ('fireman', 'firefighter', 'medium'),
        ('policeman', 'police officer', 'medium'),
        ('businessman', 'businessperson', 'medium'),
        ('stewardess', 'flight attendant', 'medium'),
        ('mankind', 'humankind', 'low'),
        ('man-made', 'artificial', 'low'),
        ('housewife', 'homemaker', 'low'),
    ],
    'disability': [
        # 한국어
        ('불구', '장애가 있는', 'high'),
        ('장님', '시각장애인', 'high'),
        ('벙어리', '언어장애인', 'high'),
        ('귀머거리', '청각장애인', 'high'),
        ('절름발이', '지체장애가 있는 사람', 'high'),
        ('병신', '장애가 있는 사람', 'high'),
        ('정상인', '비장애인', 'medium'),
        ('장애자', '장애인', 'medium'),
        # 영어
        ('blind spot', '사각지대', 'low'),
        ('crazy', '놀라운', 'low'),
        ('lame', '부적절한', 'medium'),
        ('cripple', '장애가 있는 사람', 'high'),
        ('retarded', '발달장애가 있는', 'high'),
        ('handicapped', '장애가 있는', 'medium'),
        ('dumb', '무언의', 'medium'),
        ('insane', '비합리적인', 'low'),
    ],
    'age': [
        # 한국어
        ('꼰대', '경험이 많은 사람', 'medium'),
        ('노인네', '고령자', 'medium'),
        ('늙은이', '고령자', 'medium'),
        ('애들', '젊은 세대', 'low'),
        ('어린것', '어린 사람', 'medium'),
        ('틀딱', '고령 세대', 'high'),
        # 영어
        ('old-fashioned', '전통적인', 'low'),
        ('senile', '고령의', 'high'),
        ('geezer', '고령자', 'medium'),
        ('kiddo', '젊은 사람', 'low'),
    ],
    'cultural': [
        # 한국어
        ('후진국', '개발도상국', 'medium'),
        ('미개한', '다른 문화의', 'high'),
        ('야만적', '문화적 차이가 있는', 'high'),
        ('동남아', '동남아시아 지역', 'low'),
        ('외노자', '외국인 근로자', 'high'),
        ('다문화 가정', '다양한 문화 배경의 가정', 'low'),
        ('혼혈', '다문화 배경', 'medium'),
        # 영어
        ('third world', '개발도상국', 'medium'),
        ('exotic', '독특한', 'low'),
        ('primitive', '전통적인', 'high'),
        ('illegal alien', '비정규 체류자', 'high'),
    ],
    'ability': [
        # 한국어
        ('멍청한', '적절하지 않은', 'medium'),
        ('바보', '부적절한', 'medium'),
        ('저능', '이해가 부족한', 'high'),
        ('모자란', '경험이 부족한', 'medium'),
        # 영어
        ('dummy', '플레이스홀더', 'low'),
        ('idiot', '부적절한', 'medium'),
        ('stupid', '비효율적인', 'medium'),
        ('moron', '부적절한', 'high'),
    ],
}

# 컴파일된 패턴 캐시 (대소문자 무시)
_COMPILED_RULES = []
for category, rules in _RULES.items():
    for phrase, alternative, severity in rules:
        _COMPILED_RULES.append({
            'pattern': re.compile(re.escape(phrase), re.IGNORECASE),
            'phrase': phrase,
            'category': category,
            'alternative': alternative,
            'severity': severity,
        })


def check_inclusive_language(content: str) -> dict:
    """콘텐츠에서 배제적/편향적 표현을 감지합니다.

    Args:
        content: 검사할 콘텐츠

    Returns:
        {
            "issues": [{"phrase", "category", "sentence", "alternative", "severity"}],
            "summary": {"total": int, "by_category": dict, "by_severity": dict},
            "inclusivity_score": float,  # 0-100
            "suggestions": list[str],
        }
    """
    if not content or not content.strip():
        return {
            'issues': [],
            'summary': {'total': 0, 'by_category': {}, 'by_severity': {}},
            'inclusivity_score': 100.0,
            'suggestions': ['검사할 콘텐츠가 비어 있습니다.'],
        }

    # 문장 분리
    sentences = _split_sentences(content)

    # 이슈 감지
    issues = []
    seen = set()  # (phrase_lower, sentence) 중복 방지

    for rule in _COMPILED_RULES:
        for sentence in sentences:
            if rule['pattern'].search(sentence):
                key = (rule['phrase'].lower(), sentence)
                if key not in seen:
                    seen.add(key)
                    issues.append({
                        'phrase': rule['phrase'],
                        'category': rule['category'],
                        'sentence': sentence,
                        'alternative': rule['alternative'],
                        'severity': rule['severity'],
                    })

    # 요약 통계
    cat_counter = Counter(i['category'] for i in issues)
    sev_counter = Counter(i['severity'] for i in issues)

    summary = {
        'total': len(issues),
        'by_category': dict(cat_counter),
        'by_severity': dict(sev_counter),
    }

    # 포용성 점수 계산
    score = _calculate_score(issues, content)

    # 제안 생성
    suggestions = _generate_suggestions(issues, cat_counter)

    return {
        'issues': issues,
        'summary': summary,
        'inclusivity_score': score,
        'suggestions': suggestions,
    }


def _split_sentences(content: str) -> list:
    """콘텐츠를 문장 단위로 분리합니다."""
    # 줄바꿈 또는 문장부호로 분리
    raw = re.split(r'(?<=[.!?。])\s+|\n+', content)
    return [s.strip() for s in raw if s.strip()]


def _calculate_score(issues: list, content: str) -> float:
    """포용성 점수를 계산합니다 (0-100).

    감점 기준:
    - high 심각도: 15점 차감
    - medium 심각도: 8점 차감
    - low 심각도: 3점 차감
    """
    if not issues:
        return 100.0

    deductions = 0.0
    for issue in issues:
        if issue['severity'] == 'high':
            deductions += 15
        elif issue['severity'] == 'medium':
            deductions += 8
        else:
            deductions += 3

    score = max(0.0, 100.0 - deductions)
    return round(score, 1)


def _generate_suggestions(issues: list, by_category: Counter) -> list:
    """개선 제안을 생성합니다."""
    suggestions = []

    if not issues:
        suggestions.append('편향적 표현이 감지되지 않았습니다. 포용적인 콘텐츠입니다.')
        return suggestions

    # 카테고리별 맞춤 제안
    category_tips = {
        'gender': '성별 중립적 표현을 사용하세요. 직업명에서 성별을 제거하면 더 포용적입니다.',
        'disability': '장애를 가진 사람을 먼저 언급하는 "사람 중심 언어(person-first language)"를 사용하세요.',
        'age': '나이에 대한 고정관념을 피하고 중립적 표현을 사용하세요.',
        'cultural': '문화적 배경을 존중하는 표현을 사용하세요. 일반화를 피하세요.',
        'ability': '능력과 관련된 비하 표현 대신 구체적이고 중립적인 표현을 사용하세요.',
    }

    for cat in by_category:
        if cat in category_tips:
            suggestions.append(category_tips[cat])

    # 심각도 기반 종합 제안
    high_count = sum(1 for i in issues if i['severity'] == 'high')
    if high_count > 0:
        suggestions.append(f'높은 심각도의 표현이 {high_count}건 감지되었습니다. 즉시 수정을 권장합니다.')

    return suggestions
