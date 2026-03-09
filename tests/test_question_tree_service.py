"""
질문 트리 서비스 테스트
"""
import pytest
from services.question_tree_service import (
    expand_question_tree,
    QuestionTree,
    QuestionNode,
    _detect_language,
    _extract_key_phrases,
    _extract_sentences,
    _find_hint_for_topic,
    _generate_questions_for_topic,
)


class TestDetectLanguage:
    """언어 감지 테스트"""

    def test_korean_text(self):
        text = "인공지능은 현대 기술의 핵심입니다"
        assert _detect_language(text) == 'ko'

    def test_english_text(self):
        text = "Artificial intelligence is a key technology"
        assert _detect_language(text) == 'en'

    def test_mixed_text_korean_dominant(self):
        text = "머신러닝과 딥러닝은 AI의 핵심 기술이며 중요합니다"
        assert _detect_language(text) == 'ko'

    def test_empty_text(self):
        # 한글/영어 모두 0이면 ko 반환 (ko_chars >= en_chars → 0 >= 0 = True)
        assert _detect_language("") == 'ko'


class TestExtractSentences:
    """문장 분리 테스트"""

    def test_period_separated(self):
        text = "첫 번째 문장입니다. 두 번째 문장입니다. 세 번째 문장입니다."
        sentences = _extract_sentences(text)
        assert len(sentences) == 3

    def test_newline_separated(self):
        text = "첫 번째 문장입니다\n두 번째 문장입니다\n세 번째 문장입니다"
        sentences = _extract_sentences(text)
        assert len(sentences) == 3

    def test_short_sentences_filtered(self):
        text = "좋다. 인공지능은 매우 중요한 기술입니다."
        sentences = _extract_sentences(text)
        # "좋다" (3자)는 5자 미만이므로 필터링됨
        assert len(sentences) == 1
        assert '인공지능' in sentences[0]

    def test_empty_text(self):
        assert _extract_sentences("") == []


class TestExtractKeyPhrases:
    """핵심 구문 추출 테스트"""

    def test_korean_phrases(self):
        text = "인공지능 기술은 머신러닝과 딥러닝을 포함합니다. 인공지능은 매우 중요합니다."
        phrases = _extract_key_phrases(text, 'ko', max_phrases=3)
        assert len(phrases) > 0
        # '인공지능'이 2번 등장하므로 상위에 위치해야 함
        assert '인공지능' in phrases

    def test_english_phrases(self):
        text = "Machine learning is important. Machine learning uses data. Deep learning extends machine learning."
        phrases = _extract_key_phrases(text, 'en', max_phrases=3)
        assert len(phrases) > 0
        assert 'machine' in phrases or 'learning' in phrases

    def test_stopwords_filtered(self):
        text = "그리고 그래서 따라서 때문에"
        phrases = _extract_key_phrases(text, 'ko', max_phrases=5)
        assert len(phrases) == 0

    def test_empty_text(self):
        assert _extract_key_phrases("", 'ko') == []


class TestFindHintForTopic:
    """답변 힌트 추출 테스트"""

    def test_hint_found(self):
        sentences = ["인공지능은 현대 기술의 핵심입니다.", "데이터 분석이 중요합니다."]
        hint = _find_hint_for_topic(sentences, "인공지능")
        assert "인공지능" in hint

    def test_hint_not_found(self):
        sentences = ["데이터 분석이 중요합니다."]
        hint = _find_hint_for_topic(sentences, "블록체인")
        assert hint == ""

    def test_long_hint_truncated(self):
        long_sentence = "인공지능은 " + "매우 " * 50 + "중요한 기술입니다."
        sentences = [long_sentence]
        hint = _find_hint_for_topic(sentences, "인공지능")
        assert len(hint) <= 104  # 100자 + '...'(3자) + 여유


class TestGenerateQuestions:
    """질문 생성 테스트"""

    def test_korean_why_question(self):
        q = _generate_questions_for_topic("인공지능", 'ko', 'why')
        assert '인공지능' in q
        assert any(w in q for w in ['왜', '이유', '필요'])

    def test_korean_how_question(self):
        q = _generate_questions_for_topic("데이터분석", 'ko', 'how')
        assert '데이터분석' in q
        assert any(w in q for w in ['어떻게', '원리', '개선'])

    def test_korean_what_question(self):
        q = _generate_questions_for_topic("머신러닝", 'ko', 'what')
        assert '머신러닝' in q
        assert any(w in q for w in ['무엇', '핵심', '장단점', '개념'])

    def test_english_question(self):
        q = _generate_questions_for_topic("AI", 'en', 'why')
        assert 'AI' in q

    def test_invalid_category_fallback(self):
        # 유효하지 않은 카테고리 → 'what'으로 폴백
        q = _generate_questions_for_topic("테스트", 'ko', 'invalid_category')
        assert '테스트' in q


class TestExpandQuestionTree:
    """질문 트리 확장 통합 테스트"""

    def test_basic_expansion(self):
        content = """
        인공지능은 현대 기술의 핵심입니다. 머신러닝과 딥러닝은 인공지능의 하위 분야입니다.
        데이터 분석은 인공지능 활용의 기본입니다. 자연어 처리는 텍스트를 이해하는 기술입니다.
        컴퓨터 비전은 이미지를 분석합니다.
        """
        tree = expand_question_tree(content, depth=2)

        assert isinstance(tree, QuestionTree)
        assert tree.root_topic != ""
        assert len(tree.nodes) > 0
        assert tree.total_questions > 0
        assert tree.depth >= 1

    def test_empty_content(self):
        tree = expand_question_tree("")
        assert tree.root_topic == ""
        assert tree.nodes == []
        assert tree.total_questions == 0
        assert tree.depth == 0

    def test_whitespace_only(self):
        tree = expand_question_tree("   \n\t  ")
        assert tree.root_topic == ""
        assert tree.total_questions == 0

    def test_depth_1(self):
        content = "인공지능 기술은 다양한 분야에서 활용됩니다. 머신러닝은 데이터에서 패턴을 학습합니다."
        tree = expand_question_tree(content, depth=1)
        assert tree.depth == 1
        # depth=1이면 재귀 확장 없음
        for node in tree.nodes:
            assert node.level == 0

    def test_depth_clamped_to_max(self):
        content = "인공지능 기술 설명. 딥러닝 기술 설명."
        tree = expand_question_tree(content, depth=10)
        # depth는 5로 클램핑됨
        assert tree.depth <= 5

    def test_depth_clamped_to_min(self):
        content = "인공지능 기술 설명. 딥러닝 기술 설명."
        tree = expand_question_tree(content, depth=0)
        # depth는 1로 클램핑됨
        assert tree.depth >= 1

    def test_english_content(self):
        content = """
        Machine learning is a subset of artificial intelligence.
        Deep learning uses neural networks for complex tasks.
        Natural language processing handles text understanding.
        Computer vision analyzes images and videos.
        """
        tree = expand_question_tree(content, depth=2)

        assert tree.root_topic != ""
        assert len(tree.nodes) > 0

    def test_node_structure(self):
        content = "인공지능 기술은 중요합니다. 데이터 분석은 핵심입니다. 머신러닝을 활용합니다."
        tree = expand_question_tree(content, depth=2)

        for node in tree.nodes:
            assert isinstance(node, QuestionNode)
            assert isinstance(node.question, str)
            assert node.question != ""
            assert isinstance(node.level, int)
            assert node.level >= 0
            assert isinstance(node.children, list)

    def test_parent_child_relationship(self):
        content = "인공지능 기술의 발전과 응용. 딥러닝과 머신러닝의 차이점. 데이터 과학의 중요성."
        tree = expand_question_tree(content, depth=3)

        # 레벨 0 노드는 parent_question이 None
        level_0_nodes = [n for n in tree.nodes if n.level == 0]
        for node in level_0_nodes:
            assert node.parent_question is None

        # 레벨 1+ 노드는 parent_question이 있어야 함
        deeper_nodes = [n for n in tree.nodes if n.level > 0]
        for node in deeper_nodes:
            assert node.parent_question is not None

    def test_total_questions_count(self):
        content = "인공지능과 머신러닝 기술. 딥러닝 알고리즘의 원리."
        tree = expand_question_tree(content, depth=2)

        # total_questions = 노드 수 + 자식 질문 수
        expected = len(tree.nodes) + sum(len(n.children) for n in tree.nodes)
        assert tree.total_questions == expected

    def test_very_short_content(self):
        # 키워드 추출 불가능할 수 있는 매우 짧은 텍스트
        tree = expand_question_tree("짧은")
        # 결과가 빈 트리이거나 유효한 트리여야 함
        assert isinstance(tree, QuestionTree)

    def test_children_are_strings(self):
        content = "인공지능 기술은 발전하고 있습니다. 머신러닝 활용 사례가 늘어나고 있습니다."
        tree = expand_question_tree(content, depth=2)

        for node in tree.nodes:
            for child in node.children:
                assert isinstance(child, str)
                assert len(child) > 0
