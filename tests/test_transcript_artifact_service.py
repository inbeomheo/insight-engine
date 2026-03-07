"""
자막 아티팩트 감지 서비스 테스트
"""
import unittest
from services.transcript_artifact_service import detect_transcript_artifacts


class TestTranscriptArtifactService(unittest.TestCase):
    """detect_transcript_artifacts 함수의 단위 테스트."""

    # --- 1. 빈 입력 ---
    def test_empty_content(self):
        """빈 문자열 입력 시 빈 결과와 100점 반환."""
        result = detect_transcript_artifacts('')
        self.assertEqual(result['artifacts'], [])
        self.assertEqual(result['summary']['total'], 0)
        self.assertEqual(result['clean_score'], 100.0)

        # None 입력
        result_none = detect_transcript_artifacts(None)
        self.assertEqual(result_none['artifacts'], [])

    # --- 2. 인사말 감지 ---
    def test_greeting_detection(self):
        """한국어/영어 인사말 패턴을 감지한다."""
        content = '안녕하세요 여러분. 오늘은 파이썬에 대해 알아보겠습니다.'
        result = detect_transcript_artifacts(content)

        greeting_artifacts = [a for a in result['artifacts'] if a['type'] == 'greeting']
        self.assertGreaterEqual(len(greeting_artifacts), 1)
        # '안녕하세요' 또는 '여러분'이 감지되어야 함
        detected_texts = [a['text'] for a in greeting_artifacts]
        self.assertTrue(
            any('안녕하세요' in t or '여러분' in t for t in detected_texts)
        )

    # --- 3. 구독 CTA 감지 ---
    def test_subscribe_cta_detection(self):
        """구독/좋아요/알림 요청 패턴을 감지한다."""
        content = '이 영상이 도움이 되셨다면 구독과 좋아요 부탁드립니다.'
        result = detect_transcript_artifacts(content)

        cta_artifacts = [a for a in result['artifacts'] if a['type'] == 'subscribe_cta']
        self.assertGreaterEqual(len(cta_artifacts), 1)

    # --- 4. 스폰서 감지 ---
    def test_sponsor_detection(self):
        """스폰서/협찬/광고 멘트를 감지한다."""
        content = '이 영상은 ABC 회사의 후원으로 제작되었습니다. 스폰서 감사합니다.'
        result = detect_transcript_artifacts(content)

        sponsor_artifacts = [a for a in result['artifacts'] if a['type'] == 'sponsor']
        self.assertGreaterEqual(len(sponsor_artifacts), 1)

    # --- 5. 말더듬/필러 감지 ---
    def test_filler_speech_detection(self):
        """말더듬(음, 어, um, uh 등) 패턴을 감지한다."""
        content = '음 그래서 어 이 부분은 um 중요한데요.'
        result = detect_transcript_artifacts(content)

        filler_artifacts = [a for a in result['artifacts'] if a['type'] == 'filler_speech']
        self.assertGreaterEqual(len(filler_artifacts), 1)

    # --- 6. 자기 참조 감지 ---
    def test_self_reference_detection(self):
        """채널/영상 자기 참조 패턴을 감지한다."""
        content = '제 채널에서 이전 영상을 확인해보세요. 링크는 설명란에 있습니다.'
        result = detect_transcript_artifacts(content)

        ref_artifacts = [a for a in result['artifacts'] if a['type'] == 'self_reference']
        self.assertGreaterEqual(len(ref_artifacts), 1)

    # --- 7. 타임스탬프 마커 감지 ---
    def test_timestamp_marker_detection(self):
        """[MM:SS] 또는 (MM:SS) 형식 타임스탬프를 감지한다."""
        content = '[00:00] 시작 부분입니다. 다음 섹션은 (12:34)에 있습니다.'
        result = detect_transcript_artifacts(content)

        ts_artifacts = [a for a in result['artifacts'] if a['type'] == 'timestamp_marker']
        self.assertGreaterEqual(len(ts_artifacts), 1)

    # --- 8. removable 플래그 ---
    def test_removable_flag(self):
        """greeting, subscribe_cta, sponsor, timestamp는 removable=True,
        filler_speech, self_reference는 removable=False."""
        content = (
            '안녕하세요 여러분. '
            '구독 부탁드립니다. '
            '이 영상은 스폰서의 협찬입니다. '
            '음 어 그러니까. '
            '제 채널을 방문해주세요. '
            '[00:00] 시작.'
        )
        result = detect_transcript_artifacts(content)

        for a in result['artifacts']:
            if a['type'] in ('greeting', 'subscribe_cta', 'sponsor', 'timestamp_marker'):
                self.assertTrue(a['removable'], f"{a['type']}는 removable=True여야 합니다")
            elif a['type'] in ('filler_speech', 'self_reference'):
                self.assertFalse(a['removable'], f"{a['type']}는 removable=False여야 합니다")

    # --- 9. 클린 스코어 범위 ---
    def test_clean_score_range(self):
        """clean_score는 0~100 범위여야 한다."""
        # 아티팩트 많은 콘텐츠
        dirty = '안녕하세요. 구독. 좋아요. 알림. 스폰서. 협찬. 광고. 음. 어. 그. [00:00]. (01:23). 제 채널.'
        result = detect_transcript_artifacts(dirty)

        self.assertGreaterEqual(result['clean_score'], 0.0)
        self.assertLessEqual(result['clean_score'], 100.0)

    # --- 10. 깨끗한 콘텐츠 ---
    def test_clean_content(self):
        """아티팩트가 없는 순수 콘텐츠는 빈 artifacts와 100점."""
        content = '파이썬은 인터프리터 언어입니다. 동적 타이핑을 지원하며 문법이 간결합니다.'
        result = detect_transcript_artifacts(content)

        self.assertEqual(result['artifacts'], [])
        self.assertEqual(result['summary']['total'], 0)
        self.assertEqual(result['clean_score'], 100.0)

    # --- 11. 아티팩트 비율 ---
    def test_artifact_ratio(self):
        """artifact_ratio는 감지 수 / 전체 문장 수."""
        content = '안녕하세요. 오늘 주제는 AI입니다. 구독 부탁합니다. 감사합니다.'
        result = detect_transcript_artifacts(content)

        total = result['summary']['total']
        ratio = result['summary']['artifact_ratio']
        # ratio는 0 이상이어야 함
        self.assertGreaterEqual(ratio, 0.0)
        # total이 0이 아니면 ratio도 0보다 커야 함
        if total > 0:
            self.assertGreater(ratio, 0.0)

    # --- 12. 복합 아티팩트 ---
    def test_mixed_artifacts(self):
        """여러 타입의 아티팩트가 동시에 감지된다."""
        content = (
            '안녕하세요 여러분. '
            '오늘은 머신러닝에 대해 알아봅니다. '
            '구독과 좋아요 눌러주세요. '
            '이 영상은 ABC사 후원으로 제작되었습니다. '
            '음 그래서 핵심은. '
            '제 채널의 이전 영상도 참고하세요. '
            '[03:45] 여기서부터 실습입니다.'
        )
        result = detect_transcript_artifacts(content)

        detected_types = set(a['type'] for a in result['artifacts'])
        # 최소 4가지 이상의 타입이 감지되어야 함
        self.assertGreaterEqual(len(detected_types), 4)

        # summary.by_type에 각 타입별 카운트가 있어야 함
        self.assertIsInstance(result['summary']['by_type'], dict)
        self.assertGreater(result['summary']['total'], 0)

        # suggestions가 비어있지 않아야 함
        self.assertGreater(len(result['suggestions']), 0)

    # --- 13. 영어 콘텐츠 감지 ---
    def test_english_artifacts(self):
        """영어 아티팩트도 올바르게 감지된다."""
        content = 'Hi everyone, welcome to my channel. Please subscribe and hit the bell.'
        result = detect_transcript_artifacts(content)

        detected_types = set(a['type'] for a in result['artifacts'])
        self.assertIn('greeting', detected_types)
        self.assertIn('subscribe_cta', detected_types)

    # --- 14. HH:MM:SS 타임스탬프 ---
    def test_timestamp_hhmmss(self):
        """HH:MM:SS 형식 타임스탬프도 감지된다."""
        content = '이 부분은 1:23:45에서 설명합니다.'
        result = detect_transcript_artifacts(content)

        ts_artifacts = [a for a in result['artifacts'] if a['type'] == 'timestamp_marker']
        self.assertGreaterEqual(len(ts_artifacts), 1)


if __name__ == '__main__':
    unittest.main()
