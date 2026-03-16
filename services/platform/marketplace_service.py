"""
마켓플레이스 서비스 (F4-14)
프롬프트 템플릿 마켓플레이스 CRUD
"""
import uuid
from datetime import datetime, timezone
from services.core.logging_config import ServiceLogger
import logging

logger = ServiceLogger('MarketplaceService')


class MarketplaceService:
    """프롬프트 템플릿 마켓플레이스"""

    def __init__(self):
        self._templates: dict[str, dict] = {}

    def publish_template(
        self,
        author_id: str,
        title: str,
        description: str,
        prompt_text: str,
        category: str = 'general',
        price: float = 0.0,
        tags: list[str] | None = None,
    ) -> dict:
        """템플릿 게시"""
        if not title or not prompt_text:
            return {'error': '제목과 프롬프트 텍스트는 필수입니다.'}

        try:
            template_id = uuid.uuid4().hex[:12]
            template = {
                'id': template_id,
                'author_id': author_id,
                'title': title,
                'description': description,
                'prompt_text': prompt_text,
                'category': category,
                'price': price,
                'tags': tags or [],
                'downloads': 0,
                'rating': 0.0,
                'rating_count': 0,
                'status': 'published',
                'created_at': datetime.now(timezone.utc).isoformat(),
            }
            self._templates[template_id] = template
            logger.info(f"템플릿 게시: {template_id} ({title})")
            return template
        except Exception as e:
            logger.error("publish_template 실패: %s", e, exc_info=True)
            return {}

    def list_templates(self, category: str | None = None, query: str | None = None) -> list[dict]:
        """템플릿 목록 (필터/검색)"""
        try:
            results = [t for t in self._templates.values() if t['status'] == 'published']

            if category:
                results = [t for t in results if t['category'] == category]

            if query:
                q = query.lower()
                results = [t for t in results if q in t['title'].lower() or q in t['description'].lower()]

            return sorted(results, key=lambda t: t['downloads'], reverse=True)
        except Exception as e:
            logger.error("list_templates 실패: %s", e, exc_info=True)
            return []

    def get_template(self, template_id: str) -> dict | None:
        """ID로 템플릿 단건 조회"""
        try:
            return self._templates.get(template_id)
        except Exception as e:
            logger.error("get_template 실패: %s", e, exc_info=True)
            return {}

    def download_template(self, template_id: str, user_id: str) -> dict:
        """템플릿 다운로드 (다운로드 수 증가)"""
        try:
            template = self._templates.get(template_id)
            if not template:
                return {'error': '템플릿을 찾을 수 없습니다.'}

            template['downloads'] += 1
            return {'prompt_text': template['prompt_text'], 'title': template['title']}
        except Exception as e:
            logger.error("download_template 실패: %s", e, exc_info=True)
            return {}

    def rate_template(self, template_id: str, user_id: str, rating: float) -> dict:
        """템플릿 평점 (1~5)"""
        if not (1 <= rating <= 5):
            return {'error': '평점은 1~5 사이여야 합니다.'}

        try:
            template = self._templates.get(template_id)
            if not template:
                return {'error': '템플릿을 찾을 수 없습니다.'}

            # 누적 평균 계산
            total = template['rating'] * template['rating_count'] + rating
            template['rating_count'] += 1
            template['rating'] = round(total / template['rating_count'], 2)

            return {'rating': template['rating'], 'rating_count': template['rating_count']}
        except Exception as e:
            logger.error("rate_template 실패: %s", e, exc_info=True)
            return {}

    def unpublish_template(self, template_id: str, author_id: str) -> dict:
        """템플릿 비공개 처리"""
        try:
            template = self._templates.get(template_id)
            if not template:
                return {'error': '템플릿을 찾을 수 없습니다.'}
            if template['author_id'] != author_id:
                return {'error': '본인의 템플릿만 비공개 처리할 수 있습니다.'}

            template['status'] = 'unpublished'
            return template
        except Exception as e:
            logger.error("unpublish_template 실패: %s", e, exc_info=True)
            return {}


marketplace_service = MarketplaceService()
