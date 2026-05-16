"""agent/prompts/roles — 역할별 시스템 프롬프트 + 기본 toolset 매핑"""
import unittest

from agent.prompts.roles import (
    ROLE_PROMPTS,
    ROLE_TOOLSETS,
    SUPERVISOR_PROMPT,
    WRITER_PROMPT,
    EDITOR_PROMPT,
    SEO_PROMPT,
    PUBLISHER_PROMPT,
    get_role_prompt,
    get_role_toolsets,
)


class TestRolePromptsRegistry(unittest.TestCase):

    EXPECTED_ROLES = {'supervisor', 'writer', 'editor', 'seo', 'publisher'}

    def test_all_expected_roles_present(self):
        self.assertEqual(set(ROLE_PROMPTS.keys()), self.EXPECTED_ROLES)
        self.assertEqual(set(ROLE_TOOLSETS.keys()), self.EXPECTED_ROLES)

    def test_each_prompt_non_empty(self):
        for role, prompt in ROLE_PROMPTS.items():
            with self.subTest(role=role):
                self.assertIsInstance(prompt, str)
                self.assertGreater(len(prompt.strip()), 200)

    def test_each_role_has_toolset(self):
        for role in self.EXPECTED_ROLES:
            with self.subTest(role=role):
                ts = ROLE_TOOLSETS[role]
                self.assertIsInstance(ts, list)
                self.assertGreater(len(ts), 0)


class TestRolePromptContents(unittest.TestCase):

    def test_supervisor_describes_delegation(self):
        self.assertIn('Supervisor', SUPERVISOR_PROMPT)
        self.assertIn('delegate', SUPERVISOR_PROMPT)

    def test_writer_mentions_styles(self):
        self.assertIn('Writer', WRITER_PROMPT)
        # 주요 스타일 ID 포함
        for s in ('blog_seo', 'summary', 'tutorial'):
            self.assertIn(s, WRITER_PROMPT)

    def test_editor_mentions_quality_tools(self):
        self.assertIn('Editor', EDITOR_PROMPT)
        # 품질 분석 도구 언급
        self.assertIn('analyze_readability', EDITOR_PROMPT)
        self.assertIn('grade_content', EDITOR_PROMPT)

    def test_seo_mentions_seo_tools(self):
        self.assertIn('SEO', SEO_PROMPT)
        # SEO 분석 키워드 (대소문자 무관 매칭)
        for kw in ('E-E-A-T', 'SERP', 'aeo', '키워드'):
            self.assertIn(kw, SEO_PROMPT)

    def test_publisher_warns_about_irreversibility(self):
        """발행은 되돌릴 수 없다는 경고"""
        self.assertIn('Publisher', PUBLISHER_PROMPT)
        self.assertTrue(
            '취소' in PUBLISHER_PROMPT or '신중' in PUBLISHER_PROMPT,
            'Publisher 프롬프트에 발행 신중성 경고 없음'
        )

    def test_all_prompts_share_korean_response_directive(self):
        """모든 역할은 한국어로 응답하라는 공통 베이스 포함"""
        for role, prompt in ROLE_PROMPTS.items():
            with self.subTest(role=role):
                self.assertIn('한국어로 응답', prompt)


class TestRoleToolsetMapping(unittest.TestCase):

    def test_supervisor_uses_full(self):
        self.assertEqual(ROLE_TOOLSETS['supervisor'], ['full'])

    def test_each_role_uses_corresponding_role_toolset(self):
        cases = [
            ('writer', 'role_writer'),
            ('editor', 'role_editor'),
            ('seo', 'role_seo'),
            ('publisher', 'role_publisher'),
        ]
        for role, expected_ts in cases:
            with self.subTest(role=role):
                self.assertIn(expected_ts, ROLE_TOOLSETS[role])


class TestRoleHelpers(unittest.TestCase):

    def test_get_role_prompt_known(self):
        self.assertEqual(get_role_prompt('writer'), WRITER_PROMPT)
        self.assertEqual(get_role_prompt('seo'), SEO_PROMPT)

    def test_get_role_prompt_unknown_returns_none(self):
        self.assertIsNone(get_role_prompt('unknown_role'))

    def test_get_role_toolsets_known(self):
        self.assertEqual(get_role_toolsets('supervisor'), ['full'])

    def test_get_role_toolsets_unknown_returns_full(self):
        """알 수 없는 역할은 안전한 기본값 ['full'] 반환"""
        self.assertEqual(get_role_toolsets('unknown_role'), ['full'])


if __name__ == '__main__':
    unittest.main()
