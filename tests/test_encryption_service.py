"""encryption_service 단위 테스트"""
import unittest

from services.encryption_service import EncryptionService


class TestEncryptionService(unittest.TestCase):
    """AES-256-GCM / Fernet 암호화 테스트"""

    def setUp(self):
        self.svc = EncryptionService()

    def test_available(self):
        """cryptography 패키지 설치 확인"""
        self.assertTrue(self.svc.available)

    def test_encrypt_decrypt_roundtrip(self):
        """AES-256-GCM 암복호화 왕복"""
        plaintext = '비밀 메시지입니다 123'
        encrypted = self.svc.encrypt(plaintext)
        decrypted = self.svc.decrypt(encrypted)
        self.assertEqual(decrypted, plaintext)

    def test_encrypt_produces_different_ciphertexts(self):
        """같은 평문이라도 다른 암호문 (랜덤 nonce)"""
        e1 = self.svc.encrypt('동일 텍스트')
        e2 = self.svc.encrypt('동일 텍스트')
        self.assertNotEqual(e1, e2)

    def test_decrypt_tampered_raises(self):
        """변조된 암호문 복호화 시 ValueError"""
        encrypted = self.svc.encrypt('원본')
        tampered = encrypted[:-4] + 'XXXX'
        with self.assertRaises(ValueError):
            self.svc.decrypt(tampered)

    def test_fernet_roundtrip(self):
        """Fernet 암복호화 왕복"""
        plaintext = 'Fernet 테스트 문자열'
        token = self.svc.encrypt_fernet(plaintext)
        decrypted = self.svc.decrypt_fernet(token)
        self.assertEqual(decrypted, plaintext)

    def test_fernet_invalid_token_raises(self):
        """잘못된 Fernet 토큰 시 ValueError"""
        with self.assertRaises(ValueError):
            self.svc.decrypt_fernet('invalid-token')

    def test_hash_sensitive(self):
        """SHA-256 해시 생성"""
        h1 = self.svc.hash_sensitive('test@email.com')
        h2 = self.svc.hash_sensitive('test@email.com')
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)  # SHA-256 hex

    def test_hash_with_salt(self):
        """솔트 적용 시 다른 해시"""
        h1 = self.svc.hash_sensitive('data', salt='salt1')
        h2 = self.svc.hash_sensitive('data', salt='salt2')
        self.assertNotEqual(h1, h2)

    def test_empty_string_encrypt(self):
        """빈 문자열 암호화"""
        encrypted = self.svc.encrypt('')
        decrypted = self.svc.decrypt(encrypted)
        self.assertEqual(decrypted, '')


if __name__ == '__main__':
    unittest.main()
