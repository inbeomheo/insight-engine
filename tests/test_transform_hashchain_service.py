"""변환 해시체인 서비스 테스트."""

import unittest
from services.transform_hashchain_service import (
    ChainBlock,
    HashChain,
    create_chain,
    add_transform,
    verify_chain,
    get_transform_history,
)


class TestTransformHashchainService(unittest.TestCase):
    """TransformHashchainService 단위 테스트."""

    def test_create_chain_genesis_block(self):
        """제네시스 블록으로 체인이 생성된다."""
        chain = create_chain("초기 콘텐츠")
        self.assertIsInstance(chain, HashChain)
        self.assertEqual(len(chain.blocks), 1)
        self.assertEqual(chain.blocks[0].transform_type, "genesis")
        self.assertEqual(chain.blocks[0].prev_hash, "0" * 64)

    def test_create_chain_id_format(self):
        """체인 ID가 hc_ 접두사."""
        chain = create_chain("test")
        self.assertTrue(chain.chain_id.startswith("hc_"))

    def test_create_chain_content_hash(self):
        """콘텐츠 해시가 생성된다."""
        chain = create_chain("test")
        self.assertEqual(len(chain.blocks[0].content_hash), 64)

    def test_create_chain_same_content_same_hash(self):
        """같은 콘텐츠는 같은 해시."""
        c1 = create_chain("identical")
        c2 = create_chain("identical")
        self.assertEqual(c1.blocks[0].content_hash, c2.blocks[0].content_hash)

    def test_create_chain_different_content_different_hash(self):
        """다른 콘텐츠는 다른 해시."""
        c1 = create_chain("content A")
        c2 = create_chain("content B")
        self.assertNotEqual(c1.blocks[0].content_hash, c2.blocks[0].content_hash)

    def test_add_transform_appends_block(self):
        """변환 블록이 추가된다."""
        chain = create_chain("원본")
        updated = add_transform(chain, "수정본", "edit")
        self.assertEqual(len(updated.blocks), 2)
        self.assertEqual(updated.blocks[1].transform_type, "edit")

    def test_add_transform_links_hash(self):
        """새 블록의 prev_hash가 이전 블록의 content_hash와 일치."""
        chain = create_chain("원본")
        updated = add_transform(chain, "수정본", "translate")
        self.assertEqual(updated.blocks[1].prev_hash, updated.blocks[0].content_hash)

    def test_add_transform_multiple(self):
        """여러 변환을 연속 추가할 수 있다."""
        chain = create_chain("v1")
        chain = add_transform(chain, "v2", "edit")
        chain = add_transform(chain, "v3", "translate")
        chain = add_transform(chain, "v4", "format")
        self.assertEqual(len(chain.blocks), 4)

    def test_add_transform_preserves_chain_id(self):
        """변환 추가 후 체인 ID가 보존된다."""
        chain = create_chain("test")
        original_id = chain.chain_id
        updated = add_transform(chain, "new", "edit")
        self.assertEqual(updated.chain_id, original_id)

    def test_verify_chain_valid(self):
        """유효한 체인은 True."""
        chain = create_chain("원본")
        chain = add_transform(chain, "수정1", "edit")
        chain = add_transform(chain, "수정2", "translate")
        self.assertTrue(verify_chain(chain))

    def test_verify_chain_empty(self):
        """빈 체인은 True."""
        chain = HashChain(chain_id="empty", blocks=[])
        self.assertTrue(verify_chain(chain))

    def test_verify_chain_single_block(self):
        """단일 블록 체인은 True."""
        chain = create_chain("단일")
        self.assertTrue(verify_chain(chain))

    def test_verify_chain_tampered(self):
        """해시가 변조되면 False."""
        chain = create_chain("원본")
        chain = add_transform(chain, "수정", "edit")

        # 중간 블록의 content_hash 변조
        chain.blocks[0].content_hash = "tampered_hash"
        self.assertFalse(verify_chain(chain))

    def test_verify_chain_genesis_tampered(self):
        """제네시스 블록의 prev_hash가 변조되면 False."""
        chain = create_chain("test")
        chain.blocks[0].prev_hash = "not_zero"
        self.assertFalse(verify_chain(chain))

    def test_get_transform_history(self):
        """변환 이력을 반환한다."""
        chain = create_chain("초기")
        chain = add_transform(chain, "편집", "edit")
        chain = add_transform(chain, "번역", "translate")

        history = get_transform_history(chain)
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0]["transform_type"], "genesis")
        self.assertEqual(history[1]["transform_type"], "edit")
        self.assertEqual(history[2]["transform_type"], "translate")

    def test_get_transform_history_has_timestamp(self):
        """이력에 타임스탬프가 포함된다."""
        chain = create_chain("test")
        history = get_transform_history(chain)
        self.assertIn("timestamp", history[0])

    def test_get_transform_history_has_metadata(self):
        """이력에 메타데이터가 포함된다."""
        chain = create_chain("test")
        history = get_transform_history(chain)
        self.assertIn("metadata", history[0])

    def test_add_transform_custom_metadata(self):
        """커스텀 메타데이터를 전달할 수 있다."""
        chain = create_chain("test")
        meta = {"editor": "user1", "reason": "오타 수정"}
        chain = add_transform(chain, "fixed", "edit", metadata=meta)
        self.assertEqual(chain.blocks[1].metadata["editor"], "user1")

    def test_add_transform_empty_chain_raises(self):
        """빈 체인에 변환 추가 시 에러."""
        empty = HashChain(chain_id="empty", blocks=[])
        with self.assertRaises(ValueError):
            add_transform(empty, "content", "edit")


if __name__ == "__main__":
    unittest.main()
