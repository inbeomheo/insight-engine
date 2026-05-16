"""routes/graphql_routes — 최소 GraphQL 엔드포인트 + 파서 단위 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from flask import Flask

from routes.graphql_routes import (
    graphql_bp,
    _parse_arguments,
    _parse_fields,
    execute_graphql,
    SCHEMA,
)


def _build_client(debug=False):
    app = Flask(__name__)
    app.register_blueprint(graphql_bp)
    app.config['TESTING'] = True
    app.debug = debug
    return app.test_client()


class TestArgumentParser(unittest.TestCase):

    def test_quoted_string(self):
        result = _parse_arguments('url: "https://x.com/a"')
        self.assertEqual(result, {'url': 'https://x.com/a'})

    def test_multiple_args(self):
        result = _parse_arguments('url: "x", styleId: "blog_seo", language: ko')
        self.assertEqual(result['url'], 'x')
        self.assertEqual(result['styleId'], 'blog_seo')
        self.assertEqual(result['language'], 'ko')

    def test_unquoted_token(self):
        result = _parse_arguments('count: 5')
        self.assertEqual(result['count'], '5')

    def test_empty(self):
        self.assertEqual(_parse_arguments(''), {})


class TestFieldsParser(unittest.TestCase):

    def test_extract_fields(self):
        self.assertEqual(_parse_fields('id name description'),
                         ['id', 'name', 'description'])

    def test_ignores_special_chars(self):
        result = _parse_fields('id, name, description')
        self.assertEqual(result, ['id', 'name', 'description'])

    def test_empty(self):
        self.assertEqual(_parse_fields(''), [])


class TestExecuteGraphQL(unittest.TestCase):

    def test_introspection_query(self):
        result = execute_graphql('{ __schema { types { name } } }')
        self.assertIn('data', result)
        self.assertIn('__schema', result['data'])

    def test_ping_query(self):
        result = execute_graphql('{ ping }')
        self.assertEqual(result['data']['ping'], 'pong')

    def test_unknown_query(self):
        result = execute_graphql('{ unknown_field }')
        self.assertIn('errors', result)

    def test_plugins_query(self):
        fake_plugins = [
            {'id': 'p1', 'name': '네이버', 'description': '네이버 블로그'},
            {'id': 'p2', 'name': 'WP', 'description': 'WordPress'},
        ]
        with patch('routes.graphql_routes.resolve_plugins', return_value=fake_plugins):
            result = execute_graphql('{ plugins { id name } }')
        self.assertEqual(len(result['data']['plugins']), 2)
        # 'description'은 요청 안 했으므로 미포함
        self.assertNotIn('description', result['data']['plugins'][0])

    def test_mutation_generate_content(self):
        with patch('routes.graphql_routes.resolve_generate_content',
                   return_value={'title': 'T', 'content': 'C', 'html': '<p>C</p>',
                                 'commentSummaryIncluded': False}):
            result = execute_graphql(
                'mutation { generateContent(url: "https://x.com", styleId: "blog_seo") { title content } }'
            )
        self.assertEqual(result['data']['generateContent']['title'], 'T')


class TestGraphQLEndpoint(unittest.TestCase):
    """라우트 endpoint 자체"""

    def test_get_in_prod_returns_403(self):
        """GET은 debug 모드 외에는 차단 (GraphiQL UI)"""
        client = _build_client(debug=False)
        resp = client.get('/graphql')
        self.assertEqual(resp.status_code, 403)

    def test_get_in_debug_returns_html(self):
        client = _build_client(debug=True)
        resp = client.get('/graphql')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'GraphiQL', resp.data)

    def test_post_empty_body_returns_400(self):
        client = _build_client()
        resp = client.post('/graphql', json=None, content_type='application/json')
        self.assertEqual(resp.status_code, 400)

    def test_post_missing_query_returns_400(self):
        client = _build_client()
        resp = client.post('/graphql', json={})
        self.assertEqual(resp.status_code, 400)

    def test_post_valid_query_returns_200(self):
        client = _build_client()
        resp = client.post('/graphql', json={'query': '{ ping }'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['data']['ping'], 'pong')

    def test_unknown_query_returns_400(self):
        client = _build_client()
        resp = client.post('/graphql', json={'query': '{ nonexistent }'})
        self.assertEqual(resp.status_code, 400)


class TestSchemaEndpoint(unittest.TestCase):

    def test_returns_sdl(self):
        client = _build_client()
        resp = client.get('/graphql/schema')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'type Query', resp.data)
        self.assertIn(b'plugins', resp.data)


class TestSchemaConstant(unittest.TestCase):

    def test_includes_essential_types(self):
        for type_name in ('Plugin', 'GenerateResult', 'Schedule', 'Query', 'Mutation'):
            self.assertIn(f'type {type_name}', SCHEMA)


if __name__ == '__main__':
    unittest.main()
