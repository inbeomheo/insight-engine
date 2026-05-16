"""agent/compressor — 컨텍스트 압축기 단위 테스트

5단계 알고리즘 (Hermes 패턴) 중 LLM 호출 없는 단계를 위주로 테스트:
1. 도구 결과 프루닝
2. 헤드/미들/테일 분리
3. 미리보기 추출
4. 폴백 요약
5. 토큰 추정
"""
import json
import unittest
from unittest.mock import patch

from agent.compressor import (
    compress_messages,
    _prune_tool_results,
    _extract_preview,
    _split_head_middle_tail,
    _find_existing_summary,
    _fallback_summary,
    _estimate_tokens,
    _messages_to_text,
    SUMMARY_MARKER,
)


def _msg(role: str, content: str = '', **extra) -> dict:
    return {'role': role, 'content': content, **extra}


class TestPruneToolResults(unittest.TestCase):

    def test_short_results_unchanged(self):
        msgs = [_msg('tool', 'short') for _ in range(10)]
        msgs.insert(0, _msg('system', 'sys'))
        result = _prune_tool_results(msgs, max_len=100, protect_recent=3)
        # 모두 길이 100 이하라 변경 없음
        for m in result:
            if m.get('role') == 'tool':
                self.assertEqual(m.get('content'), 'short')

    def test_long_old_results_truncated(self):
        long_content = 'x' * 500
        msgs = [_msg('tool', long_content)] * 10
        result = _prune_tool_results(msgs, max_len=200, protect_recent=3)
        # 옛 도구 결과(처음 7개)는 축약됨
        for m in result[:7]:
            self.assertIn('결과 축약', m['content'])
        # 최근 3개는 원본 유지
        for m in result[-3:]:
            self.assertEqual(m['content'], long_content)

    def test_protect_recent_skipped_when_total_small(self):
        msgs = [_msg('tool', 'x' * 500)] * 5
        result = _prune_tool_results(msgs, max_len=100, protect_recent=10)
        # protect_recent보다 적으므로 변경 없음
        self.assertEqual(result, msgs)

    def test_non_tool_roles_not_pruned(self):
        msgs = [
            _msg('user', 'x' * 500),
            _msg('assistant', 'y' * 500),
            _msg('tool', 'z' * 500),
        ] * 5
        result = _prune_tool_results(msgs, max_len=100, protect_recent=3)
        # user / assistant는 길이와 관계없이 보존
        for m in result:
            if m['role'] in ('user', 'assistant'):
                self.assertEqual(len(m['content']), 500)


class TestExtractPreview(unittest.TestCase):

    def test_json_dict_summarized(self):
        content = json.dumps({'a': 'long' * 100, 'b': 2, 'c': 3, 'd': 4, 'e': 5, 'f': 6})
        preview = _extract_preview(content, max_len=200)
        # 처음 5개 키만 포함, 'f' 제외
        self.assertNotIn('"f"', preview)
        self.assertIn('"a"', preview)

    def test_json_list_summarized(self):
        content = json.dumps([{'x': i} for i in range(10)])
        preview = _extract_preview(content, max_len=200)
        # 처음 2개만
        self.assertIn('"x": 0', preview)
        self.assertNotIn('"x": 9', preview)

    def test_plain_text_truncated(self):
        content = 'a' * 500
        preview = _extract_preview(content, max_len=100)
        self.assertEqual(len(preview), 100)


class TestSplitHeadMiddleTail(unittest.TestCase):

    def test_basic_split(self):
        msgs = [_msg('system', 'sys')]
        msgs += [_msg('user', f'u{i}') for i in range(15)]
        msgs += [_msg('assistant', f'a{i}') for i in range(15)]
        head, middle, tail = _split_head_middle_tail(msgs, tail_count=5)
        # head는 시스템 + 첫 user-assistant
        self.assertEqual(head[0]['role'], 'system')
        # tail은 5개
        self.assertEqual(len(tail), 5)
        # head + middle + tail = 원본
        self.assertEqual(len(head) + len(middle) + len(tail), len(msgs))

    def test_small_conversation_empty_middle(self):
        msgs = [_msg('system', 'sys'), _msg('user', 'q'), _msg('assistant', 'a')]
        head, middle, tail = _split_head_middle_tail(msgs, tail_count=10)
        # 3개 메시지 → 미들 없음
        self.assertEqual(middle, [])


class TestFindExistingSummary(unittest.TestCase):

    def test_finds_marker(self):
        msgs = [
            _msg('user', 'q'),
            _msg('assistant', f'{SUMMARY_MARKER}\n이전 요약 내용입니다'),
            _msg('user', 'q2'),
        ]
        result = _find_existing_summary(msgs)
        self.assertEqual(result, '이전 요약 내용입니다')

    def test_no_summary_returns_none(self):
        msgs = [_msg('user', 'q'), _msg('assistant', 'a')]
        self.assertIsNone(_find_existing_summary(msgs))


class TestFallbackSummary(unittest.TestCase):

    def test_extracts_user_messages_and_tools(self):
        msgs = [
            _msg('user', '첫 번째 질문'),
            _msg('assistant', '', tool_calls=[
                {'function': {'name': 'read_file'}},
                {'function': {'name': 'edit_file'}},
            ]),
            _msg('user', '두 번째 질문'),
        ]
        result = _fallback_summary(msgs)
        self.assertIn('첫 번째 질문', result)
        self.assertIn('두 번째 질문', result)
        self.assertIn('read_file', result)
        self.assertIn('edit_file', result)

    def test_empty_returns_turn_count(self):
        """빈 middle도 '턴 수: 0개' 요약 라인을 항상 포함"""
        result = _fallback_summary([])
        self.assertIn('턴 수', result)
        self.assertIn('0', result)


class TestEstimateTokens(unittest.TestCase):

    def test_empty(self):
        self.assertEqual(_estimate_tokens([]), 0)

    def test_proportional_to_content(self):
        small = _estimate_tokens([_msg('user', 'a' * 100)])
        big = _estimate_tokens([_msg('user', 'a' * 1000)])
        self.assertGreater(big, small)

    def test_includes_tool_calls(self):
        with_tools = _estimate_tokens([_msg('assistant', '', tool_calls=[{'function': {'name': 'x', 'arguments': 'y' * 200}}])])
        without_tools = _estimate_tokens([_msg('assistant', '')])
        self.assertGreater(with_tools, without_tools)


class TestMessagesToText(unittest.TestCase):

    def test_tool_role_marked(self):
        msgs = [_msg('tool', 'tool result content')]
        result = _messages_to_text(msgs)
        self.assertIn('[Tool Result]', result)
        self.assertIn('tool result content', result)

    def test_assistant_tool_calls(self):
        msgs = [_msg('assistant', '', tool_calls=[{'function': {'name': 'analyze'}}])]
        result = _messages_to_text(msgs)
        self.assertIn('도구 호출', result)
        self.assertIn('analyze', result)

    def test_truncates_long_total(self):
        msgs = [_msg('user', 'x' * 600)] * 30
        result = _messages_to_text(msgs, max_total=2000)
        # max_total 초과 시 생략 표시
        self.assertIn('이하 생략', result)


class TestCompressMessagesIntegration(unittest.TestCase):
    """compress_messages 전체 흐름 — LLM 호출 부분만 모의"""

    def test_empty_passthrough(self):
        self.assertEqual(compress_messages([], target_tokens=1000), [])

    def test_short_messages_only_prune(self):
        """target보다 작으면 압축 안 함"""
        msgs = [_msg('user', 'short')] * 5
        result = compress_messages(msgs, target_tokens=10_000)
        # 변경 없음 (모두 짧고 target이 큼)
        self.assertEqual(len(result), 5)

    def test_long_messages_summarized_with_fallback(self):
        """LLM 실패 시 fallback summary 사용"""
        # 헤드 + 큰 미들 + 테일
        msgs = [_msg('system', 'sys')]
        msgs += [_msg('user', 'first q'), _msg('assistant', 'first a')]
        msgs += [_msg('user', 'x' * 5000)] * 30  # 거대한 미들
        msgs += [_msg('user', 'recent q'), _msg('assistant', 'recent a')]

        # LLM이 실패하도록
        with patch('agent.compressor.completion', side_effect=RuntimeError('llm down'), create=True):
            result = compress_messages(msgs, target_tokens=500)

        # 압축 후 크기가 원본보다 작아야 함
        self.assertLess(len(result), len(msgs))
        # SUMMARY_MARKER가 결과에 포함
        joined = '\n'.join(m.get('content', '') for m in result)
        self.assertIn(SUMMARY_MARKER, joined)


if __name__ == '__main__':
    unittest.main()
