"""
문장 분석 통합 진입점 (얇은 re-export shim).

실제 구현은 services/analysis/sentence/ 서브패키지에 모듈별로 분리되어 있다.
기존 import 경로 호환을 위해 이 모듈에서 8개 함수를 다시 export한다.

8개 개별 분석기:
- analyze_variety (문장 다양성) — services/analysis/sentence/variety.py
- analyze_connector_variety (연결어 다양성) — services/analysis/sentence/connector_variety.py
- analyze_sentence_rhythm (문장 리듬) — services/analysis/sentence/rhythm.py
- analyze_sentence_ending_variety (종결어미 다양성) — services/analysis/sentence/ending_variety.py
- analyze_avg_words_per_sentence (문장당 평균 단어 수) — services/analysis/sentence/avg_words.py
- score_sentence_complexity (문장 복잡도) — services/analysis/sentence/complexity.py
- analyze_sentence_starter_diversity (시작어 다양성) — services/analysis/sentence/starter_diversity.py
- analyze_topic_sentence_alignment (주제문 정렬) — services/analysis/sentence/topic_alignment.py
"""
from services.analysis.sentence import (
    analyze_variety,
    analyze_connector_variety,
    analyze_sentence_rhythm,
    analyze_sentence_ending_variety,
    analyze_avg_words_per_sentence,
    score_sentence_complexity,
    analyze_sentence_starter_diversity,
    analyze_topic_sentence_alignment,
)

__all__ = [
    'analyze_variety',
    'analyze_connector_variety',
    'analyze_sentence_rhythm',
    'analyze_sentence_ending_variety',
    'analyze_avg_words_per_sentence',
    'score_sentence_complexity',
    'analyze_sentence_starter_diversity',
    'analyze_topic_sentence_alignment',
]
