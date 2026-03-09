"""규정 문구 삽입 서비스

콘텐츠 유형에 따라 필수 면책조항(disclaimer)을 자동으로 삽입한다.
이미 포함된 문구는 중복 삽입하지 않는다.
"""
import re
from dataclasses import dataclass


@dataclass
class Disclaimer:
    """면책조항 항목"""
    text: str                   # 면책 문구 본문
    category: str               # "finance" | "health" | "legal" | "general"
    required: bool              # 필수 여부
    position: str               # "header" | "footer" | "inline"


# 콘텐츠 유형별 면책조항 정의
_DISCLAIMERS: dict[str, list[Disclaimer]] = {
    'finance': [
        Disclaimer(
            text='※ 본 콘텐츠는 투자 권유가 아니며, 투자 판단의 참고 자료로만 활용하시기 바랍니다.',
            category='finance',
            required=True,
            position='footer',
        ),
        Disclaimer(
            text='※ 투자에 따른 손실은 투자자 본인에게 귀속됩니다.',
            category='finance',
            required=True,
            position='footer',
        ),
    ],
    'health': [
        Disclaimer(
            text='※ 본 콘텐츠는 의학적 조언이 아닙니다. 건강 관련 결정은 반드시 의료 전문가와 상담하시기 바랍니다.',
            category='health',
            required=True,
            position='footer',
        ),
    ],
    'legal': [
        Disclaimer(
            text='※ 본 콘텐츠는 법적 조언이 아닙니다. 법률 문제는 전문 변호사와 상담하시기 바랍니다.',
            category='legal',
            required=True,
            position='footer',
        ),
    ],
    'general': [
        Disclaimer(
            text='※ 본 콘텐츠는 AI에 의해 생성되었으며, 사실과 다를 수 있습니다.',
            category='general',
            required=True,
            position='footer',
        ),
    ],
}

# 유효한 콘텐츠 유형
_VALID_CONTENT_TYPES = set(_DISCLAIMERS.keys())


def _is_already_present(content: str, disclaimer_text: str) -> bool:
    """면책 문구가 이미 콘텐츠에 포함되어 있는지 확인한다.

    특수문자(※)를 제외한 핵심 텍스트로 비교하여
    약간의 서식 차이도 감지한다.

    Args:
        content: 원본 콘텐츠
        disclaimer_text: 확인할 면책 문구

    Returns:
        이미 포함되어 있으면 True
    """
    # 특수문자, 공백 정규화 후 비교
    def normalize(text: str) -> str:
        text = re.sub(r'[※*•\s]+', ' ', text)
        return text.strip().lower()

    normalized_content = normalize(content)
    normalized_disclaimer = normalize(disclaimer_text)

    return normalized_disclaimer in normalized_content


def get_required_disclaimers(content_type: str) -> list[Disclaimer]:
    """콘텐츠 유형별 필수 문구를 조회한다.

    Args:
        content_type: 콘텐츠 유형 ("finance" | "health" | "legal" | "general")

    Returns:
        해당 유형의 Disclaimer 리스트

    Raises:
        ValueError: content_type이 유효하지 않은 경우
    """
    if content_type not in _VALID_CONTENT_TYPES:
        raise ValueError(
            f"유효하지 않은 content_type: '{content_type}'. "
            f"허용값: {sorted(_VALID_CONTENT_TYPES)}"
        )

    return list(_DISCLAIMERS[content_type])


def insert_regulatory(content: str, content_type: str = 'general') -> str:
    """콘텐츠에 필수 규정 문구를 삽입한다.

    이미 포함된 문구는 중복 삽입하지 않으며,
    position에 따라 header/footer/inline 위치에 삽입한다.

    Args:
        content: 원본 콘텐츠
        content_type: 콘텐츠 유형 (기본: "general")

    Returns:
        면책조항이 삽입된 콘텐츠

    Raises:
        ValueError: content가 None이거나, content_type이 유효하지 않은 경우
    """
    if content is None:
        raise ValueError("content는 None일 수 없습니다")

    if content_type not in _VALID_CONTENT_TYPES:
        raise ValueError(
            f"유효하지 않은 content_type: '{content_type}'. "
            f"허용값: {sorted(_VALID_CONTENT_TYPES)}"
        )

    disclaimers = _DISCLAIMERS[content_type]

    # 삽입할 문구 분류
    header_parts: list[str] = []
    footer_parts: list[str] = []

    for d in disclaimers:
        if not d.required:
            continue

        # 중복 삽입 방지
        if _is_already_present(content, d.text):
            continue

        if d.position == 'header':
            header_parts.append(d.text)
        elif d.position == 'footer':
            footer_parts.append(d.text)
        else:  # inline — footer와 동일하게 처리
            footer_parts.append(d.text)

    # 조합
    result = content

    if header_parts:
        header_block = '\n'.join(header_parts) + '\n\n'
        result = header_block + result

    if footer_parts:
        footer_block = '\n\n---\n' + '\n'.join(footer_parts)
        result = result + footer_block

    return result
