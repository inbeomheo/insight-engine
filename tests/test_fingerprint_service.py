"""fingerprint_service 단위 테스트"""
import unittest

from services.fingerprint_service import (
    FingerprintService, _encode_bits, _decode_bits
)


class TestBitEncoding(unittest.TestCase):
    """제로폭 문자 인코딩/디코딩 테스트"""

    def test_roundtrip(self):
        """인코딩 → 디코딩 왕복"""
        data = 'hello'
        encoded = _encode_bits(data)
        decoded = _decode_bits(encoded)
        self.assertEqual(decoded, data)

    def test_no_marker_returns_none(self):
        """마커 없으면 None"""
        self.assertIsNone(_decode_bits('일반 텍스트'))

    def test_max_32_chars(self):
        """32자 초과 데이터 잘림"""
        long_data = 'A' * 50
        encoded = _encode_bits(long_data)
        decoded = _decode_bits(encoded)
        self.assertEqual(len(decoded), 32)


class TestFingerprintService(unittest.TestCase):
    """FingerprintService 테스트"""

    def setUp(self):
        self.svc = FingerprintService()

    def test_embed_and_extract(self):
        """지문 삽입 + 추출"""
        content = '첫 번째 단락입니다.\n\n두 번째 단락입니다.'
        watermarked, fp_id = self.svc.embed(content, 'user1', 'content1', timestamp=1000.0)
        extracted = self.svc.extract(watermarked)
        self.assertIsNotNone(extracted)
        self.assertEqual(extracted, fp_id[:12])

    def test_verify_success(self):
        """지문 검증 성공"""
        content = '테스트 콘텐츠입니다.'
        watermarked, fp_id = self.svc.embed(content, 'user1', timestamp=1000.0)
        self.assertTrue(self.svc.verify(watermarked, fp_id))

    def test_verify_fail(self):
        """지문 검증 실패"""
        content = '테스트 콘텐츠입니다.'
        watermarked, _ = self.svc.embed(content, 'user1', timestamp=1000.0)
        self.assertFalse(self.svc.verify(watermarked, 'wrong_fingerprint_id'))

    def test_extract_from_clean_content(self):
        """지문 없는 콘텐츠에서 추출 시 None"""
        self.assertIsNone(self.svc.extract('일반 텍스트입니다.'))

    def test_hash_content_ignores_fingerprint(self):
        """해시는 지문 제거 후 계산"""
        content = '동일한 콘텐츠'
        watermarked, _ = self.svc.embed(content, 'user1', timestamp=1000.0)
        h1 = self.svc.hash_content(content)
        h2 = self.svc.hash_content(watermarked)
        self.assertEqual(h1, h2)

    def test_strip_fingerprint(self):
        """지문 제거 후 원본 복원"""
        content = '원본 텍스트'
        watermarked, _ = self.svc.embed(content, 'user1', timestamp=1000.0)
        stripped = self.svc.strip_fingerprint(watermarked)
        self.assertEqual(stripped, content)

    def test_different_users_different_fingerprints(self):
        """다른 사용자 → 다른 지문"""
        content = '콘텐츠'
        _, fp1 = self.svc.embed(content, 'user1', timestamp=1000.0)
        _, fp2 = self.svc.embed(content, 'user2', timestamp=1000.0)
        self.assertNotEqual(fp1, fp2)


if __name__ == '__main__':
    unittest.main()
