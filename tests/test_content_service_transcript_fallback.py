import unittest


class TestTranscriptFallbackParsing(unittest.TestCase):
    def test_extract_yt_initial_player_response(self):
        from services import content_service

        html = """
        <html><head></head><body>
        <script>
        var ytInitialPlayerResponse = {"captions": {"playerCaptionsTracklistRenderer": {"captionTracks": [
            {"languageCode": "ko", "baseUrl": "https://example.com/timedtext?x=1"},
            {"languageCode": "en", "kind": "asr", "baseUrl": "https://example.com/timedtext?x=2"}
        ]}}};
        </script>
        </body></html>
        """

        player = content_service._extract_yt_initial_player_response(html)
        self.assertIsInstance(player, dict)
        tracks = content_service._extract_caption_tracks(player)
        self.assertEqual(len(tracks), 2)

    def test_pick_caption_track_prefers_ko_over_en_asr(self):
        from services import content_service

        tracks = [
            {"languageCode": "en", "kind": "asr", "baseUrl": "https://example.com/en"},
            {"languageCode": "ko", "baseUrl": "https://example.com/ko"},
        ]

        picked = content_service._pick_caption_track(tracks, preferred=("ko", "en"))
        self.assertEqual(picked.get("languageCode"), "ko")

    def test_parse_vtt(self):
        from services import content_service

        vtt = """WEBVTT

        00:00:00.000 --> 00:00:01.000
        안녕하세요

        00:00:01.000 --> 00:00:02.000
        반갑습니다
        """

        parsed = content_service._parse_vtt(vtt)
        self.assertIn("안녕하세요", parsed)
        self.assertIn("반갑습니다", parsed)

    def test_parse_timedtext_xml(self):
        from services import content_service

        xml = """<?xml version='1.0' encoding='utf-8'?>
        <transcript>
          <text start="0" dur="1">안녕하세요</text>
          <text start="1" dur="1">반갑습니다</text>
        </transcript>
        """

        parsed = content_service._parse_timedtext_xml(xml)
        self.assertIn("안녕하세요", parsed)
        self.assertIn("반갑습니다", parsed)


if __name__ == "__main__":
    unittest.main()
