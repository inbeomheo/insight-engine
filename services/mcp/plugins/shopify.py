"""
Shopify 블로그 발행 플러그인 (F7-14)

Shopify Admin REST API를 통해 블로그 포스트(Article)를 생성합니다.
SHOPIFY_STORE_DOMAIN, SHOPIFY_ACCESS_TOKEN 환경변수 필요.
"""
import json
import logging
import os
import urllib.error
import urllib.request

from ..plugin_interface import MCPPlugin

logger = logging.getLogger(__name__)


class ShopifyPlugin(MCPPlugin):
    """Shopify 블로그에 Article을 발행하는 플러그인"""

    @property
    def name(self) -> str:
        return "Shopify Blog"

    @property
    def description(self) -> str:
        return "Shopify 스토어 블로그에 아티클을 발행합니다"

    def schema(self) -> dict:
        return {
            'type': 'object',
            'properties': {
                'store_domain': {
                    'type': 'string',
                    'description': 'Shopify 스토어 도메인 (예: mystore.myshopify.com)',
                },
                'access_token': {
                    'type': 'string',
                    'description': 'Shopify Admin API Access Token',
                },
                'blog_id': {
                    'type': 'string',
                    'description': 'Shopify 블로그 ID',
                },
                'author': {
                    'type': 'string',
                    'description': '작성자 이름',
                },
                'tags': {
                    'type': 'string',
                    'description': '태그 (쉼표 구분)',
                },
                'published': {
                    'type': 'boolean',
                    'description': '즉시 발행 여부 (기본: true)',
                    'default': True,
                },
            },
            'required': ['store_domain', 'access_token', 'blog_id'],
        }

    def execute(self, content: str, title: str, **kwargs) -> dict:
        store_domain = kwargs.get('store_domain') or os.getenv('SHOPIFY_STORE_DOMAIN', '')
        access_token = kwargs.get('access_token') or os.getenv('SHOPIFY_ACCESS_TOKEN', '')
        blog_id = kwargs.get('blog_id') or os.getenv('SHOPIFY_BLOG_ID', '')

        if not store_domain:
            return {'success': False, 'message': 'Shopify 스토어 도메인이 필요합니다.', 'url': None}
        if not access_token:
            return {'success': False, 'message': 'Shopify Access Token이 필요합니다.', 'url': None}
        if not blog_id:
            return {'success': False, 'message': 'Shopify 블로그 ID가 필요합니다.', 'url': None}

        store_domain = store_domain.replace('https://', '').replace('http://', '')

        article_data = {
            'article': {
                'title': title,
                'body_html': f'<p>{content.replace(chr(10), "</p><p>")}</p>',
                'author': kwargs.get('author', ''),
                'tags': kwargs.get('tags', ''),
                'published': kwargs.get('published', True),
            }
        }

        url = f'https://{store_domain}/admin/api/2024-01/blogs/{blog_id}/articles.json'
        req = urllib.request.Request(
            url,
            data=json.dumps(article_data).encode(),
            headers={
                'X-Shopify-Access-Token': access_token,
                'Content-Type': 'application/json',
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())

            article = data.get('article', {})
            article_id = article.get('id', '')
            handle = article.get('handle', '')
            article_url = f'https://{store_domain}/blogs/{blog_id}/{handle}' if handle else None

            return {
                'success': True,
                'message': f"Shopify Article 생성 완료 (ID: {article_id})",
                'url': article_url,
            }

        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8', errors='replace')
            logger.error(f"Shopify HTTP 오류: {e.code} — {error_body}")
            return {'success': False, 'message': f'Shopify API 오류: {e.code}', 'url': None}
        except Exception as e:
            logger.error(f"Shopify 발행 실패: {e}")
            return {'success': False, 'message': f'Shopify 발행 실패: {str(e)}', 'url': None}
