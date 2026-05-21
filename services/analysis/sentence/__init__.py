"""문장 분석 서브패키지 — 8개 규칙 기반 분석기.

각 분석기는 독립적으로 사용 가능. 모두 AI API 호출 없음.
"""
from services.analysis.sentence.variety import analyze_variety
from services.analysis.sentence.connector_variety import analyze_connector_variety
from services.analysis.sentence.rhythm import analyze_sentence_rhythm
from services.analysis.sentence.ending_variety import analyze_sentence_ending_variety
from services.analysis.sentence.avg_words import analyze_avg_words_per_sentence
from services.analysis.sentence.complexity import score_sentence_complexity
from services.analysis.sentence.starter_diversity import analyze_sentence_starter_diversity
from services.analysis.sentence.topic_alignment import analyze_topic_sentence_alignment

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
