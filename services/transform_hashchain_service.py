"""
변환 해시체인 서비스.

콘텐츠 변환 이력을 해시체인으로 기록하고 무결성을 검증한다.
"""

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class ChainBlock:
    """해시체인 블록."""
    block_id: str
    prev_hash: str
    content_hash: str
    transform_type: str
    timestamp: str
    metadata: dict


@dataclass
class HashChain:
    """해시체인."""
    chain_id: str
    blocks: list  # list[ChainBlock]


def _hash_content(content: str) -> str:
    """콘텐츠의 SHA256 해시를 생성한다."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    """현재 UTC 시간을 ISO 형식으로 반환한다."""
    return datetime.now(timezone.utc).isoformat()


def create_chain(initial_content: str) -> HashChain:
    """제네시스 블록으로 해시체인을 생성한다."""
    chain_id = f"hc_{uuid.uuid4().hex[:8]}"
    content_hash = _hash_content(initial_content)

    genesis = ChainBlock(
        block_id=f"blk_{uuid.uuid4().hex[:8]}",
        prev_hash="0" * 64,  # 제네시스 블록
        content_hash=content_hash,
        transform_type="genesis",
        timestamp=_now_iso(),
        metadata={"content_length": len(initial_content)},
    )

    return HashChain(chain_id=chain_id, blocks=[genesis])


def add_transform(
    chain: HashChain,
    content: str,
    transform_type: str,
    metadata: dict = None,
) -> HashChain:
    """변환 블록을 체인에 추가한다."""
    if not chain.blocks:
        raise ValueError("체인에 블록이 없습니다. create_chain()으로 먼저 생성하세요.")

    last_block = chain.blocks[-1]
    # 이전 블록의 content_hash를 prev_hash로 사용
    prev_hash = last_block.content_hash

    content_hash = _hash_content(content)

    new_block = ChainBlock(
        block_id=f"blk_{uuid.uuid4().hex[:8]}",
        prev_hash=prev_hash,
        content_hash=content_hash,
        transform_type=transform_type,
        timestamp=_now_iso(),
        metadata=metadata or {"content_length": len(content)},
    )

    new_blocks = list(chain.blocks) + [new_block]
    return HashChain(chain_id=chain.chain_id, blocks=new_blocks)


def verify_chain(chain: HashChain) -> bool:
    """체인 무결성을 검증한다 (해시 연결 확인)."""
    if not chain.blocks:
        return True

    # 제네시스 블록 검증
    if chain.blocks[0].prev_hash != "0" * 64:
        return False

    # 각 블록의 prev_hash가 이전 블록의 content_hash와 일치하는지 확인
    for i in range(1, len(chain.blocks)):
        expected_prev = chain.blocks[i - 1].content_hash
        actual_prev = chain.blocks[i].prev_hash
        if expected_prev != actual_prev:
            return False

    return True


def get_transform_history(chain: HashChain) -> list:
    """변환 이력을 반환한다."""
    history = []
    for block in chain.blocks:
        history.append({
            "block_id": block.block_id,
            "transform_type": block.transform_type,
            "timestamp": block.timestamp,
            "content_hash": block.content_hash[:16] + "...",
            "metadata": block.metadata,
        })
    return history
