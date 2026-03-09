"""문서 AI 리스타일 Import + 답변 블록 컴파일러 테스트"""
import pytest
from services.restyle_import_service import (
    ContentCard,
    RestyledContent,
    AnswerBlock,
    restyle_document,
    compile_answer_blocks,
    export_blocks,
    merge_short_cards,
)


class TestRestyleDocumentBasic:
    """기본 텍스트 카드 분해 테스트"""

    def test_restyle_document_basic(self):
        """일반 텍스트가 text 카드로 분해된다"""
        text = "첫 번째 문단입니다.\n\n두 번째 문단입니다."
        result = restyle_document(text)

        assert isinstance(result, RestyledContent)
        assert result.original_length == len(text)
        assert result.layout == 'card'
        assert len(result.cards) == 2
        assert result.cards[0].card_type == 'text'
        assert result.cards[0].content == '첫 번째 문단입니다.'
        assert result.cards[1].card_type == 'text'
        assert result.cards[1].content == '두 번째 문단입니다.'

    def test_restyle_document_order(self):
        """카드 순서(order)가 0부터 증가한다"""
        text = "A\nB\nC"
        result = restyle_document(text)
        orders = [c.order for c in result.cards]
        assert orders == [0, 1, 2]


class TestRestyleDocumentMarkdown:
    """마크다운 헤딩 감지 테스트"""

    def test_heading_h1(self):
        """# 헤딩이 heading 카드로 변환된다"""
        text = "# 제목입니다"
        result = restyle_document(text)
        assert len(result.cards) == 1
        assert result.cards[0].card_type == 'heading'
        assert result.cards[0].title == '제목입니다'

    def test_heading_h2(self):
        """## 헤딩도 감지된다"""
        text = "## 소제목"
        result = restyle_document(text)
        assert result.cards[0].card_type == 'heading'
        assert result.cards[0].title == '소제목'

    def test_heading_with_body(self):
        """헤딩과 본문이 함께 있을 때 각각 분리된다"""
        text = "# 제목\n본문 내용입니다."
        result = restyle_document(text)
        assert len(result.cards) == 2
        assert result.cards[0].card_type == 'heading'
        assert result.cards[1].card_type == 'text'


class TestRestyleDocumentList:
    """목록 항목 인식 테스트"""

    def test_unordered_list_dash(self):
        """- 로 시작하는 줄이 list 카드로 인식된다"""
        text = "- 항목1\n- 항목2\n- 항목3"
        result = restyle_document(text)
        assert len(result.cards) == 1
        assert result.cards[0].card_type == 'list'
        assert '항목1' in result.cards[0].content
        assert '항목3' in result.cards[0].content

    def test_unordered_list_asterisk(self):
        """* 로 시작하는 줄도 list 카드로 인식된다"""
        text = "* 사과\n* 바나나"
        result = restyle_document(text)
        assert result.cards[0].card_type == 'list'

    def test_ordered_list(self):
        """숫자. 으로 시작하는 줄이 list 카드로 인식된다"""
        text = "1. 첫째\n2. 둘째\n3. 셋째"
        result = restyle_document(text)
        assert result.cards[0].card_type == 'list'
        assert '첫째' in result.cards[0].content

    def test_list_separated_by_blank_line(self):
        """빈 줄로 분리된 목록은 별도 카드가 된다"""
        text = "- 그룹1 항목\n\n- 그룹2 항목"
        result = restyle_document(text)
        assert len(result.cards) == 2
        assert all(c.card_type == 'list' for c in result.cards)


class TestRestyleDocumentQuote:
    """인용문 인식 테스트"""

    def test_quote(self):
        """> 로 시작하는 줄이 quote 카드로 인식된다"""
        text = "> 인용문입니다."
        result = restyle_document(text)
        assert len(result.cards) == 1
        assert result.cards[0].card_type == 'quote'
        assert result.cards[0].content == '인용문입니다.'


class TestRestyleDocumentEmpty:
    """빈 텍스트 처리 테스트"""

    def test_empty_string(self):
        """빈 문자열은 빈 카드 목록을 반환한다"""
        result = restyle_document('')
        assert result.original_length == 0
        assert result.cards == []

    def test_whitespace_only(self):
        """공백만 있는 텍스트도 빈 결과를 반환한다"""
        result = restyle_document('   \n\n  ')
        assert result.cards == []

    def test_none_like(self):
        """None이 아닌 빈 문자열 처리"""
        result = restyle_document('')
        assert isinstance(result, RestyledContent)


class TestRestyleDocumentLayout:
    """레이아웃 옵션 테스트"""

    def test_default_layout(self):
        """기본 레이아웃은 card이다"""
        result = restyle_document('텍스트')
        assert result.layout == 'card'

    def test_timeline_layout(self):
        """timeline 레이아웃이 설정된다"""
        result = restyle_document('텍스트', layout='timeline')
        assert result.layout == 'timeline'

    def test_grid_layout(self):
        """grid 레이아웃이 설정된다"""
        result = restyle_document('텍스트', layout='grid')
        assert result.layout == 'grid'


class TestCompileAnswerBlocksWithQuestions:
    """질문형 문장 추출 테스트"""

    def test_question_with_answer(self):
        """물음표가 있는 문장이 질문으로 추출된다"""
        content = "파이썬이란 무엇인가? 파이썬은 범용 프로그래밍 언어입니다."
        blocks = compile_answer_blocks(content)
        assert len(blocks) == 1
        assert blocks[0].question == '파이썬이란 무엇인가?'
        assert '프로그래밍 언어' in blocks[0].answer

    def test_korean_question_word(self):
        """한국어 의문사(무엇, 어떻게 등)로 시작하는 문장이 질문으로 추출된다"""
        content = "어떻게 사용하나요? 설치 후 실행하면 됩니다."
        blocks = compile_answer_blocks(content)
        assert blocks[0].question == '어떻게 사용하나요?'

    def test_multiple_paragraphs(self):
        """여러 문단이 각각 별도 블록으로 변환된다"""
        content = "첫 질문? 첫 답변.\n\n두 번째 질문? 두 번째 답변."
        blocks = compile_answer_blocks(content)
        assert len(blocks) == 2
        assert blocks[0].source_paragraph == 0
        assert blocks[1].source_paragraph == 1


class TestCompileAnswerBlocksNoQuestions:
    """질문 없는 텍스트 처리 테스트"""

    def test_no_question_converts_first_sentence(self):
        """질문이 없으면 첫 문장이 질문으로 변환된다"""
        content = "프로그래밍은 중요합니다. 다양한 분야에서 활용됩니다."
        blocks = compile_answer_blocks(content)
        assert len(blocks) == 1
        # 첫 문장이 물음표로 끝나도록 변환됨
        assert blocks[0].question.endswith('?')
        assert '프로그래밍' in blocks[0].question

    def test_single_sentence_paragraph(self):
        """문장이 하나뿐인 문단도 블록으로 변환된다"""
        content = "단일 문장입니다."
        blocks = compile_answer_blocks(content)
        assert len(blocks) == 1
        assert blocks[0].question.endswith('?')


class TestCompileAnswerBlocksWordCount:
    """단어수 계산 테스트"""

    def test_word_count(self):
        """답변의 단어수가 정확히 계산된다"""
        content = "질문입니다? 하나 둘 셋 넷 다섯."
        blocks = compile_answer_blocks(content)
        assert blocks[0].word_count == 5  # "하나 둘 셋 넷 다섯."


class TestCompileAnswerBlocksEmpty:
    """빈 콘텐츠 처리 테스트"""

    def test_empty_string(self):
        """빈 문자열은 빈 리스트를 반환한다"""
        assert compile_answer_blocks('') == []

    def test_whitespace_only(self):
        """공백만 있는 텍스트도 빈 리스트를 반환한다"""
        assert compile_answer_blocks('   \n\n  ') == []


class TestExportBlocksHtml:
    """HTML 출력 테스트"""

    def test_export_html(self):
        """AnswerBlock이 HTML로 올바르게 내보내진다"""
        blocks = [
            AnswerBlock(question='질문1?', answer='답변1입니다.', source_paragraph=0, word_count=1),
        ]
        html = export_blocks(blocks, format='html')
        assert '<div class="qa-blocks">' in html
        assert '<h3 class="question">질문1?</h3>' in html
        assert '<p class="answer">답변1입니다.</p>' in html

    def test_export_html_escaping(self):
        """HTML 특수 문자가 이스케이프된다"""
        blocks = [
            AnswerBlock(question='<script>?', answer='a & b', source_paragraph=0),
        ]
        html = export_blocks(blocks, format='html')
        assert '&lt;script&gt;' in html
        assert '&amp;' in html

    def test_export_html_empty(self):
        """빈 블록 리스트는 빈 문자열을 반환한다"""
        assert export_blocks([], format='html') == ''

    def test_export_html_multiple(self):
        """여러 블록이 순서대로 출력된다"""
        blocks = [
            AnswerBlock(question='Q1?', answer='A1', source_paragraph=0),
            AnswerBlock(question='Q2?', answer='A2', source_paragraph=1),
        ]
        html = export_blocks(blocks, format='html')
        assert 'data-index="0"' in html
        assert 'data-index="1"' in html


class TestExportBlocksMarkdown:
    """마크다운 출력 테스트"""

    def test_export_markdown(self):
        """AnswerBlock이 마크다운으로 올바르게 내보내진다"""
        blocks = [
            AnswerBlock(question='질문?', answer='답변.', source_paragraph=0),
        ]
        md = export_blocks(blocks, format='markdown')
        assert '### 질문?' in md
        assert '답변.' in md

    def test_export_markdown_empty(self):
        """빈 블록 리스트는 빈 문자열을 반환한다"""
        assert export_blocks([], format='markdown') == ''

    def test_export_markdown_format(self):
        """마크다운 형식이 올바르다 (### 제목 + 빈 줄 + 내용)"""
        blocks = [
            AnswerBlock(question='Q?', answer='A.', source_paragraph=0),
        ]
        md = export_blocks(blocks, format='markdown')
        lines = md.split('\n')
        assert lines[0] == '### Q?'
        assert lines[1] == ''
        assert lines[2] == 'A.'


class TestMergeShortCards:
    """짧은 카드 병합 테스트"""

    def test_merge_short_text_cards(self):
        """min_length 미만의 짧은 카드가 이전 카드에 병합된다"""
        cards = [
            ContentCard(card_type='text', content='긴 텍스트 ' * 20, order=0),
            ContentCard(card_type='text', content='짧음', order=1),
        ]
        merged = merge_short_cards(cards, min_length=50)
        assert len(merged) == 1
        assert '짧음' in merged[0].content

    def test_heading_not_merged(self):
        """heading 카드는 병합 대상에서 제외된다"""
        cards = [
            ContentCard(card_type='heading', title='제목', order=0),
            ContentCard(card_type='text', content='짧음', order=1),
        ]
        merged = merge_short_cards(cards, min_length=50)
        # heading은 독립 유지, 짧은 text도 heading 뒤라 병합 불가
        assert len(merged) == 2
        assert merged[0].card_type == 'heading'

    def test_merge_reorders(self):
        """병합 후 order가 재정렬된다"""
        cards = [
            ContentCard(card_type='text', content='긴 텍스트 ' * 20, order=0),
            ContentCard(card_type='text', content='짧', order=5),
            ContentCard(card_type='text', content='또 긴 텍스트 ' * 20, order=10),
        ]
        merged = merge_short_cards(cards, min_length=50)
        orders = [c.order for c in merged]
        assert orders == list(range(len(merged)))

    def test_empty_cards(self):
        """빈 카드 리스트는 빈 리스트를 반환한다"""
        assert merge_short_cards([]) == []

    def test_all_long_cards_unchanged(self):
        """모든 카드가 min_length 이상이면 변화 없다"""
        cards = [
            ContentCard(card_type='text', content='a' * 60, order=0),
            ContentCard(card_type='text', content='b' * 60, order=1),
        ]
        merged = merge_short_cards(cards, min_length=50)
        assert len(merged) == 2
