"""YouTube 채널 분석 서비스 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.channel_analysis_service import (
    analyze_channel,
    _extract_channel_id,
    _cluster_topics,
    _compute_stats,
)


class TestExtractChannelId(unittest.TestCase):
    """채널 URL에서 ID 추출 테스트"""

    def test_direct_channel_id(self):
        """직접 channel ID가 포함된 URL"""
        url = 'https://www.youtube.com/channel/UCxxxxxxxxxxxxxxxxxxxxxx'
        result = _extract_channel_id(url)
        self.assertEqual(result, 'UCxxxxxxxxxxxxxxxxxxxxxx')

    @patch('services.channel_analysis_service._resolve_channel_id')
    def test_handle_url(self, mock_resolve):
        """@handle URL에서 채널 ID 변환"""
        mock_resolve.return_value = 'UC_resolved_id'
        url = 'https://www.youtube.com/@testchannel'
        result = _extract_channel_id(url)
        mock_resolve.assert_called_once_with('testchannel')
        self.assertEqual(result, 'UC_resolved_id')

    def test_invalid_url(self):
        """유효하지 않은 URL은 None 반환"""
        result = _extract_channel_id('https://example.com/not-youtube')
        self.assertIsNone(result)


class TestClusterTopics(unittest.TestCase):
    """주제 클러스터링 테스트"""

    def test_basic_clustering(self):
        """제목에서 키워드를 추출하여 클러스터를 생성합니다."""
        videos = [
            {'title': '파이썬 기초 강좌', 'description': '파이썬 입문'},
            {'title': '파이썬 웹 개발', 'description': '장고 프레임워크'},
            {'title': '자바스크립트 기초', 'description': 'React 강좌'},
            {'title': '파이썬 데이터 분석', 'description': '판다스 활용'},
        ]
        clusters = _cluster_topics(videos, top_n=3)

        self.assertGreater(len(clusters), 0)
        # 파이썬이 가장 빈도 높아야 함
        self.assertEqual(clusters[0]['topic'], '파이썬')
        self.assertGreater(clusters[0]['count'], 1)

    def test_empty_videos(self):
        """빈 영상 목록은 빈 클러스터를 반환합니다."""
        clusters = _cluster_topics([], top_n=5)
        self.assertEqual(clusters, [])

    def test_ratio_sums_to_one(self):
        """ratio 합이 약 1.0"""
        videos = [
            {'title': 'React 튜토리얼', 'description': '프론트엔드'},
            {'title': 'React 고급 패턴', 'description': '컴포넌트'},
            {'title': 'Vue 입문', 'description': '프론트엔드'},
        ]
        clusters = _cluster_topics(videos, top_n=5)
        total = sum(c['ratio'] for c in clusters)
        self.assertAlmostEqual(total, 1.0, places=1)


class TestComputeStats(unittest.TestCase):
    """통계 계산 테스트"""

    def test_basic_stats(self):
        """채널 정보와 영상 목록에서 통계를 계산합니다."""
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
        self.assertEqual(stats['subscriber_count'], 10000)
        self.assertEqual(stats['avg_views_recent'], 2000)
        self.assertEqual(stats['recent_video_count'], 3)

    def test_no_videos(self):
        """영상이 없으면 평균 조회수 0"""
        channel_info = {'video_count': 0, 'view_count': 0, 'subscriber_count': 0}
        stats = _compute_stats(channel_info, [])
        self.assertEqual(stats['avg_views_recent'], 0)


class TestAnalyzeChannel(unittest.TestCase):
    """analyze_channel 통합 테스트"""

    def test_no_api_key(self):
        """API 키가 없으면 ValueError 발생"""
        with patch('services.channel_analysis_service.YOUTUBE_API_KEY', ''):
            with self.assertRaises(ValueError) as ctx:
                analyze_channel('https://www.youtube.com/channel/UCtest')
            self.assertIn('YOUTUBE_API_KEY', str(ctx.exception))

    @patch('services.channel_analysis_service._get_video_stats')
    @patch('services.channel_analysis_service.requests.get')
    @patch('services.channel_analysis_service.YOUTUBE_API_KEY', 'test-key')
    def test_full_analysis(self, mock_get, mock_stats):
        """전체 분석 플로우를 모킹하여 테스트합니다."""
        # 채널 정보 API 응답
        channel_resp = MagicMock()
        channel_resp.json.return_value = {
            'items': [{
                'id': 'UCtest',
                'snippet': {'title': '테스트 채널', 'description': '설명'},
                'statistics': {
                    'subscriberCount': '5000',
                    'videoCount': '50',
                    'viewCount': '100000',
                },
            }]
        }
        channel_resp.raise_for_status = MagicMock()

        # 검색 API 응답 (최근 영상)
        search_resp = MagicMock()
        search_resp.json.return_value = {
            'items': [
                {
                    'id': {'videoId': 'vid1'},
                    'snippet': {
                        'title': '파이썬 기초',
                        'description': '입문 강좌',
                        'publishedAt': '2024-01-01T00:00:00Z',
                    },
                },
                {
                    'id': {'videoId': 'vid2'},
                    'snippet': {
                        'title': '파이썬 고급',
                        'description': '심화 강좌',
                        'publishedAt': '2024-01-02T00:00:00Z',
                    },
                },
            ]
        }
        search_resp.raise_for_status = MagicMock()

        mock_get.side_effect = [channel_resp, search_resp]
        mock_stats.return_value = {
            'vid1': {'viewCount': 1000, 'likeCount': 50},
            'vid2': {'viewCount': 2000, 'likeCount': 100},
        }

        result = analyze_channel('https://www.youtube.com/channel/UCtest')

        self.assertEqual(result['channel_name'], '테스트 채널')
        self.assertEqual(result['stats']['total_videos'], 50)
        self.assertEqual(result['stats']['subscriber_count'], 5000)
        self.assertEqual(len(result['recent_videos']), 2)
        self.assertIsInstance(result['topic_clusters'], list)


if __name__ == '__main__':
    unittest.main()
