"""
프롬프트 품질 정적 평가 스크립트 (Frozen Metric)
AI 호출 없이 프롬프트 텍스트 자체를 분석하여 점수를 매긴다.

3가지 메트릭:
  1. 구조 점수 (40%) — 역할, 출력 형식, CoT, Few-shot
  2. 금칙어 점수 (30%) — 금칙어 포함 여부, 댓글 방지 규칙
  3. 명확성 점수 (30%) — 구체적 지시, 길이/톤/형식/언어 명시
"""

import re
import sys
import os

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from prompts.styles import STYLE_PROMPTS
from prompts.base import FORBIDDEN_EXPRESSIONS, BASE_PROMPT

# ── 금칙어 리스트 ──
FORBIDDEN_WORDS = [
    "놀라운", "혁신적", "획기적", "최고의", "게임체인저",
    "압도적", "경이로운", "드디어", "탁월한", "인상적",
    "뛰어난", "강력한"
]

# 내부 전용 프롬프트 (평가에서 제외)
INTERNAL_ONLY = {"mindmap", "chapter_split", "cited_summary", "comment_summary"}


def score_structure(prompt_text: str) -> dict:
    """구조 점수 (40점 만점)"""
    scores = {}

    # 1. 역할 정의 (10점)
    role_patterns = [r"# 역할", r"## 이 스타일의 목표", r"역할:", r"당신은.*전문가", r"당신은.*입니다"]
    has_role = any(re.search(p, prompt_text) for p in role_patterns)
    scores["역할 정의"] = 10 if has_role else 0

    # 2. 출력 형식 명시 (10점)
    format_patterns = [r"# 출력 형식", r"## 출력 형식", r"출력 형식", r"출력.*형식"]
    has_format = any(re.search(p, prompt_text) for p in format_patterns)
    scores["출력 형식"] = 10 if has_format else 0

    # 3. Chain-of-Thought 단계 (10점)
    cot_patterns = [r"작성 순서", r"단계별", r"Step \d", r"순서.*준수", r"\d\.\s.*→", r"작성 가이드"]
    has_cot = any(re.search(p, prompt_text) for p in cot_patterns)
    scores["CoT 단계"] = 10 if has_cot else 0

    # 4. Few-shot 예시 (10점)
    example_patterns = [r"좋은 예시", r"참고용", r"예시.*시작", r"```\n.*\n```"]
    has_example = any(re.search(p, prompt_text, re.DOTALL) for p in example_patterns)
    scores["Few-shot 예시"] = 10 if has_example else 0

    return scores


def score_forbidden(prompt_text: str) -> dict:
    """금칙어 점수 (30점 만점)"""
    scores = {}

    # 1. 금칙어 자체 미포함 (15점) — 예시/금지 목록 내의 언급은 허용
    # 금지 목록 안의 언급을 제외한 본문에서 금칙어 검색
    # "금지" 섹션 외부에서 금칙어가 사용되는지 체크
    found_forbidden = []
    lines = prompt_text.split('\n')
    in_forbidden_section = False
    in_example_section = False
    for line in lines:
        if re.search(r"금지.*표현|절대.*금지|금지 표현", line):
            in_forbidden_section = True
            continue
        if re.search(r"좋은 예시|참고용|```", line):
            in_example_section = not in_example_section if "```" in line else True
            continue
        if in_forbidden_section and (line.strip() == "" or line.startswith("#")):
            in_forbidden_section = False
        if not in_forbidden_section and not in_example_section:
            for word in FORBIDDEN_WORDS:
                if word in line:
                    found_forbidden.append(word)

    scores["금칙어 미사용"] = 15 if len(found_forbidden) == 0 else max(0, 15 - len(found_forbidden) * 3)

    # 2. 댓글 방지 규칙 명시 (15점)
    comment_patterns = [
        r"댓글.*없으면.*언급.*금지",
        r"댓글.*없으면.*절대.*언급",
        r"\[댓글\].*섹션.*없.*때",
        r"댓글.*규칙",
        r"시청자 반응.*절대.*언급",
    ]
    has_comment_rule = any(re.search(p, prompt_text) for p in comment_patterns)
    # base.py에 이미 포함되어 있으므로, 스타일에도 명시했으면 보너스
    scores["댓글 방지 규칙"] = 15 if has_comment_rule else 8  # base에 있으니 기본 8점

    return scores


def score_clarity(prompt_text: str) -> dict:
    """명확성 점수 (30점 만점)"""
    scores = {}

    # 1. 구체적 지시 (10점) — 모호한 "잘", "좋게" 대신 구체적 수치/행동
    specific_patterns = [
        r"\d+자", r"\d+개", r"\d+줄", r"\d+문장",
        r"\d+~\d+", r"이내", r"이상", r"이하",
        r"H2|H3|##|###",
    ]
    specificity_count = sum(1 for p in specific_patterns if re.search(p, prompt_text))
    scores["구체적 지시"] = min(10, specificity_count * 2)

    # 2. 길이/톤/형식 명시 (10점)
    length_tone = 0
    if re.search(r"글 길이|자 이내|자 이상|\d+자|\d+줄", prompt_text):
        length_tone += 3
    if re.search(r"톤|문체|~요|~해요|대화체|구어체|객관|분석", prompt_text):
        length_tone += 4
    if re.search(r"마크다운|HTML|JSON|형식|포맷|출력", prompt_text):
        length_tone += 3
    scores["길이/톤/형식"] = min(10, length_tone)

    # 3. 출력 언어 명시 (10점)
    lang_patterns = [r"한국어", r"ko|en|ja", r"언어.*명시", r"작성.*언어"]
    has_lang = any(re.search(p, prompt_text) for p in lang_patterns)
    # base.py에서 한국어가 기본이므로 스타일에 없어도 기본 5점
    scores["출력 언어"] = 10 if has_lang else 5

    return scores


def evaluate_all() -> list[dict]:
    """모든 스타일 프롬프트를 평가하고 결과를 반환"""
    results = []

    for style_id, prompt_text in STYLE_PROMPTS.items():
        if style_id in INTERNAL_ONLY:
            continue

        struct = score_structure(prompt_text)
        forbidden = score_forbidden(prompt_text)
        clarity = score_clarity(prompt_text)

        struct_total = sum(struct.values())
        forbidden_total = sum(forbidden.values())
        clarity_total = sum(clarity.values())
        total = struct_total + forbidden_total + clarity_total

        results.append({
            "style_id": style_id,
            "structure": struct,
            "structure_total": struct_total,
            "forbidden": forbidden,
            "forbidden_total": forbidden_total,
            "clarity": clarity,
            "clarity_total": clarity_total,
            "total": total,
        })

    # 총점 오름차순 정렬 (낮은 점수 → 개선 우선)
    results.sort(key=lambda r: r["total"])
    return results


def print_results(results: list[dict]):
    """결과를 TSV + 콘솔 출력"""
    print(f"\n{'='*70}")
    print(f"프롬프트 품질 평가 결과 (Frozen Metric)")
    print(f"{'='*70}\n")

    header = f"{'스타일':<20} {'구조(40)':<10} {'금칙어(30)':<12} {'명확성(30)':<12} {'총점(100)':<10}"
    print(header)
    print("-" * 70)

    for r in results:
        line = f"{r['style_id']:<20} {r['structure_total']:<10} {r['forbidden_total']:<12} {r['clarity_total']:<12} {r['total']:<10}"
        print(line)

    print(f"\n{'='*70}")
    print("개선 우선순위 (낮은 점수 순):")
    for i, r in enumerate(results[:5], 1):
        details = []
        if r["structure_total"] < 40:
            missing = [k for k, v in r["structure"].items() if v == 0]
            if missing:
                details.append(f"구조 누락: {', '.join(missing)}")
        if r["forbidden_total"] < 30:
            missing = [k for k, v in r["forbidden"].items() if v < 15]
            if missing:
                details.append(f"금칙어 부족: {', '.join(missing)}")
        if r["clarity_total"] < 30:
            missing = [k for k, v in r["clarity"].items() if v < 10]
            if missing:
                details.append(f"명확성 부족: {', '.join(missing)}")
        detail_str = " | ".join(details) if details else "양호"
        print(f"  {i}. {r['style_id']} ({r['total']}점) - {detail_str}")


def save_tsv(results: list[dict], filepath: str):
    """결과를 TSV 파일로 저장"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("style_id\tstructure\tforbidden\tclarity\ttotal\tdetails\n")
        for r in results:
            struct_detail = "|".join(f"{k}={v}" for k, v in r["structure"].items())
            forbidden_detail = "|".join(f"{k}={v}" for k, v in r["forbidden"].items())
            clarity_detail = "|".join(f"{k}={v}" for k, v in r["clarity"].items())
            details = f"S:[{struct_detail}] F:[{forbidden_detail}] C:[{clarity_detail}]"
            f.write(f"{r['style_id']}\t{r['structure_total']}\t{r['forbidden_total']}\t{r['clarity_total']}\t{r['total']}\t{details}\n")


if __name__ == "__main__":
    results = evaluate_all()
    print_results(results)

    tsv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompt_results.tsv")
    save_tsv(results, tsv_path)
    print(f"\n결과 저장: {tsv_path}")
