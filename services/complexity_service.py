"""
콘텐츠 복잡도 분석 서비스 (F10-18)
텍스트의 가독성, 전문성 수준, 구조 복잡도를 정량 분석
"""
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# 전문 용어 사전 (도메인별)
_TECH_TERMS = {
    'ai': ['딥러닝', '신경망', 'LLM', '파인튜닝', 'RAG', 'GPT', '임베딩', '트랜스포머'],
    'finance': ['포트폴리오', '유동성', '파생상품', '레버리지', 'ETF', '리밸런싱'],
    'medical': ['염증', '대사', '면역', '항체', '전이', '병변', '진단'],
    'programming': ['알고리즘', '복잡도', '비동기', '동시성', '아키텍처', '인터페이스'],
}


@dataclass
class ComplexityReport:
    """복잡도 분석 리포트"""
    # 가독성 지표
    avg_sentence_length: float      # 평균 문장 길이 (자)
    avg_word_length: float          # 평균 단어 길이
    paragraph_count: int            # 문단 수
    sentence_count: int             # 문장 수

    # 구조 지표
    heading_depth: int              # 최대 헤딩 깊이 (h1~h6)
    list_count: int                 # 목록 항목 수
    code_block_count: int           # 코드 블록 수

    # 전문성 지표
    technical_term_count: int       # 전문 용어 수
    domain_detected: str            # 감지된 도메인

    # 종합 점수 (0~100)
    readability_score: float        # 가독성 점수 (높을수록 읽기 쉬움)
    complexity_score: float         # 복잡도 점수 (높을수록 복잡)
    expertise_level: str            # 전문성 수준 (beginner/intermediate/expert)

    def to_dict(self) -> Dict[str, Any]:
        """분석 결과를 딕셔너리로 변환"""
        return {
            'readability_score': round(self.readability_score, 1),
            'complexity_score': round(self.complexity_score, 1),
            'expertise_level': self.expertise_level,
            'avg_sentence_length': round(self.avg_sentence_length, 1),
            'paragraph_count': self.paragraph_count,
            'sentence_count': self.sentence_count,
            'heading_depth': self.heading_depth,
            'technical_term_count': self.technical_term_count,
            'domain_detected': self.domain_detected,
            'suggestions': self._get_suggestions(),
        }

    def _get_suggestions(self) -> List[str]:
        suggestions = []
        if self.avg_sentence_length > 150:
            suggestions.append("문장이 너무 깁니다. 80~120자 내외로 분리하세요.")
        if self.avg_sentence_length < 30:
            suggestions.append("문장이 너무 짧습니다. 내용을 더 풍부하게 작성하세요.")
        if self.paragraph_count < 3:
            suggestions.append("문단 구분이 부족합니다. 더 세분화하세요.")
        if self.heading_depth == 0 and self.sentence_count > 10:
            suggestions.append("헤딩이 없습니다. 섹션 구조를 추가하면 가독성이 향상됩니다.")
        if self.complexity_score > 80:
            suggestions.append("콘텐츠가 매우 복잡합니다. 초보자를 위한 설명을 추가하세요.")
        return suggestions


class ComplexityService:
    """콘텐츠 복잡도 분석 서비스"""

    def analyze(self, content: str) -> ComplexityReport:
        """
        콘텐츠 복잡도 종합 분석

        Args:
            content: 분석할 마크다운 텍스트

        Returns:
            ComplexityReport
        """
        if not content or not content.strip():
            return ComplexityReport(
                avg_sentence_length=0, avg_word_length=0,
                paragraph_count=0, sentence_count=0,
                heading_depth=0, list_count=0, code_block_count=0,
                technical_term_count=0, domain_detected='unknown',
                readability_score=0, complexity_score=0, expertise_level='beginner'
            )

        # 마크다운 정제 (분석용 평문)
        plain = self._strip_markdown(content)

        # 구조 분석
        paragraphs = [p for p in content.split('\n\n') if p.strip()]
        sentences = self._split_sentences(plain)
        words = plain.split()

        avg_sentence_len = sum(len(s) for s in sentences) / max(1, len(sentences))
        avg_word_len = sum(len(w) for w in words) / max(1, len(words))

        # 마크다운 구조
        headings = re.findall(r'^(#{1,6})\s', content, re.MULTILINE)
        heading_depth = max((len(h) for h in headings), default=0)
        list_items = len(re.findall(r'^[-*+]\s', content, re.MULTILINE))
        code_blocks = len(re.findall(r'```', content)) // 2

        # 전문 용어
        tech_count, domain = self._count_tech_terms(content)

        # 가독성 점수 계산 (한국어 Flesch 변형)
        readability = self._korean_readability(avg_sentence_len, avg_word_len)

        # 복잡도 점수 (0~100)
        complexity = min(100, (
            max(0, avg_sentence_len - 50) * 0.3 +
            heading_depth * 3 +
            tech_count * 2 +
            code_blocks * 5 +
            max(0, len(paragraphs) - 5) * 2
        ))

        # 전문성 수준
        if tech_count >= 10 or avg_sentence_len >= 120:
            expertise = 'expert'
        elif tech_count >= 5 or avg_sentence_len >= 80:
            expertise = 'intermediate'
        else:
            expertise = 'beginner'

        return ComplexityReport(
            avg_sentence_length=avg_sentence_len,
            avg_word_length=avg_word_len,
            paragraph_count=len(paragraphs),
            sentence_count=len(sentences),
            heading_depth=heading_depth,
            list_count=list_items,
            code_block_count=code_blocks,
            technical_term_count=tech_count,
            domain_detected=domain,
            readability_score=readability,
            complexity_score=complexity,
            expertise_level=expertise,
        )

    def _strip_markdown(self, text: str) -> str:
        """마크다운 기호 제거 (분석용 평문 변환)"""
        text = re.sub(r'```[\s\S]*?```', '', text)
        text = re.sub(r'`[^`]+`', '', text)
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'\*{1,3}([^\*]+)\*{1,3}', r'\1', text)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        text = re.sub(r'^[-*+]\s+', '', text, flags=re.MULTILINE)
        return text

    def _split_sentences(self, text: str) -> List[str]:
        """문장 분리"""
        separators = re.compile(r'[.!?。]\s+')
        sentences = separators.split(text)
        return [s.strip() for s in sentences if len(s.strip()) > 10]

    def _count_tech_terms(self, content: str) -> tuple:
        """전문 용어 수 및 도메인 감지"""
        domain_counts = {}
        for domain, terms in _TECH_TERMS.items():
            count = sum(content.count(term) for term in terms)
            domain_counts[domain] = count

        max_domain = max(domain_counts, key=domain_counts.get, default='unknown')
        total = sum(domain_counts.values())
        detected = max_domain if domain_counts.get(max_domain, 0) > 0 else 'general'
        return total, detected

    def _korean_readability(self, avg_sentence_len: float, avg_word_len: float) -> float:
        """한국어 가독성 점수 (0~100, 높을수록 읽기 쉬움)"""
        # 최적: 문장 50~80자, 단어 3~5자
        sentence_penalty = max(0, (avg_sentence_len - 80) / 200) * 50
        word_penalty = max(0, (avg_word_len - 5) / 10) * 20
        score = max(0, 100 - sentence_penalty - word_penalty)
        return round(score, 1)
