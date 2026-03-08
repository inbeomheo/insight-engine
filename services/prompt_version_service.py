"""
프롬프트 버전 관리 서비스 (F10-27)
프롬프트 변경 이력 추적, A/B 테스트, 롤백 지원
"""
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 저장 경로
PROMPT_VERSION_STORE = os.getenv('PROMPT_VERSION_STORE', './data/prompt_versions.jsonl')


@dataclass
class PromptVersion:
    """프롬프트 버전 레코드"""
    version_id: str          # SHA256 해시 (내용 기반)
    prompt_key: str          # 프롬프트 식별자 (예: 'blog_seo_style')
    content: str             # 프롬프트 내용
    version_num: int         # 순번 (1, 2, 3, ...)
    created_at: float        # 생성 시각
    created_by: str          # 생성자 (사용자 ID 또는 'system')
    description: str         # 변경 설명
    is_active: bool          # 현재 활성 버전 여부
    tags: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)  # 성능 지표

    @staticmethod
    def make_version_id(content: str) -> str:
        """프롬프트 내용 기반 SHA256 버전 ID 생성 (16자)"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]


class PromptVersionService:
    """
    프롬프트 버전 관리 서비스

    기능:
    - 버전 저장/조회/활성화
    - 변경 이력 조회
    - 성능 메트릭 기록
    - 버전 간 diff
    - 롤백
    """

    def __init__(self, store_path: str = PROMPT_VERSION_STORE):
        self.store_path = store_path
        os.makedirs(os.path.dirname(store_path) if os.path.dirname(store_path) else '.', exist_ok=True)
        self._cache: Dict[str, List[PromptVersion]] = {}  # key → versions

    def save_version(
        self,
        prompt_key: str,
        content: str,
        description: str = '',
        created_by: str = 'system',
        tags: Optional[List[str]] = None,
        activate: bool = True,
    ) -> PromptVersion:
        """
        새 프롬프트 버전 저장

        Args:
            prompt_key: 프롬프트 식별자
            content: 프롬프트 내용
            description: 변경 사유
            activate: True면 즉시 활성화

        Returns:
            저장된 PromptVersion
        """
        versions = self.get_history(prompt_key)
        version_num = len(versions) + 1

        version = PromptVersion(
            version_id=PromptVersion.make_version_id(content),
            prompt_key=prompt_key,
            content=content,
            version_num=version_num,
            created_at=time.time(),
            created_by=created_by,
            description=description,
            is_active=activate,
            tags=tags or [],
        )

        # 기존 활성 버전 비활성화
        if activate:
            for v in versions:
                v.is_active = False

        # 저장
        versions.append(version)
        self._cache[prompt_key] = versions
        self._persist(version)

        logger.info("프롬프트 버전 저장: key=%s, v%d, active=%s", prompt_key, version_num, activate)
        return version

    def get_active(self, prompt_key: str) -> Optional[PromptVersion]:
        """현재 활성 버전 반환"""
        versions = self.get_history(prompt_key)
        for v in reversed(versions):
            if v.is_active:
                return v
        return versions[-1] if versions else None

    def get_by_version_num(self, prompt_key: str, version_num: int) -> Optional[PromptVersion]:
        """버전 번호로 조회"""
        versions = self.get_history(prompt_key)
        for v in versions:
            if v.version_num == version_num:
                return v
        return None

    def rollback(self, prompt_key: str, version_num: int) -> Optional[PromptVersion]:
        """특정 버전으로 롤백 (해당 버전 재활성화)"""
        versions = self.get_history(prompt_key)
        target = None
        for v in versions:
            v.is_active = False
            if v.version_num == version_num:
                target = v

        if not target:
            logger.warning("롤백 대상 버전 없음: %s v%d", prompt_key, version_num)
            return None

        target.is_active = True
        self._cache[prompt_key] = versions
        self._persist_all(prompt_key, versions)

        logger.info("프롬프트 롤백 완료: key=%s → v%d", prompt_key, version_num)
        return target

    def get_history(self, prompt_key: str) -> List[PromptVersion]:
        """버전 이력 조회 (버전 번호 오름차순)"""
        if prompt_key in self._cache:
            return self._cache[prompt_key]

        versions = []
        if os.path.exists(self.store_path):
            with open(self.store_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        if data.get('prompt_key') == prompt_key:
                            versions.append(PromptVersion(**data))
                    except Exception:
                        continue

        versions.sort(key=lambda v: v.version_num)
        self._cache[prompt_key] = versions
        return versions

    def record_metric(self, prompt_key: str, version_id: str, metric_name: str, value: float) -> None:
        """버전별 성능 메트릭 기록 (예: quality_score, user_rating)"""
        versions = self.get_history(prompt_key)
        for v in versions:
            if v.version_id == version_id:
                v.metrics[metric_name] = value
                self._persist_all(prompt_key, versions)
                return
        logger.warning("메트릭 기록 실패: 버전 없음 %s/%s", prompt_key, version_id)

    def diff(self, prompt_key: str, version_a: int, version_b: int) -> Dict[str, Any]:
        """두 버전 간 diff 반환"""
        v_a = self.get_by_version_num(prompt_key, version_a)
        v_b = self.get_by_version_num(prompt_key, version_b)

        if not v_a or not v_b:
            return {'error': '버전을 찾을 수 없습니다'}

        # 단순 라인 diff
        lines_a = set(v_a.content.split('\n'))
        lines_b = set(v_b.content.split('\n'))
        added = lines_b - lines_a
        removed = lines_a - lines_b

        return {
            'version_a': version_a,
            'version_b': version_b,
            'added_lines': sorted(added),
            'removed_lines': sorted(removed),
            'length_change': len(v_b.content) - len(v_a.content),
        }

    def _persist(self, version: PromptVersion):
        with open(self.store_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(asdict(version), ensure_ascii=False) + '\n')

    def _persist_all(self, prompt_key: str, versions: List[PromptVersion]):
        """특정 키의 모든 버전 재저장 (상태 변경 시)"""
        # 전체 파일 재작성 (간단 구현)
        all_versions = {}
        if os.path.exists(self.store_path):
            with open(self.store_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        key = data.get('prompt_key', '')
                        if key not in all_versions:
                            all_versions[key] = []
                        if key != prompt_key:
                            all_versions[key].append(data)
                    except Exception:
                        continue

        all_versions[prompt_key] = [asdict(v) for v in versions]

        with open(self.store_path, 'w', encoding='utf-8') as f:
            for key_versions in all_versions.values():
                for v_data in key_versions:
                    f.write(json.dumps(v_data, ensure_ascii=False) + '\n')


# 싱글톤
_service: Optional[PromptVersionService] = None


def get_prompt_version_service() -> PromptVersionService:
    """PromptVersionService 싱글톤 인스턴스 반환"""
    global _service
    if _service is None:
        _service = PromptVersionService()
    return _service
