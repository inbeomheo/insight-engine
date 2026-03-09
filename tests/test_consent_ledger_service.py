"""동의 원장 서비스 테스트."""

import unittest
from services.consent_ledger_service import (
    ConsentRecord,
    ConsentLedger,
    record_consent,
    get_current_consents,
    check_consent,
    get_audit_trail,
    verify_integrity,
)


class TestConsentLedgerService(unittest.TestCase):
    """ConsentLedgerService 단위 테스트."""

    def _empty_ledger(self) -> ConsentLedger:
        return ConsentLedger(ledger_id="test_ledger", records=[])

    def test_record_consent_adds_record(self):
        """동의 기록이 추가된다."""
        ledger = self._empty_ledger()
        updated = record_consent(ledger, "user1", "marketing", True, "127.0.0.1")
        self.assertEqual(len(updated.records), 1)
        self.assertEqual(updated.records[0].user_id, "user1")
        self.assertTrue(updated.records[0].granted)

    def test_record_consent_hashes_ip(self):
        """IP가 SHA256으로 해시된다."""
        ledger = self._empty_ledger()
        updated = record_consent(ledger, "user1", "analytics", True, "192.168.1.1")
        # SHA256 해시는 64자
        self.assertEqual(len(updated.records[0].ip_hash), 64)
        # 원본 IP는 아님
        self.assertNotEqual(updated.records[0].ip_hash, "192.168.1.1")

    def test_record_consent_same_ip_same_hash(self):
        """같은 IP는 같은 해시를 생성한다."""
        ledger = self._empty_ledger()
        l1 = record_consent(ledger, "u1", "marketing", True, "10.0.0.1")
        l2 = record_consent(l1, "u2", "marketing", True, "10.0.0.1")
        self.assertEqual(l2.records[0].ip_hash, l2.records[1].ip_hash)

    def test_record_consent_preserves_previous(self):
        """기존 기록이 보존된다."""
        ledger = self._empty_ledger()
        l1 = record_consent(ledger, "u1", "marketing", True, "1.1.1.1")
        l2 = record_consent(l1, "u1", "analytics", True, "1.1.1.1")
        self.assertEqual(len(l2.records), 2)

    def test_get_current_consents(self):
        """최신 동의 상태를 반환한다."""
        ledger = self._empty_ledger()
        l1 = record_consent(ledger, "u1", "marketing", True, "1.1.1.1")
        l2 = record_consent(l1, "u1", "analytics", False, "1.1.1.1")
        consents = get_current_consents(l2, "u1")
        self.assertTrue(consents["marketing"])
        self.assertFalse(consents["analytics"])

    def test_get_current_consents_override(self):
        """나중 기록이 이전 기록을 덮어쓴다."""
        ledger = self._empty_ledger()
        l1 = record_consent(ledger, "u1", "marketing", True, "1.1.1.1")
        l2 = record_consent(l1, "u1", "marketing", False, "1.1.1.1")
        consents = get_current_consents(l2, "u1")
        self.assertFalse(consents["marketing"])

    def test_get_current_consents_empty(self):
        """기록 없는 사용자는 빈 딕셔너리."""
        ledger = self._empty_ledger()
        self.assertEqual(get_current_consents(ledger, "u_unknown"), {})

    def test_check_consent_true(self):
        """동의한 유형은 True."""
        ledger = self._empty_ledger()
        l1 = record_consent(ledger, "u1", "data_collection", True, "1.1.1.1")
        self.assertTrue(check_consent(l1, "u1", "data_collection"))

    def test_check_consent_false(self):
        """동의하지 않은 유형은 False."""
        ledger = self._empty_ledger()
        l1 = record_consent(ledger, "u1", "marketing", False, "1.1.1.1")
        self.assertFalse(check_consent(l1, "u1", "marketing"))

    def test_check_consent_missing_type(self):
        """기록 없는 유형은 False."""
        ledger = self._empty_ledger()
        self.assertFalse(check_consent(ledger, "u1", "third_party"))

    def test_get_audit_trail(self):
        """감사 추적이 올바르게 반환된다."""
        ledger = self._empty_ledger()
        l1 = record_consent(ledger, "u1", "marketing", True, "1.1.1.1")
        l2 = record_consent(l1, "u2", "marketing", True, "2.2.2.2")
        l3 = record_consent(l2, "u1", "analytics", True, "1.1.1.1")

        trail = get_audit_trail(l3, "u1")
        self.assertEqual(len(trail), 2)
        self.assertTrue(all(r.user_id == "u1" for r in trail))

    def test_verify_integrity_valid(self):
        """시간 순서가 올바르면 무결성 통과."""
        ledger = self._empty_ledger()
        l1 = record_consent(ledger, "u1", "marketing", True, "1.1.1.1")
        l2 = record_consent(l1, "u1", "analytics", True, "1.1.1.1")
        self.assertTrue(verify_integrity(l2))

    def test_verify_integrity_empty(self):
        """빈 원장은 무결성 통과."""
        self.assertTrue(verify_integrity(self._empty_ledger()))

    def test_verify_integrity_single_record(self):
        """단일 레코드 원장은 무결성 통과."""
        ledger = self._empty_ledger()
        l1 = record_consent(ledger, "u1", "marketing", True, "1.1.1.1")
        self.assertTrue(verify_integrity(l1))

    def test_verify_integrity_tampered(self):
        """시간 순서가 변조되면 무결성 실패."""
        r1 = ConsentRecord("r1", "u1", "marketing", True, "2026-03-10T10:00:00", "hash1", "1.0")
        r2 = ConsentRecord("r2", "u1", "analytics", True, "2026-03-09T10:00:00", "hash2", "1.0")
        ledger = ConsentLedger(ledger_id="test", records=[r1, r2])
        self.assertFalse(verify_integrity(ledger))

    def test_record_consent_version(self):
        """버전 정보가 기록된다."""
        ledger = self._empty_ledger()
        l1 = record_consent(ledger, "u1", "marketing", True, "1.1.1.1", version="2.0")
        self.assertEqual(l1.records[0].version, "2.0")

    def test_record_consent_record_id_format(self):
        """레코드 ID 형식이 cr_ 접두사."""
        ledger = self._empty_ledger()
        l1 = record_consent(ledger, "u1", "marketing", True, "1.1.1.1")
        self.assertTrue(l1.records[0].record_id.startswith("cr_"))


if __name__ == "__main__":
    unittest.main()
