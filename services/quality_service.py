"""
품질 자동 평가 서비스 (LLM-as-judge 패턴)

생성된 콘텐츠를 별도 AI 호출로 평가하고, 기준 미달 시 재생성합니다.
quality_check: true 파라미터가 있을 때만 동작합니다.

추가 비용 안내:
- 품질 평가 활성화 시 요청당 AI 호출 1회 추가 (평가 전용)
- 재생성 활성화 시 최대 1회 추가 (기준 미달 시만)
"""
import json
import re
import os
from typing import Dict, Optional, Tuple

from flask import current_app

# 등급 순서 (낮을수록 낮은 등급)
_GRADE_ORDER = {'D': 0, 'C': 1, 'B': 2, 'A': 3}

# 기본 평가 모델 (가장 저렴하고 빠른 모델 우선)
_EVAL_MODEL_CANDIDATES = [
    'zhipuai/GLM-4.5-Air',
    'gemini/gemini-2.5-flash-lite-preview-09-2025',
    'gemini/gemini-3-flash-preview',
    'deepseek/deepseek-chat',
]


def _get_eval_model() -> Optional[str]:
    """사용 가능한 평가 모델을 반환합니다. 없으면 None."""
    from config import PROVIDER_API_KEYS

    for model_id in _EVAL_MODEL_CANDIDATES:
        provider = model_id.split('/')[0]
        api_key = PROVIDER_API_KEYS.get(provider, '')
        if api_key:
            return model_id
    return None


def _parse_quality_json(raw_text: str) -> Optional[Dict]:
    """LLM 응답에서 JSON을 파싱합니다. 코드 블록 제거 후 시도."""
    # ```json ... ``` 블록 제거
    text = re.sub(r'```json\s*', '', raw_text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()

    # JSON 객체 추출 시도
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # 전체 텍스트 직접 파싱
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _validate_quality_result(data: Dict) -> Dict:
    """파싱된 dict의 유효성을 검증하고 정규화합니다."""
    required_keys = {'accuracy', 'coherence', 'readability', 'usefulness', 'overall', 'grade', 'feedback'}

    # 누락 키 확인
    if not required_keys.issubset(data.keys()):
        raise ValueError(f"품질 평가 결과에 필수 키 누락: {required_keys - data.keys()}")

    # 점수 범위 검증 (1~10)
    for key in ('accuracy', 'coherence', 'readability', 'usefulness'):
        score = data[key]
        if not isinstance(score, (int, float)) or not (1 <= score <= 10):
            raise ValueError(f"점수 범위 오류: {key}={score}")

    # overall 재계산 (LLM 오류 보정)
    calculated_overall = round(
        (data['accuracy'] + data['coherence'] + data['readability'] + data['usefulness']) / 4, 1
    )
    data['overall'] = calculated_overall

    # 등급 재계산 (LLM 오류 보정)
    if calculated_overall >= 8.0:
        data['grade'] = 'A'
    elif calculated_overall >= 6.0:
        data['grade'] = 'B'
    elif calculated_overall >= 4.0:
        data['grade'] = 'C'
    else:
        data['grade'] = 'D'

    # feedback 문자열 확인
    if not isinstance(data.get('feedback'), str):
        data['feedback'] = '평가 피드백을 가져올 수 없습니다.'

    return data


def evaluate_quality(content: str, source_summary: str, model: Optional[str] = None) -> Dict:
    """
    LLM-as-judge 패턴으로 생성된 콘텐츠의 품질을 평가합니다.

    Args:
        content: 평가할 생성 콘텐츠 텍스트
        source_summary: 원본 자막 요약 (최초 500자 사용)
        model: 평가에 사용할 모델 ID (None이면 자동 선택)

    Returns:
        dict: {
            accuracy, coherence, readability, usefulness: int (1~10),
            overall: float,
            grade: str ("A"/"B"/"C"/"D"),
            feedback: str,
            eval_model: str (사용된 모델)
        }

    Raises:
        Exception: 평가 모델이 없거나 LLM 호출 실패 시
    """
    from prompts.quality_eval import QUALITY_EVAL_PROMPT
    from litellm import completion

    eval_model = model or _get_eval_model()
    if not eval_model:
        raise Exception("품질 평가에 사용 가능한 AI 모델이 없습니다. API 키를 확인해주세요.")

    # 자막 요약: 최초 500자로 제한
    truncated_summary = source_summary[:500] if source_summary else '(자막 요약 없음)'
    # 콘텐츠: 최초 3000자로 제한 (평가 비용 절감)
    truncated_content = content[:3000] if content else ''

    eval_prompt = QUALITY_EVAL_PROMPT.format(
        source_summary=truncated_summary,
        content=truncated_content,
    )

    # LiteLLM 호출 파라미터 구성
    kwargs = {
        "model": eval_model,
        "messages": [{"role": "user", "content": eval_prompt}],
        "temperature": 0.1,  # 평가 일관성을 위해 낮은 temperature
        "max_tokens": 512,
        "timeout": 60,
    }

    # GLM 모델 처리
    if eval_model.startswith("zhipuai/"):
        zhipuai_key = os.getenv("ZHIPUAI_API_KEY")
        if not zhipuai_key:
            raise ValueError("ZHIPUAI_API_KEY 환경변수가 설정되지 않았습니다.")
        kwargs["model"] = f"openai/{eval_model.replace('zhipuai/', '')}"
        kwargs["api_base"] = 'https://open.bigmodel.cn/api/paas/v4/'
        kwargs["api_key"] = zhipuai_key

    # Ollama 처리
    if eval_model.startswith("ollama_chat/") or eval_model.startswith("ollama/"):
        kwargs["api_base"] = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    try:
        response = completion(**kwargs)
        raw_text = response.choices[0].message.content

        parsed = _parse_quality_json(raw_text)
        if parsed is None:
            raise ValueError(f"품질 평가 JSON 파싱 실패. 원본 응답: {raw_text[:200]}")

        result = _validate_quality_result(parsed)
        result['eval_model'] = eval_model
        return result

    except Exception as e:
        current_app.logger.error(f"품질 평가 실패: eval_model={eval_model}, error={e}")
        raise


def should_regenerate(quality_result: Dict, threshold: str = "C") -> bool:
    """
    품질 등급이 기준 미달인지 확인합니다.

    Args:
        quality_result: evaluate_quality() 반환값
        threshold: 최소 허용 등급 ("A"/"B"/"C"/"D"). 기본값 "C"

    Returns:
        bool: 재생성 필요 시 True (등급 < threshold)
    """
    grade = quality_result.get('grade', 'D')
    threshold_order = _GRADE_ORDER.get(threshold, 1)
    grade_order = _GRADE_ORDER.get(grade, 0)
    return grade_order < threshold_order


def calculate_comprehensive_score(content: str) -> Dict:
    """콘텐츠 종합 점수를 로컬에서 계산합니다.

    AI 호출 없이 규칙 기반으로 SEO, 가독성, 독창성, 구조 점수를 산출합니다.

    Args:
        content: 평가할 콘텐츠 텍스트

    Returns:
        dict: {
            total_score: int (0~100),
            seo: int (0~100),
            readability: int (0~100),
            originality: int (0~100),
            structure: int (0~100),
            details: dict (항목별 세부 정보)
        }
    """
    if not content or not content.strip():
        return {
            "total_score": 0,
            "seo": 0, "readability": 0, "originality": 0, "structure": 0,
            "details": {"error": "콘텐츠가 비어있습니다."},
        }

    lines = content.split('\n')
    text_lines = [l for l in lines if l.strip()]
    char_count = len(content)
    word_count = len(content.split())

    # --- SEO 점수 (0~100) ---
    seo = 50  # 기본 50점
    headings = [l for l in text_lines if l.strip().startswith('#')]
    if headings:
        seo += min(20, len(headings) * 5)  # 소제목 있으면 가산
    if char_count >= 500:
        seo += 10
    if char_count >= 1500:
        seo += 10
    # 링크 포함 여부
    if re.search(r'\[.+?\]\(.+?\)', content) or re.search(r'https?://', content):
        seo += 10
    seo = min(100, seo)

    # --- 가독성 점수 (0~100) ---
    readability = 50
    # 평균 문단 길이 (짧을수록 좋음)
    paragraphs = [l for l in text_lines if not l.strip().startswith('#')]
    if paragraphs:
        avg_para_len = sum(len(p) for p in paragraphs) / len(paragraphs)
        if avg_para_len < 200:
            readability += 20
        elif avg_para_len < 400:
            readability += 10
    # 리스트 아이템 사용
    list_items = len([l for l in text_lines if re.match(r'^\s*[-*•\d]+[.)]\s', l.strip())])
    if list_items > 0:
        readability += min(15, list_items * 3)
    # 소제목으로 구조화
    if len(headings) >= 2:
        readability += 15
    readability = min(100, readability)

    # --- 독창성 점수 (0~100) ---
    # 규칙 기반 근사: 다양한 어휘 사용도 측정
    originality = 50
    words = re.findall(r'[가-힣]{2,}|[a-zA-Z]{3,}', content.lower())
    if words:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio > 0.6:
            originality += 25
        elif unique_ratio > 0.4:
            originality += 15
        elif unique_ratio > 0.3:
            originality += 5
    # 금지 표현 감점
    _CLICHE_WORDS = ['놀라운', '혁신적', '획기적', '최고의', '게임체인저', '압도적', '경이로운']
    cliche_count = sum(1 for w in _CLICHE_WORDS if w in content)
    originality -= cliche_count * 5
    originality = max(0, min(100, originality))

    # --- 구조 점수 (0~100) ---
    structure = 40  # 기본
    if len(headings) >= 1:
        structure += 15
    if len(headings) >= 3:
        structure += 10
    if list_items >= 2:
        structure += 10
    if char_count >= 300:
        structure += 10
    # 서론-본론-결론 패턴 (소제목 3개 이상)
    if len(headings) >= 3:
        structure += 15
    structure = min(100, structure)

    total = round((seo + readability + originality + structure) / 4)

    return {
        "total_score": total,
        "seo": seo,
        "readability": readability,
        "originality": originality,
        "structure": structure,
        "details": {
            "char_count": char_count,
            "word_count": word_count,
            "heading_count": len(headings),
            "list_items": list_items,
        },
    }


def auto_regenerate(
    content_fn,
    source_summary: str,
    quality_threshold: str = "C",
    max_retries: int = 1,
    eval_model: Optional[str] = None,
) -> Tuple[Dict, Dict]:
    """
    기준 미달 시 콘텐츠를 재생성합니다. 최대 1회 재시도.

    Args:
        content_fn: 콘텐츠 생성 함수. 호출 시 (result_dict, used_prompt) 반환
                   선택적으로 temperature 오버라이드를 위해 temperature 파라미터를 받을 수 있음
        source_summary: 원본 자막 요약 (품질 평가용)
        quality_threshold: 최소 허용 등급 ("A"/"B"/"C"/"D")
        max_retries: 최대 재시도 횟수 (비용 폭발 방지, 기본값 1)
        eval_model: 평가 모델 (None이면 자동 선택)

    Returns:
        tuple: (best_result, quality_result)
            - best_result: 최고 품질의 생성 결과 dict
            - quality_result: 해당 결과의 품질 평가 dict
    """
    best_result = None
    best_quality = None

    for attempt in range(max_retries + 1):
        try:
            result, _ = content_fn()
            content = result.get('content', '')

            quality = evaluate_quality(content, source_summary, eval_model)

            # 첫 시도 또는 더 높은 등급이면 업데이트
            if best_quality is None or _GRADE_ORDER.get(quality['grade'], 0) > _GRADE_ORDER.get(best_quality['grade'], 0):
                best_result = result
                best_quality = quality

            # 기준 충족 시 즉시 반환
            if not should_regenerate(quality, quality_threshold):
                current_app.logger.info(f"품질 기준 충족: grade={quality['grade']}, attempt={attempt + 1}")
                break

            if attempt < max_retries:
                current_app.logger.info(
                    f"품질 기준 미달 (grade={quality['grade']}), 재시도 {attempt + 1}/{max_retries}"
                )

        except Exception as e:
            current_app.logger.warning(f"auto_regenerate 시도 {attempt + 1} 실패: {e}")
            # 품질 평가 실패 시 마지막 생성 결과라도 반환
            if best_result is None and 'result' in locals():
                best_result = result
            break

    if best_result is None:
        raise Exception("자동 재생성: 콘텐츠 생성에 실패했습니다.")

    return best_result, best_quality
