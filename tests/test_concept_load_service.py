"""Concept Load Analyzer 서비스 테스트."""
import unittest
from services.concept_load_service import analyze_concept_load


class TestConceptLoad(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_concept_load('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['level'], 'none')

    def test_none_content(self):
        result = analyze_concept_load(None)
        self.assertEqual(result['score'], 100.0)

    def test_no_concepts(self):
        content = '오늘 날씨가 좋습니다. 산책을 나갔습니다. 맛있는 점심을 먹었습니다.'
        result = analyze_concept_load(content)
        self.assertEqual(result['summary']['max_concepts_in_window'], 0)

    def test_manageable_load(self):
        content = ('레이턴시를 줄입니다. 일반적인 내용입니다. 다음 단계로 넘어갑니다.')
        result = analyze_concept_load(content)
        self.assertEqual(result['summary']['level'], 'manageable')

    def test_overloaded_ko(self):
        content = ('레이턴시와 스루풋을 측정합니다. '
                   '미들웨어와 오케스트레이션을 설정합니다. '
                   '프로비저닝과 컨테이너와 클러스터를 구성합니다.')
        result = analyze_concept_load(content)
        self.assertGreater(result['summary']['overloaded_windows'], 0)

    def test_overloaded_en(self):
        content = ('Configure sharding and partitioning for the database. '
                   'Implement serialization with middleware and orchestration. '
                   'Add webhook polling with replication enabled.')
        result = analyze_concept_load(content)
        self.assertGreater(result['summary']['overloaded_windows'], 0)

    def test_common_acronyms_not_counted(self):
        content = ('API와 URL을 사용합니다. JSON 데이터를 처리합니다. HTTP 요청을 보냅니다.')
        result = analyze_concept_load(content)
        # 흔한 약어는 인지부하에 포함되지 않음
        self.assertEqual(result['summary']['overloaded_windows'], 0)

    def test_explanation_raises_threshold(self):
        content = ('레이턴시란 응답 시간을 의미합니다. '
                   '스루풋과 미들웨어를 설정합니다. '
                   '오케스트레이션을 구성합니다.')
        result = analyze_concept_load(content)
        # 설명이 있으면 임계값이 완화됨
        segments = result['overloaded_segments']
        if segments:
            self.assertTrue(segments[0]['has_explanation'])

    def test_max_concepts(self):
        content = ('레이턴시를 측정합니다. '
                   '스루풋을 확인합니다. '
                   '일반 문장입니다.')
        result = analyze_concept_load(content)
        self.assertGreaterEqual(result['summary']['max_concepts_in_window'], 0)

    def test_score_range(self):
        content = '일반적인 콘텐츠입니다.'
        result = analyze_concept_load(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인 테스트입니다.'
        result = analyze_concept_load(content)
        self.assertIn('score', result)
        self.assertIn('summary', result)
        self.assertIn('overloaded_segments', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_sentences', result['summary'])
        self.assertIn('max_concepts_in_window', result['summary'])
        self.assertIn('overloaded_windows', result['summary'])
        self.assertIn('level', result['summary'])

    def test_suggestions_for_overload(self):
        content = ('레이턴시와 스루풋을 측정합니다. '
                   '미들웨어와 오케스트레이션을 설정합니다. '
                   '프로비저닝과 컨테이너를 구성합니다.')
        result = analyze_concept_load(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_segment_details(self):
        content = ('레이턴시와 스루풋과 미들웨어와 오케스트레이션을 설명합니다. '
                   '프로비저닝과 컨테이너를 구성합니다. '
                   '클러스터와 파이프라인을 관리합니다.')
        result = analyze_concept_load(content)
        if result['overloaded_segments']:
            seg = result['overloaded_segments'][0]
            self.assertIn('concept_count', seg)
            self.assertIn('concepts', seg)
            self.assertIn('preview', seg)


if __name__ == '__main__':
    unittest.main()
