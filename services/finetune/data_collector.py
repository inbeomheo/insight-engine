"""
자동 학습 데이터 수집 서비스 (F10-15)
Supabase 히스토리에서 고품질 콘텐츠를 자동으로 선별하여 학습 데이터 구성
"""
import logging
import os
import time
from typing import Any, Dict, List, Optional

from .dataset_builder import DatasetBuilder
from .reward_model import RuleBasedRewardModel

logger = logging.getLogger(__name__)


class AutoDataCollector:
    """
    자동 학습 데이터 수집기

    주기적으로 히스토리에서 품질 높은 콘텐츠를 수집하여
    파인튜닝 데이터셋을 자동으로 갱신합니다.
    """

    def __init__(
        self,
        output_dir: str = './data/finetune',
        min_quality_score: float = 0.6,
        min_content_length: int = 500,
    ):
        self.output_dir = output_dir
        self.min_quality_score = min_quality_score
        self.min_content_length = min_content_length
        self.reward_model = RuleBasedRewardModel()
        os.makedirs(output_dir, exist_ok=True)

    def collect_from_supabase(
        self,
        days_back: int = 30,
        limit: int = 1000,
    ) -> Dict[str, Any]:
        """
        Supabase 히스토리에서 학습 데이터 수집

        Args:
            days_back: 최근 N일 데이터 수집
            limit: 최대 레코드 수

        Returns:
            수집 결과 통계
        """
        try:
            from services.data.supabase_service import get_supabase_client
            client = get_supabase_client()
            if not client:
                return {'error': 'Supabase 미연결'}

            from datetime import datetime, timedelta
            cutoff = (datetime.utcnow() - timedelta(days=days_back)).isoformat()

            resp = client.table('ie_histories') \
                .select('url, title, style_id, content') \
                .gte('created_at', cutoff) \
                .limit(limit) \
                .execute()

            records = resp.data or []
        except Exception as e:
            logger.error("Supabase 데이터 수집 실패: %s", e)
            return {'error': str(e)}

        return self._process_records(records)

    def collect_from_local_cache(self, cache_db_path: str) -> Dict[str, Any]:
        """로컬 SQLite 캐시에서 학습 데이터 수집"""
        try:
            import sqlite3
            conn = sqlite3.connect(cache_db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT video_id as url, style_id, result_json FROM ai_cache LIMIT 1000"
            ).fetchall()
            conn.close()

            records = []
            import json
            for row in rows:
                try:
                    result = json.loads(row['result_json'])
                    records.append({
                        'url': row['url'],
                        'title': result.get('title', ''),
                        'style_id': row['style_id'],
                        'content': result.get('content', ''),
                    })
                except Exception:
                    continue

        except Exception as e:
            logger.error("로컬 캐시 수집 실패: %s", e)
            return {'error': str(e)}

        return self._process_records(records)

    def _process_records(self, records: List[Dict]) -> Dict[str, Any]:
        """레코드 필터링 및 데이터셋 빌더에 추가"""
        builder = DatasetBuilder(min_output_length=self.min_content_length)

        filtered_in = 0
        filtered_out = 0

        for record in records:
            content = record.get('content', '')
            style_id = record.get('style_id', 'blog_seo')

            if not content or len(content) < self.min_content_length:
                filtered_out += 1
                continue

            # 품질 점수 필터링
            scores = self.reward_model.score(content, style_id)
            if scores['total'] < self.min_quality_score:
                logger.debug("품질 미달 제외: score=%.2f", scores['total'])
                filtered_out += 1
                continue

            if builder.add_example(
                builder.examples.__class__
            ):  # 실제 TrainingExample 추가는 add_from_history 사용
                filtered_in += 1

        # add_from_history를 통해 처리
        quality_records = [
            r for r in records
            if r.get('content') and len(r.get('content', '')) >= self.min_content_length
            and self.reward_model.score(r.get('content', ''), r.get('style_id', 'blog_seo'))['total'] >= self.min_quality_score
        ]

        added = builder.add_from_history(quality_records)

        if added > 0:
            timestamp = int(time.time())
            output_path = os.path.join(self.output_dir, f'dataset_{timestamp}.jsonl')
            save_stats = builder.save(output_path, fmt='openai')
            logger.info("데이터셋 저장: %s, %s", output_path, save_stats)
        else:
            save_stats = {}

        return {
            'total_records': len(records),
            'quality_passed': added,
            'quality_failed': len(records) - added,
            'dataset_stats': builder.get_stats(),
            'save_stats': save_stats,
        }

    def run_periodic_collection(self, interval_hours: int = 24) -> None:
        """주기적 데이터 수집 (별도 스레드에서 실행)"""
        import threading

        def _collect_loop():
            while True:
                logger.info("자동 학습 데이터 수집 시작")
                try:
                    result = self.collect_from_supabase(days_back=7, limit=500)
                    logger.info("수집 완료: %s", result)
                except Exception as e:
                    logger.error("수집 오류: %s", e)
                time.sleep(interval_hours * 3600)

        t = threading.Thread(target=_collect_loop, name="AutoDataCollector", daemon=True)
        t.start()
        logger.info("자동 데이터 수집 스케줄러 시작 (간격: %dh)", interval_hours)
