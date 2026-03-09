"""출처 서명(Provenance Stamp) 서비스 테스트."""
import unittest
from services.provenance_stamp_service import (
    stamp_provenance,
    verify_stamp,
    ProvenanceRecord,
    _encode_watermark,
    _decode_watermark,
    _strip_watermark,
    _compute_hash,
)


class TestStampProvenance(unittest.TestCase):
    """stamp_provenance 함수 테스트."""

    def test_basic_stamp(self):
        """기본 서명 생성."""
        record = stamp_provenance('테스트 콘텐츠')
        self.assertIsInstance(record, ProvenanceRecord)
        self.assertTrue(record.stamp_id)
        self.assertTrue(record.content_hash)
        self.assertEqual(record.author, 'AI')
        self.assertTrue(record.created_at)
        self.assertTrue(record.watermark)

    def test_custom_author_and_model(self):
        """커스텀 작성자 및 모델 지정."""
        record = stamp_provenance('콘텐츠', author='홍길동', model='gemini-2.5-flash')
        self.assertEqual(record.author, '홍길동')
        self.assertEqual(record.model, 'gemini-2.5-flash')

    def test_stamp_id_uniqueness(self):
        """동일 콘텐츠라도 stamp_id는 매번 다름."""
        r1 = stamp_provenance('같은 콘텐츠')
        r2 = stamp_provenance('같은 콘텐츠')
        self.assertNotEqual(r1.stamp_id, r2.stamp_id)

    def test_content_hash_consistency(self):
        """같은 콘텐츠는 같은 해시."""
        r1 = stamp_provenance('동일한 내용')
        r2 = stamp_provenance('동일한 내용')
        self.assertEqual(r1.content_hash, r2.content_hash)

    def test_content_hash_sha256_length(self):
        """해시가 SHA256 형식 (64자 hex)."""
        record = stamp_provenance('테스트')
        self.assertEqual(len(record.content_hash), 64)

    def test_watermark_is_invisible(self):
        """워터마크가 보이지 않는 문자로 구성."""
        record = stamp_provenance('콘텐츠')
        # 워터마크의 모든 문자가 zero-width 유니코드
        visible = [ch for ch in record.watermark if ch.isprintable() and not ch.isspace()]
        self.assertEqual(len(visible), 0)

    def test_different_content_different_hash(self):
        """다른 콘텐츠는 다른 해시."""
        r1 = stamp_provenance('콘텐츠 A')
        r2 = stamp_provenance('콘텐츠 B')
        self.assertNotEqual(r1.content_hash, r2.content_hash)


class TestVerifyStamp(unittest.TestCase):
    """verify_stamp 함수 테스트."""

    def test_verify_watermarked_content(self):
        """워터마크 삽입 후 검증."""
        original = '원본 콘텐츠입니다.'
        record = stamp_provenance(original)
        watermarked = original + record.watermark
        verified = verify_stamp(watermarked)
        self.assertIsNotNone(verified)
        self.assertEqual(verified.stamp_id, record.stamp_id)

    def test_verify_no_watermark(self):
        """워터마크 없는 콘텐츠는 None."""
        result = verify_stamp('일반 텍스트입니다.')
        self.assertIsNone(result)

    def test_verify_empty_content(self):
        """빈 콘텐츠는 None."""
        self.assertIsNone(verify_stamp(''))

    def test_verify_none_content(self):
        """None 입력은 None."""
        self.assertIsNone(verify_stamp(None))

    def test_verify_hash_matches_original(self):
        """검증 시 해시가 원본과 일치."""
        original = '해시 검증 테스트'
        record = stamp_provenance(original)
        watermarked = original + record.watermark
        verified = verify_stamp(watermarked)
        self.assertEqual(verified.content_hash, record.content_hash)

    def test_watermark_in_middle(self):
        """콘텐츠 중간에 워터마크를 삽입해도 검증 가능."""
        record = stamp_provenance('앞뒤 콘텐츠')
        content_with_wm = '앞 부분' + record.watermark + ' 뒤 부분'
        verified = verify_stamp(content_with_wm)
        self.assertIsNotNone(verified)
        self.assertEqual(verified.stamp_id, record.stamp_id)


class TestInternalFunctions(unittest.TestCase):
    """내부 헬퍼 함수 테스트."""

    def test_encode_decode_roundtrip(self):
        """인코딩 → 디코딩 왕복 테스트."""
        original_id = 'abc123def456'
        encoded = _encode_watermark(original_id)
        decoded = _decode_watermark(encoded)
        self.assertEqual(decoded, original_id)

    def test_encode_decode_korean(self):
        """한국어 포함 stamp_id 왕복."""
        original_id = 'test한글'
        encoded = _encode_watermark(original_id)
        decoded = _decode_watermark(encoded)
        self.assertEqual(decoded, original_id)

    def test_strip_watermark(self):
        """워터마크 문자 제거."""
        clean = '깨끗한 텍스트'
        watermark = _encode_watermark('testid')
        dirty = clean + watermark
        stripped = _strip_watermark(dirty)
        self.assertEqual(stripped, clean)

    def test_compute_hash_deterministic(self):
        """해시는 결정적."""
        h1 = _compute_hash('테스트')
        h2 = _compute_hash('테스트')
        self.assertEqual(h1, h2)

    def test_decode_empty_string(self):
        """빈 문자열 디코딩."""
        result = _decode_watermark('')
        self.assertEqual(result, '')


if __name__ == '__main__':
    unittest.main()
