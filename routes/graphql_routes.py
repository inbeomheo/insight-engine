"""
GraphQL API 라우트 (F7-09)

순수 Python으로 구현한 최소 GraphQL 엔드포인트.
주요 쿼리: plugins, schedules, generateContent (mutation)
"""
import logging
import re
from typing import Any, Optional

from flask import Blueprint, request, jsonify, current_app, g
from utils.responses import api_error

from src.contexts.identity.interface.auth_decorators import require_auth
from services.usage.usage_service import UsageService

graphql_bp = Blueprint('graphql', __name__)
logger = logging.getLogger(__name__)


# ── GraphQL 스키마 정의 ──────────────────────────────────────

SCHEMA = """
type Plugin {
  id: String!
  name: String!
  description: String!
}

type GenerateResult {
  title: String!
  content: String!
  html: String
  commentSummaryIncluded: Boolean
}

type Schedule {
  id: String!
  title: String!
  targetPlugin: String!
  scheduledAt: String!
  status: String!
}

type Query {
  plugins: [Plugin!]!
  schedules: [Schedule!]!
  ping: String!
}

type Mutation {
  generateContent(url: String!, styleId: String!, language: String): GenerateResult
}
"""


# ── 리졸버 ──────────────────────────────────────

def resolve_plugins() -> list:
    try:
        from services.mcp import plugin_registry
        return plugin_registry.list_plugins()
    except Exception as e:
        logger.error(f"GraphQL plugins 리졸버 오류: {e}")
        return []


def resolve_schedules() -> list:
    try:
        from services.data.schedule_service import schedule_service
        # 모든 예약 조회 (관리자 용도)
        return schedule_service._store if hasattr(schedule_service, '_store') else []
    except Exception as e:
        logger.error(f"GraphQL schedules 리졸버 오류: {e}")
        return []


def resolve_generate_content(url: str, style_id: str, language: str = 'ko') -> Optional[dict]:
    """콘텐츠 생성 뮤테이션 리졸버"""
    # 사용량 체크
    user_id = g.user_id if hasattr(g, 'user_id') else None
    if not UsageService.check_can_use(user_id):
        return {'errors': [{'message': '사용량이 초과되었습니다.'}]}

    try:
        from services.core.content_service import get_transcript
        from services.core.ai_service import create_content
        transcript = get_transcript(url)
        if not transcript:
            return None
        result = create_content(transcript, style_id, modifiers={'language': language})
        return {
            'title': result.get('title', ''),
            'content': result.get('content', ''),
            'html': result.get('html'),
            'commentSummaryIncluded': result.get('comment_summary_included', False),
        }
    except Exception as e:
        logger.error(f"GraphQL generateContent 리졸버 오류: {e}")
        return None


# ── 최소 GraphQL 파서/실행기 ──────────────────────────────────────

def _parse_arguments(arg_str: str) -> dict:
    """단순 GraphQL 인수 파싱 (중첩 없는 기본형만 지원)"""
    args = {}
    # key: "value" 또는 key: value 패턴 매칭
    for match in re.finditer(r'(\w+)\s*:\s*(?:"([^"]*)"|([\w.-]+))', arg_str):
        key = match.group(1)
        value = match.group(2) if match.group(2) is not None else match.group(3)
        args[key] = value
    return args


def _parse_fields(field_str: str) -> list:
    """중첩 없는 필드 목록 파싱"""
    return re.findall(r'\b(\w+)\b', field_str)


def execute_graphql(query: str, variables: Optional[dict] = None) -> dict:
    """GraphQL 쿼리 실행

    지원 쿼리:
    - { plugins { id name description } }
    - { schedules { id title ... } }
    - { ping }
    - mutation { generateContent(url: "...", styleId: "...") { title content } }
    """
    query = query.strip()

    # Introspection 쿼리 기본 응답
    if '__schema' in query or '__type' in query:
        return {
            'data': {
                '__schema': {
                    'types': [
                        {'name': 'Query'}, {'name': 'Mutation'},
                        {'name': 'Plugin'}, {'name': 'GenerateResult'},
                        {'name': 'Schedule'},
                    ]
                }
            }
        }

    is_mutation = query.startswith('mutation')
    data: dict[str, Any] = {}

    if is_mutation:
        # generateContent 뮤테이션
        m = re.search(
            r'generateContent\s*\(([^)]+)\)\s*\{([^}]+)\}',
            query,
        )
        if m:
            args = _parse_arguments(m.group(1))
            url = args.get('url', '')
            style_id = args.get('styleId', args.get('style_id', 'blog_seo'))
            language = args.get('language', 'ko')
            result = resolve_generate_content(url, style_id, language)
            data['generateContent'] = result
    else:
        # Query 처리
        if 'plugins' in query:
            plugins = resolve_plugins()
            m = re.search(r'plugins\s*\{([^}]+)\}', query)
            if m:
                fields = _parse_fields(m.group(1))
                data['plugins'] = [
                    {f: p.get(f) for f in fields if f in p}
                    for p in plugins
                ]

        if 'schedules' in query:
            schedules = resolve_schedules()
            data['schedules'] = schedules if isinstance(schedules, list) else []

        if 'ping' in query:
            data['ping'] = 'pong'

    if not data and not is_mutation:
        return {'errors': [{'message': '알 수 없는 쿼리입니다.'}]}

    return {'data': data}


# ── 라우트 ──────────────────────────────────────

@graphql_bp.route('/graphql', methods=['GET', 'POST'])
@require_auth
def graphql_endpoint():
    """GraphQL 엔드포인트"""
    if request.method == 'GET':
        # GraphiQL UI는 개발 모드에서만 허용
        if not current_app.debug:
            return api_error('GraphiQL은 개발 모드에서만 사용 가능합니다.', 403)
        return _graphiql_html(), 200, {'Content-Type': 'text/html'}

    body = request.get_json(silent=True)
    if not body:
        return jsonify({'errors': [{'message': '요청 본문이 필요합니다.'}]}), 400

    query = body.get('query', '')
    variables = body.get('variables')

    if not query:
        return jsonify({'errors': [{'message': 'query 필드가 필요합니다.'}]}), 400

    result = execute_graphql(query, variables)
    status = 200 if 'errors' not in result else 400
    return jsonify(result), status


@graphql_bp.route('/graphql/schema', methods=['GET'])
def graphql_schema():
    """SDL 스키마 반환"""
    return SCHEMA, 200, {'Content-Type': 'text/plain; charset=utf-8'}


def _graphiql_html() -> str:
    return """<!DOCTYPE html>
<html>
<head>
  <title>Insight Engine GraphQL</title>
  <link rel="stylesheet" href="https://unpkg.com/graphiql/graphiql.min.css" />
</head>
<body style="margin:0;">
  <div id="graphiql" style="height:100vh;"></div>
  <script crossorigin src="https://unpkg.com/react/umd/react.production.min.js"></script>
  <script crossorigin src="https://unpkg.com/react-dom/umd/react-dom.production.min.js"></script>
  <script crossorigin src="https://unpkg.com/graphiql/graphiql.min.js"></script>
  <script>
    const fetcher = GraphiQL.createFetcher({ url: '/graphql' });
    ReactDOM.render(
      React.createElement(GraphiQL, { fetcher }),
      document.getElementById('graphiql')
    );
  </script>
</body>
</html>"""
