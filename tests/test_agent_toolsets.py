"""agent/toolsets — Toolset 정의 + 재귀적 해석 단위 테스트"""
import unittest

from agent.toolsets import (
    TOOLSETS,
    resolve_toolset,
    resolve_toolsets,
    resolve_toolset_names,
    get_toolset_description,
    list_toolset_names,
)


class TestToolsetsStructure(unittest.TestCase):

    def test_all_have_description(self):
        for name, ts in TOOLSETS.items():
            with self.subTest(toolset=name):
                self.assertIn('description', ts)
                self.assertIsInstance(ts['description'], str)
                self.assertGreater(len(ts['description']), 0)

    def test_all_have_tools_and_includes_keys(self):
        for name, ts in TOOLSETS.items():
            with self.subTest(toolset=name):
                self.assertIn('tools', ts)
                self.assertIn('includes', ts)
                self.assertIsInstance(ts['tools'], list)
                self.assertIsInstance(ts['includes'], list)

    def test_includes_reference_existing_toolsets(self):
        """includes에 적힌 모든 이름이 TOOLSETS 키로 존재해야 함"""
        all_names = set(TOOLSETS.keys())
        for name, ts in TOOLSETS.items():
            for inc in ts['includes']:
                with self.subTest(toolset=name, include=inc):
                    self.assertIn(inc, all_names, f'{name} 의 includes 에 unknown: {inc}')

    def test_full_role_includes_many_toolsets(self):
        """full 역할은 sanity check — 10개 이상 포함"""
        self.assertIn('full', TOOLSETS)
        self.assertGreaterEqual(len(TOOLSETS['full']['includes']), 10)


class TestResolveToolset(unittest.TestCase):

    def test_unknown_returns_empty(self):
        self.assertEqual(resolve_toolset('nonexistent'), [])

    def test_leaf_toolset_returns_own_tools(self):
        # collector는 직접 tools만 있음
        result = resolve_toolset('collector')
        self.assertIn('collect_youtube', result)
        self.assertIn('collect_webpage', result)

    def test_composite_role_expands(self):
        """role_publisher = export + integrations + mcp + schedule + rewrite + agent_control"""
        result = resolve_toolset('role_publisher')
        # export 도구 포함 확인
        self.assertIn('export_docx', result)

    def test_deduplication(self):
        """role_writer가 같은 도구를 두 경로로 포함해도 한 번만"""
        result = resolve_toolset('role_writer') if 'role_writer' in TOOLSETS else None
        if result:
            self.assertEqual(len(result), len(set(result)))

    def test_circular_reference_safe(self):
        """수동으로 순환 참조 toolset을 삽입해도 무한루프 없음"""
        original = TOOLSETS.copy()
        try:
            TOOLSETS['__test_a'] = {'tools': ['x'], 'includes': ['__test_b'], 'description': 't'}
            TOOLSETS['__test_b'] = {'tools': ['y'], 'includes': ['__test_a'], 'description': 't'}
            result = resolve_toolset('__test_a')
            # 양쪽 tool 다 포함되어야 함 (한 번씩만)
            self.assertIn('x', result)
            self.assertIn('y', result)
            self.assertEqual(len(result), 2)
        finally:
            TOOLSETS.pop('__test_a', None)
            TOOLSETS.pop('__test_b', None)


class TestResolveToolsets(unittest.TestCase):

    def test_multiple_toolsets_combined(self):
        result = resolve_toolsets(['collector', 'core'])
        self.assertIn('collect_youtube', result)
        self.assertIn('create_content', result)

    def test_visited_dedup_across_toolsets(self):
        """동일 toolset이 여러 번 나와도 도구는 한 번씩"""
        result = resolve_toolsets(['collector', 'collector'])
        self.assertEqual(len(result), len(set(result)))

    def test_empty_input(self):
        self.assertEqual(resolve_toolsets([]), [])


class TestResolveToolsetNames(unittest.TestCase):

    def test_leaf_toolset_returns_self(self):
        result = resolve_toolset_names(['collector'])
        self.assertIn('collector', result)

    def test_composite_expands_to_leaves(self):
        """role 합성을 leaf toolset 이름으로 펼침"""
        result = resolve_toolset_names(['role_publisher'])
        # 합성 자체는 결과에 포함되지 않음 (또는 자체 tools 있을 때만)
        self.assertGreater(len(result), 0)
        # leaf 중 하나는 'export'
        self.assertIn('export', result)

    def test_unknown_name_silent_skip(self):
        result = resolve_toolset_names(['nonexistent', 'collector'])
        self.assertEqual(result, ['collector'])

    def test_dedup_across_inputs(self):
        result = resolve_toolset_names(['collector', 'collector', 'core'])
        self.assertEqual(len(result), len(set(result)))


class TestGetToolsetDescription(unittest.TestCase):

    def test_known(self):
        desc = get_toolset_description('collector')
        self.assertIn('수집', desc)

    def test_unknown_returns_empty(self):
        self.assertEqual(get_toolset_description('nonexistent'), '')


class TestListToolsetNames(unittest.TestCase):

    def test_returns_all_keys(self):
        names = list_toolset_names()
        self.assertEqual(set(names), set(TOOLSETS.keys()))

    def test_includes_essential_names(self):
        names = list_toolset_names()
        for essential in ('collector', 'core', 'full'):
            self.assertIn(essential, names)


if __name__ == '__main__':
    unittest.main()
