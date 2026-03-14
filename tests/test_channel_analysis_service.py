"""channel_analysis_service 단위 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.content.channel_analysis_service import (
    _extract_channel_id,
    _compute_stats,
    _cluster_topics,
    analyze_channel,
    _API_BASE,
    _REQUEST_TIMEOUT,
)


class TestConstants(unittest.TestCase):

    def test_api_base(self):
        """API 베이스 URL"""
        self.assertIn('googleapis.com', _API_BASE)

    def test_timeout(self):
        """요청 타임아웃"""
        self.assertEqual(_REQUEST_TIMEOUT, 15)


class TestExtractChannelId(unittest.TestCase):

    def test_channel_url(self):
        """/channel/UC... 패턴"""
        url = 'https://www.youtube.com/channel/UCabcDEF123'
        self.assertEqual(_extract_channel_id(url), 'UCabcDEF123')

    def test_handle_url(self):
        """/@handle 패턴 → _resolve_channel_id 호출"""
        with patch('services.channel_analysis_service._resolve_channel_id', return_value='UC_resolved') as mock:
            result = _extract_channel_id('https://www.youtube.com/@testhandle')
        self.assertEqual(result, 'UC_resolved')
        mock.assert_called_once_with('testhandle')

    def test_custom_url(self):
        """/c/customname 패턴"""
        with patch('services.channel_analysis_service._resolve_channel_id', return_value='UC_custom') as mock:
            result = _extract_channel_id('https://www.youtube.com/c/MyChannel')
        self.assertEqual(result, 'UC_custom')
        mock.assert_called_once_with('MyChannel')

    def test_invalid_url(self):
        """유효하지 않은 URL → None"""
        result = _extract_channel_id('https://example.com/page')
        self.assertIsNone(result)

    def test_channel_id_with_dash(self):
        """하이픈 포함 채널 ID"""
        url = 'https://youtube.com/channel/UC-abc_DEF123'
        self.assertEqual(_extract_channel_id(url), 'UC-abc_DEF123')


class TestComputeStats(unittest.TestCase):

    def test_basic_stats(self):
        """기본 통계 계산"""
        channel_info = {
            'video_count': 100,
            'view_count': 500000,
            'subscriber_count': 10000,
        }
        videos = [
            {'view_count': 1000},
            {'view_count': 2000},
            {'view_count': 3000},
        ]
        stats = _compute_stats(channel_info, videos)
        self.assertEqual(stats['total_videos'], 100)
        self.assertEqual(stats['total_views'], 500000)
        self.assertEqual(stats['subscriber_count'], 10000)
        self.assertEqual(stats['recent_video_count'], 3)
        self.assertEqual(stats['avg_views_recent'], 2000)

    def test_empty_videos(self):
        """영상 없음 → 평균 0"""
        stats = _compute_stats({'video_count': 0, 'view_count': 0, 'subscriber_count': 0}, [])
        self.assertEqual(stats['avg_views_recent'], 0)
        self.assertEqual(stats['recent_video_count'], 0)

    def test_videos_with_zero_views(self):
        """조회수 0인 영상만"""
        stats = _compute_stats(
            {'video_count': 1, 'view_count': 0, 'subscriber_count': 0},
            [{'view_count': 0}],
        )
        self.assertEqual(stats['avg_views_recent'], 0)


class TestClusterTopics(unittest.TestCase):

    def test_basic_clustering(self):
        """기본 키워드 클러스터링"""
        videos = [
            {'title': '파이썬 기초 강의', 'description': '파이썬 입문'},
            {'title': '파이썬 고급 문법', 'description': '고급 파이썬'},
            {'title': '자바스크립트 튜토리얼', 'description': 'JS 강의'},
        ]
        clusters = _cluster_topics(videos, top_n=3)
        self.assertGreater(len(clusters), 0)
        # 파이썬이 가장 많이 언급
        self.assertEqual(clusters[0]['topic'], '파이썬')

    def test_empty_videos(self):
        """빈 영상 목록"""
        clusters = _cluster_topics([], top_n=5)
        self.assertEqual(clusters, [])

    def test_cluster_has_ratio(self):
        """클러스터에 ratio 필드"""
        videos = [{'title': '테스트 코드 작성법', 'description': ''}]
        clusters = _cluster_topics(videos, top_n=3)
        for c in clusters:
            self.assertIn('ratio', c)
            self.assertIn('count', c)

    def test_stopwords_filtered(self):
        """불용어 필터링"""
        videos = [{'title': 'the and for with this that', 'description': ''}]
        clusters = _cluster_topics(videos, top_n=5)
        topics = [c['topic'] for c in clusters]
        self.assertNotIn('the', topics)
        self.assertNotIn('and', topics)


class TestAnalyzeChannel(unittest.TestCase):

    @patch('services.channel_analysis_service.YOUTUBE_API_KEY', '')
    def test_no_api_key(self):
        """API 키 없음 → ValueError"""
        with self.assertRaises(ValueError) as ctx:
            analyze_channel('https://youtube.com/channel/UCtest')
        self.assertIn('YOUTUBE_API_KEY', str(ctx.exception))

    @patch('services.channel_analysis_service.YOUTUBE_API_KEY', 'test-key')
    @patch('services.channel_analysis_service._extract_channel_id', return_value=None)
    def test_invalid_url(self, mock_extract):
        """유효하지 않은 URL → ValueError"""
        with self.assertRaises(ValueError) as ctx:
            analyze_channel('https://invalid.com')
        self.assertIn('유효하지 않은', str(ctx.exception))

    @patch('services.channel_analysis_service.YOUTUBE_API_KEY', 'test-key')
    @patch('services.channel_analysis_service._cluster_topics', return_value=[])
    @patch('services.channel_analysis_service._get_recent_videos', return_value=[])
    @patch('services.channel_analysis_service._get_channel_info', return_value={'title': '테스트 채널', 'video_count': 10, 'view_count': 1000, 'subscriber_count': 100})
    @patch('services.channel_analysis_service._extract_channel_id', return_value='UC_test')
    def test_success(self, mock_extract, mock_info, mock_videos, mock_cluster):
        """정상 분석"""
        result = analyze_channel('https://youtube.com/channel/UC_test')
        self.assertEqual(result['channel_name'], '테스트 채널')
        self.assertIn('stats', result)
        self.assertIn('topic_clusters', result)
        self.assertIn('recent_videos', result)


if __name__ == '__main__':
    unittest.main()
