"""C2PA 스탬핑 서비스 테스트"""

import hashlib
import unittest
from services.c2pa_stamping_service import (
    C2PAManifest,
    create_manifest, add_action, verify_manifest,
    chain_manifests, export_manifest,
)


class TestC2PAStampingService(unittest.TestCase):
    """C2PA 스탬핑 서비스 테스트"""

    def test_create_manifest(self):
        """매니페스트 생성"""
        m = create_manifest("테스트 콘텐츠", "작성자", "InsightEngine")
        self.assertIsNotNone(m.manifest_id)
        self.assertEqual(m.creator, "작성자")
        self.assertEqual(m.tool, "InsightEngine")
        self.assertIn("created", m.actions)
        self.assertEqual(m.parent_hash, "")

    def test_create_manifest_hash(self):
        """해시 검증"""
        content = "테스트 콘텐츠"
        m = create_manifest(content, "작성자", "tool")
        expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        self.assertEqual(m.content_hash, expected_hash)

    def test_add_action(self):
        """행위 추가"""
        m = create_manifest("내용", "작성자", "tool")
        m = add_action(m, "edited")
        self.assertIn("edited", m.actions)
        self.assertIn("created", m.actions)

    def test_add_action_duplicate(self):
        """중복 행위는 무시"""
        m = create_manifest("내용", "작성자", "tool")
        m = add_action(m, "created")
        self.assertEqual(m.actions.count("created"), 1)

    def test_verify_manifest_valid(self):
        """유효한 콘텐츠 검증"""
        content = "원본 콘텐츠"
        m = create_manifest(content, "작성자", "tool")
        self.assertTrue(verify_manifest(m, content))

    def test_verify_manifest_tampered(self):
        """변조된 콘텐츠 검증 실패"""
        m = create_manifest("원본", "작성자", "tool")
        self.assertFalse(verify_manifest(m, "변조된 콘텐츠"))

    def test_chain_manifests(self):
        """부모-자식 체인"""
        parent = create_manifest("부모 콘텐츠", "작성자", "tool")
        child = chain_manifests(parent, "자식 콘텐츠")
        self.assertEqual(child.parent_hash, parent.content_hash)
        self.assertIn("derived", child.actions)
        self.assertNotEqual(child.manifest_id, parent.manifest_id)

    def test_chain_manifests_inherits_creator(self):
        """자식이 부모 크리에이터 상속"""
        parent = create_manifest("부모", "원작자", "도구A")
        child = chain_manifests(parent, "자식")
        self.assertEqual(child.creator, "원작자")
        self.assertEqual(child.tool, "도구A")

    def test_chain_manifests_custom_creator(self):
        """자식에 커스텀 크리에이터"""
        parent = create_manifest("부모", "원작자", "도구A")
        child = chain_manifests(parent, "자식", creator="편집자", tool="도구B")
        self.assertEqual(child.creator, "편집자")
        self.assertEqual(child.tool, "도구B")

    def test_export_manifest(self):
        """JSON 내보내기"""
        m = create_manifest("콘텐츠", "작성자", "tool")
        exported = export_manifest(m)
        self.assertEqual(exported["manifest_id"], m.manifest_id)
        self.assertEqual(exported["content_hash"], m.content_hash)
        self.assertEqual(exported["creator"], "작성자")
        self.assertIsInstance(exported["actions"], list)

    def test_export_manifest_fields(self):
        """내보내기 필드 완전성"""
        m = create_manifest("콘텐츠", "작성자", "tool")
        exported = export_manifest(m)
        expected_keys = {"manifest_id", "content_hash", "creator", "created_at", "tool", "actions", "parent_hash"}
        self.assertEqual(set(exported.keys()), expected_keys)

    def test_different_content_different_hash(self):
        """다른 콘텐츠는 다른 해시"""
        m1 = create_manifest("콘텐츠A", "작성자", "tool")
        m2 = create_manifest("콘텐츠B", "작성자", "tool")
        self.assertNotEqual(m1.content_hash, m2.content_hash)


if __name__ == "__main__":
    unittest.main()
