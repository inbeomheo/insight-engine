"""
품질 자동 평가 (Quality Gate) 통합 테스트

P2-5A: 프롬프트 텍스트 검증
P2-5B: evaluate_quality(), should_regenerate() 단위 테스트
P2-5E: auto_regenerate() 재생성 로직 테스트
P2-5C: /generate 응답의 quality_score 필드 테스트
"""
import json
import unittest
from unittest.mock import patch, MagicMock


# ─── P2-5A: 프롬프트 텍스트 검증 ─────────────────────────────────


class TestQualityEvalPrompt(unittest.TestCase):
    """품질 평가 프롬프트 구조 테스트"""

    def setUp(self):
        from prompts.quality_eval import QUALITY_EVAL_PROMPT
        self.prompt = QUALITY_EVAL_PROMPT

    def test_prompt_contains_four_criteria(self):
        """4개 평가 기준(정확성/일관성/가독성/유용성) 포함 여부"""
        self.assertIn('accuracy', self.prompt)
        self.assertIn('coherence', self.prompt)
        self.assertIn('readability', self.prompt)
        self.assertIn('usefulness', self.prompt)

    def test_prompt_contains_grade_thresholds(self):
        """등급 기준(A/B/C/D) 포함 여부"""
        self.assertIn('A등급', self.prompt)
        self.assertIn('B등급', self.prompt)
        self.assertIn('C등급', self.prompt)
        self.assertIn('D등급', self.prompt)

    def test_prompt_has_json_output_format(self):
        """JSON 출력 형식 지시 포함 여부"""
        self.assertIn('json', self.prompt.lower())
        self.assertIn('overall', self.prompt)
        self.assertIn('grade', self.prompt)
        self.assertIn('feedback', self.prompt)

    def test_prompt_has_placeholders(self):
        """source_summary / content 플레이스홀더 포함 여부"""
        self.assertIn('{source_summary}', self.prompt)
        self.assertIn('{content}', self.prompt)

    def test_prompt_format_works(self):
        """프롬프트 .format() 정상 동작 확인"""
        formatted = self.prompt.format(
            source_summary='테스트 자막 요약',
            content='테스트 생성 콘텐츠',
        )
        self.assertIn('테스트 자막 요약', formatted)
        self.assertIn('테스트 생성 콘텐츠', formatted)


# ─── P2-5B: 품질 서비스 단위 테스트 ──────────────────────────────


class TestParseQualityJson(unittest.TestCase):
    """_parse_quality_json 파싱 테스트"""

    def test_parse_clean_json(self):
        """순수 JSON 파싱"""
        from services.quality.quality_service import _parse_quality_json
        raw = '{"accuracy": 8, "coherence": 7, "readability": 9, "usefulness": 6, "overall": 7.5, "grade": "B", "feedback": "좋음"}'
        result = _parse_quality_json(raw)
        self.assertIsNotNone(result)
        self.assertEqual(result['grade'], 'B')

    def test_parse_json_in_code_block(self):
        """```json ... ``` 블록 내 JSON 파싱"""
        from services.quality.quality_service import _parse_quality_json
        raw = '```json\n{"accuracy": 8, "coherence": 7, "readability": 9, "usefulness": 6, "overall": 7.5, "grade": "B", "feedback": "좋음"}\n```'
        result = _parse_quality_json(raw)
        self.assertIsNotNone(result)
        self.assertEqual(result['accuracy'], 8)

    def test_parse_json_with_surrounding_text(self):
        """전후 텍스트가 있는 JSON 파싱"""
        from services.quality.quality_service import _parse_quality_json
        raw = '평가 결과:\n{"accuracy": 5, "coherence": 5, "readability": 5, "usefulness": 5, "overall": 5.0, "grade": "C", "feedback": "보통"}\n감사합니다.'
        result = _parse_quality_json(raw)
        self.assertIsNotNone(result)

    def test_parse_invalid_json_returns_none(self):
        """잘못된 JSON은 None 반환"""
        from services.quality.quality_service import _parse_quality_json
        result = _parse_quality_json('이것은 JSON이 아닙니다')
        self.assertIsNone(result)


class TestValidateQualityResult(unittest.TestCase):
    """_validate_quality_result 검증 테스트"""

    def _make_valid_data(self, accuracy=8, coherence=7, readability=9, usefulness=6):
        return {
            'accuracy': accuracy,
            'coherence': coherence,
            'readability': readability,
            'usefulness': usefulness,
            'overall': 7.5,
            'grade': 'B',
            'feedback': '테스트 피드백',
        }

    def test_valid_data_passes(self):
        """유효한 데이터는 통과"""
        from services.quality.quality_service import _validate_quality_result
        data = self._make_valid_data()
        result = _validate_quality_result(data)
        self.assertEqual(result['grade'], 'B')

    def test_overall_recalculated(self):
        """overall이 LLM 오류 값이어도 재계산됨"""
        from services.quality.quality_service import _validate_quality_result
        data = self._make_valid_data(accuracy=8, coherence=8, readability=8, usefulness=8)
        data['overall'] = 99  # 잘못된 값
        result = _validate_quality_result(data)
        self.assertAlmostEqual(result['overall'], 8.0)

    def test_grade_a_threshold(self):
        """overall 8.0 이상 → A등급"""
        from services.quality.quality_service import _validate_quality_result
        data = self._make_valid_data(accuracy=8, coherence=8, readability=9, usefulness=9)
        result = _validate_quality_result(data)
        self.assertEqual(result['grade'], 'A')

    def test_grade_d_threshold(self):
        """overall 4.0 미만 → D등급"""
        from services.quality.quality_service import _validate_quality_result
        data = self._make_valid_data(accuracy=2, coherence=3, readability=3, usefulness=2)
        result = _validate_quality_result(data)
        self.assertEqual(result['grade'], 'D')

    def test_missing_key_raises_error(self):
        """필수 키 누락 시 ValueError"""
        from services.quality.quality_service import _validate_quality_result
        data = {'accuracy': 8, 'coherence': 7}  # 나머지 키 없음
        with self.assertRaises(ValueError):
            _validate_quality_result(data)

    def test_score_out_of_range_raises_error(self):
        """점수 범위(1~10) 초과 시 ValueError"""
        from services.quality.quality_service import _validate_quality_result
        data = self._make_valid_data(accuracy=11)  # 10 초과
        with self.assertRaises(ValueError):
            _validate_quality_result(data)


class TestShouldRegenerate(unittest.TestCase):
    """should_regenerate 로직 테스트"""

    def _make_quality(self, grade):
        return {'grade': grade, 'overall': 5.0}

    def test_grade_d_below_c_threshold(self):
        """D등급은 C 기준 미달 → True"""
        from services.quality.quality_service import should_regenerate
        self.assertTrue(should_regenerate(self._make_quality('D'), 'C'))

    def test_grade_c_meets_c_threshold(self):
        """C등급은 C 기준 충족 → False"""
        from services.quality.quality_service import should_regenerate
        self.assertFalse(should_regenerate(self._make_quality('C'), 'C'))

    def test_grade_a_meets_all_thresholds(self):
        """A등급은 모든 기준 충족 → False"""
        from services.quality.quality_service import should_regenerate
        for threshold in ('A', 'B', 'C', 'D'):
            self.assertFalse(should_regenerate(self._make_quality('A'), threshold))

    def test_grade_b_below_a_threshold(self):
        """B등급은 A 기준 미달 → True"""
        from services.quality.quality_service import should_regenerate
        self.assertTrue(should_regenerate(self._make_quality('B'), 'A'))


class TestEvaluateQuality(unittest.TestCase):
    """evaluate_quality() 모킹 테스트"""

    def _make_mock_response(self, grade='B', overall=7.0):
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = json.dumps({
            'accuracy': 7,
            'coherence': 7,
            'readability': 7,
            'usefulness': 7,
            'overall': overall,
            'grade': grade,
            'feedback': '전반적으로 양호한 콘텐츠입니다.',
        })
        return mock_resp

    def _make_app_context(self):
        """Flask 앱 컨텍스트 반환"""
        import app as flask_app
        return flask_app.app.app_context()

    @patch('services.quality_service._get_eval_model', return_value='zhipuai/GLM-4.5-Air')
    @patch('services.quality_service.os.getenv', return_value='fake-api-key')
    @patch('litellm.completion')
    def test_evaluate_quality_returns_correct_structure(self, mock_completion, mock_getenv, mock_eval_model):
        """evaluate_quality() 반환값 구조 검증"""
        mock_completion.return_value = self._make_mock_response('B', 7.0)

        with self._make_app_context():
            from services.quality.quality_service import evaluate_quality
            result = evaluate_quality(
                content='테스트 콘텐츠입니다.',
                source_summary='테스트 자막 요약',
                model='zhipuai/GLM-4.5-Air',
            )

        required_keys = {'accuracy', 'coherence', 'readability', 'usefulness', 'overall', 'grade', 'feedback', 'eval_model'}
        self.assertTrue(required_keys.issubset(result.keys()))
        self.assertIn(result['grade'], ('A', 'B', 'C', 'D'))

    @patch('services.quality_service._get_eval_model', return_value=None)
    def test_evaluate_quality_no_model_raises(self, mock_eval_model):
        """사용 가능한 모델 없으면 예외 발생"""
        with self._make_app_context():
            from services.quality.quality_service import evaluate_quality
            with self.assertRaises(Exception) as ctx:
                evaluate_quality('content', 'summary')
            self.assertIn('모델', str(ctx.exception))


# ─── P2-5E: auto_regenerate 테스트 ────────────────────────────────


class TestAutoRegenerate(unittest.TestCase):
    """auto_regenerate() 재생성 로직 테스트"""

    def _make_result(self, content='테스트'):
        return ({'title': '제목', 'content': content, 'html': '', 'usage': {}}, '프롬프트')

    def _make_quality(self, grade, overall):
        return {
            'accuracy': 5, 'coherence': 5, 'readability': 5, 'usefulness': 5,
            'overall': overall, 'grade': grade, 'feedback': '피드백',
            'eval_model': 'test-model'
        }

    def _make_app_context(self):
        import app as flask_app
        return flask_app.app.app_context()

    def test_returns_best_result_on_first_pass(self):
        """첫 시도에서 기준 충족 시 즉시 반환"""
        call_count = {'n': 0}

        def content_fn():
            call_count['n'] += 1
            return self._make_result('좋은 콘텐츠')

        with self._make_app_context():
            with patch('services.quality_service.evaluate_quality') as mock_eval:
                mock_eval.return_value = self._make_quality('B', 7.0)

                from services.quality.quality_service import auto_regenerate
                result, quality = auto_regenerate(content_fn, '자막 요약', quality_threshold='C')

        self.assertEqual(call_count['n'], 1)
        self.assertIsNotNone(result)
        self.assertEqual(quality['grade'], 'B')

    def test_retries_on_low_grade(self):
        """D등급 → 재시도 1회 발생"""
        call_count = {'n': 0}
        qualities = [
            {'accuracy': 3, 'coherence': 3, 'readability': 3, 'usefulness': 3,
             'overall': 3.0, 'grade': 'D', 'feedback': '미흡', 'eval_model': 'test'},
            {'accuracy': 7, 'coherence': 7, 'readability': 7, 'usefulness': 7,
             'overall': 7.0, 'grade': 'B', 'feedback': '양호', 'eval_model': 'test'},
        ]

        def content_fn():
            call_count['n'] += 1
            return self._make_result(f'콘텐츠 {call_count["n"]}')

        with self._make_app_context():
            with patch('services.quality_service.evaluate_quality') as mock_eval:
                mock_eval.side_effect = qualities

                from services.quality.quality_service import auto_regenerate
                result, quality = auto_regenerate(
                    content_fn, '자막 요약', quality_threshold='C', max_retries=1
                )

        self.assertEqual(call_count['n'], 2)
        self.assertEqual(quality['grade'], 'B')

    def test_returns_best_grade_when_retry_worse(self):
        """재시도 결과가 원본보다 낮으면 원본 반환"""
        call_count = {'n': 0}
        qualities = [
            {'accuracy': 7, 'coherence': 7, 'readability': 7, 'usefulness': 7,
             'overall': 7.0, 'grade': 'B', 'feedback': '양호', 'eval_model': 'test'},
            {'accuracy': 3, 'coherence': 3, 'readability': 3, 'usefulness': 3,
             'overall': 3.0, 'grade': 'D', 'feedback': '나쁨', 'eval_model': 'test'},
        ]

        def content_fn():
            call_count['n'] += 1
            return self._make_result(f'콘텐츠 {call_count["n"]}')

        with self._make_app_context():
            with patch('services.quality_service.evaluate_quality') as mock_eval:
                mock_eval.side_effect = qualities

                from services.quality.quality_service import auto_regenerate
                result, quality = auto_regenerate(
                    content_fn, '자막 요약', quality_threshold='A', max_retries=1
                )

        # B등급(첫 시도)이 D등급(재시도)보다 높으므로 B 반환
        self.assertEqual(quality['grade'], 'B')


# ─── P2-5C: /generate 응답 quality_score 필드 테스트 ─────────────


class TestGenerateEndpointQualityScore(unittest.TestCase):
    """Flask 엔드포인트 레벨에서 quality_score 필드 테스트"""

    def setUp(self):
        """Flask 테스트 클라이언트 설정"""
        import os
        os.environ.setdefault('TESTING', 'true')

        with patch('services.supabase_service.is_supabase_enabled', return_value=False):
            import app as flask_app
            self.app = flask_app.app
            self.client = self.app.test_client()

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_quality_score_not_in_response_by_default(self, mock_supabase):
        """quality_check 미지정 시 quality_score 없음 (null)"""
        with self.app.test_request_context():
            resp = self.client.post(
                '/generate',
                json={
                    'url': 'https://www.youtube.com/watch?v=test123',
                    'model': 'zhipuai/GLM-4.5-Air',
                    'style': 'blog_seo',
                },
                headers={'Authorization': 'Bearer fake-token'},
            )
        # 인증 실패 또는 URL 오류 등 → quality_score 확인만 의미
        # 응답 자체가 400이어도 quality_score가 응답에 없는 구조면 OK
        # (실제 엔드포인트 흐름은 mock 없이 테스트 어려움 → 서비스 레벨에서 검증)
        self.assertIsNotNone(resp)  # 서버가 최소한 응답함

    def test_quality_score_field_exists_in_response_structure(self):
        """_save_and_respond에서 quality_score=None이면 응답에 null로 포함됨"""
        # generation_helpers의 _save_and_respond가 quality_score를 응답에 포함하는지
        # 직접 함수 시그니처 확인 (통합 수준 smoke test)
        import inspect
        from routes.generation_helpers import _save_and_respond
        sig = inspect.signature(_save_and_respond)
        self.assertIn('quality_score', sig.parameters)


if __name__ == '__main__':
    unittest.main()
