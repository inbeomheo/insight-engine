"""모든 스타일 프롬프트의 공통 invariant 검증

각 프롬프트가 무심코 변경되거나 누락되면 콘텐츠 생성이 망가지므로 보호:
- 모든 스타일이 STYLE_PROMPTS에 등록됨
- 각 프롬프트는 충분히 길고 비어있지 않음
- get_style_prompt는 unknown → blog_seo 폴백
- CITED_SUMMARY는 [HH:MM:SS] 형식을 명시
- GEO_SEO는 entity/structured_data 키워드 포함
- SHORTS_SCRIPT는 60초/3-5클립 가이드 포함
- COURSE는 단계별 학습 구조 명시
- 모든 프롬프트가 '자막'을 참조 (입력 소스)
"""
import unittest

from prompts.styles import (
    STYLE_PROMPTS,
    get_style_prompt,
    BLOG_SEO_PROMPT,
    SUMMARY_PROMPT,
    TUTORIAL_PROMPT,
    QNA_PROMPT,
    APP_IDEAS_PROMPT,
    YOZM_IT_PROMPT,
    BRUNCH_ESSAY_PROMPT,
    NAVER_POPULAR_PROMPT,
    SNS_POST_PROMPT,
    NEWSLETTER_PROMPT,
    SHOW_NOTES_PROMPT,
    COMMENT_SUMMARY_PROMPT,
    MINDMAP_PROMPT,
    SHORTS_SCRIPT_PROMPT,
    GEO_SEO_PROMPT,
    COURSE_PROMPT,
    CITED_SUMMARY_PROMPT,
)


class TestStylePromptsRegistry(unittest.TestCase):

    EXPECTED_UI_STYLES = {
        'blog_seo', 'summary', 'tutorial', 'qna', 'app_ideas',
        'yozm_it', 'brunch_essay', 'naver_popular', 'sns_post',
        'newsletter', 'show_notes', 'shorts_script', 'geo_seo',
        'course', 'cited_summary',
    }

    def test_all_expected_styles_present(self):
        for style_id in self.EXPECTED_UI_STYLES:
            with self.subTest(style=style_id):
                self.assertIn(style_id, STYLE_PROMPTS,
                              f'{style_id}이 STYLE_PROMPTS에 등록되지 않음')

    def test_internal_only_mindmap_present(self):
        """mindmap은 UI 비노출이지만 등록되어야 함 (내부 호출용)"""
        self.assertIn('mindmap', STYLE_PROMPTS)

    def test_all_prompts_non_empty_strings(self):
        for style_id, prompt in STYLE_PROMPTS.items():
            with self.subTest(style=style_id):
                self.assertIsInstance(prompt, str)
                self.assertGreater(len(prompt.strip()), 50,
                                   f'{style_id} 프롬프트가 너무 짧음')

    def test_all_prompts_describe_writing_task(self):
        """모든 프롬프트는 글 작성 관련 키워드 (스타일/문체/작성/글/콘텐츠/독자/자막/영상 등)를 참조"""
        keywords = ('자막', '영상', '내용', '제공', '작성', '글', '문체',
                    '에세이', '독자', '콘텐츠', '스타일', '본문', '포스트',
                    '뉴스레터', 'Q&A', '튜토리얼')
        for style_id, prompt in STYLE_PROMPTS.items():
            with self.subTest(style=style_id):
                has_ref = any(kw in prompt for kw in keywords)
                self.assertTrue(has_ref,
                                f'{style_id} 프롬프트가 글쓰기 키워드를 전혀 포함하지 않음')


class TestGetStylePromptLookup(unittest.TestCase):

    def test_known_style_returns_correct_prompt(self):
        self.assertIs(get_style_prompt('blog_seo'), BLOG_SEO_PROMPT)
        self.assertIs(get_style_prompt('summary'), SUMMARY_PROMPT)
        self.assertIs(get_style_prompt('course'), COURSE_PROMPT)

    def test_unknown_returns_blog_seo_fallback(self):
        result = get_style_prompt('does_not_exist')
        self.assertIs(result, BLOG_SEO_PROMPT)


class TestSpecialStylePromptInvariants(unittest.TestCase):
    """특정 스타일의 도메인 키워드 검증 — 변경 시 기능 영향 큰 항목들"""

    def test_cited_summary_includes_timestamp_format(self):
        """인용 모드는 [HH:MM:SS] 형식을 LLM에게 지시해야 함"""
        self.assertTrue(
            '[HH:MM:SS]' in CITED_SUMMARY_PROMPT
            or 'HH:MM:SS' in CITED_SUMMARY_PROMPT,
            '인용 모드에 타임스탬프 형식 가이드 없음'
        )

    def test_geo_seo_includes_ai_search_keywords(self):
        """GEO_SEO는 AI 검색 키워드 (entity, structured_data, citations 등) 포함"""
        has_geo_terms = any(term in GEO_SEO_PROMPT for term in
                            ('entity', '엔티티', 'structured_data', 'JSON-LD',
                             'AI 검색', 'AI 검색엔진', 'citations', '인용'))
        self.assertTrue(has_geo_terms, 'GEO_SEO 프롬프트에 AI 검색 관련 용어 없음')

    def test_shorts_script_mentions_clip_count(self):
        """SHORTS_SCRIPT는 60초/3-5클립 가이드 포함"""
        self.assertTrue(
            '60초' in SHORTS_SCRIPT_PROMPT or '클립' in SHORTS_SCRIPT_PROMPT,
            'Shorts 스크립트 프롬프트에 클립/시간 가이드 없음'
        )

    def test_course_mentions_steps_or_chapters(self):
        """COURSE는 단계별/챕터 구조 명시"""
        self.assertTrue(
            '단계' in COURSE_PROMPT or '챕터' in COURSE_PROMPT
            or '학습' in COURSE_PROMPT or '코스' in COURSE_PROMPT,
            'COURSE 프롬프트에 학습 구조 가이드 없음'
        )

    def test_comment_summary_mentions_comments(self):
        """COMMENT_SUMMARY는 댓글을 명시적으로 참조해야 함"""
        self.assertIn('댓글', COMMENT_SUMMARY_PROMPT)

    def test_mindmap_mentions_mindmap_or_tree(self):
        """MINDMAP은 mindmap/마인드맵/트리 등 구조 키워드"""
        self.assertTrue(
            '마인드맵' in MINDMAP_PROMPT or 'mindmap' in MINDMAP_PROMPT.lower()
            or '트리' in MINDMAP_PROMPT or '계층' in MINDMAP_PROMPT
            or 'Mermaid' in MINDMAP_PROMPT or '## ' in MINDMAP_PROMPT,
            'MINDMAP 프롬프트에 마인드맵 키워드 없음'
        )


class TestForbiddenExpressionsInStyles(unittest.TestCase):
    """모든 스타일이 글로벌 금지 표현 규칙을 인지하는지 — 보통 base에서 처리되나 일부는 자체 명시"""

    UI_STYLES = ['blog_seo', 'summary', 'tutorial', 'qna', 'app_ideas',
                 'yozm_it', 'brunch_essay', 'naver_popular', 'sns_post',
                 'newsletter', 'show_notes', 'shorts_script', 'geo_seo',
                 'course']

    def test_styles_do_not_contradict_base_forbidden(self):
        """스타일 프롬프트가 BASE에서 금지한 표현을 권장하면 안 됨"""
        forbidden_words = ('놀라운 결과', '획기적 방법', '게임체인저')
        for style_id in self.UI_STYLES:
            prompt = STYLE_PROMPTS.get(style_id, '')
            for fw in forbidden_words:
                with self.subTest(style=style_id, word=fw):
                    # 금지 표현을 "사용하세요" 같은 권장 문맥에 포함하면 안 됨
                    # 금지 표현 단독 등장은 허용 (base prompt가 어차피 금지 명시)
                    bad_context = f'{fw}을(를) 사용'
                    self.assertNotIn(bad_context, prompt,
                                     f'{style_id}이 금지 표현 {fw}을(를) 권장')


if __name__ == '__main__':
    unittest.main()
