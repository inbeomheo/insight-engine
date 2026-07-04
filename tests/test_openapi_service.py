"""openapi_service 단위 테스트"""
import unittest

from services.data.openapi_service import build_openapi_spec


class TestBuildOpenapiSpec(unittest.TestCase):

    def test_returns_dict(self):
        """스펙이 dict로 반환됨"""
        spec = build_openapi_spec()
        self.assertIsInstance(spec, dict)

    def test_openapi_version(self):
        """OpenAPI 버전 3.0.3"""
        spec = build_openapi_spec()
        self.assertEqual(spec['openapi'], '3.0.3')

    def test_info_title(self):
        """기본 타이틀"""
        spec = build_openapi_spec()
        self.assertEqual(spec['info']['title'], 'Insight Engine API')

    def test_custom_title(self):
        """커스텀 타이틀"""
        spec = build_openapi_spec(app_title='My API')
        self.assertEqual(spec['info']['title'], 'My API')

    def test_custom_version(self):
        """커스텀 버전"""
        spec = build_openapi_spec(version='2.0.0')
        self.assertEqual(spec['info']['version'], '2.0.0')

    def test_custom_server_url(self):
        """커스텀 서버 URL"""
        spec = build_openapi_spec(server_url='https://api.example.com')
        self.assertEqual(spec['servers'][0]['url'], 'https://api.example.com')

    def test_paths_exist(self):
        """주요 경로 존재"""
        spec = build_openapi_spec()
        self.assertIn('/generate', spec['paths'])

    def test_security_scheme(self):
        """BearerAuth 보안 스키마"""
        spec = build_openapi_spec()
        schemes = spec['components']['securitySchemes']
        self.assertIn('BearerAuth', schemes)
        self.assertEqual(schemes['BearerAuth']['type'], 'http')

    def test_schemas_defined(self):
        """주요 스키마 정의"""
        spec = build_openapi_spec()
        schemas = spec['components']['schemas']
        self.assertIn('GenerateRequest', schemas)
        self.assertIn('GenerateResponse', schemas)
        self.assertIn('ErrorResponse', schemas)

    def test_tags(self):
        """태그 목록"""
        spec = build_openapi_spec()
        tag_names = [t['name'] for t in spec['tags']]
        self.assertIn('Content', tag_names)

    def test_generate_endpoint_post(self):
        """/generate POST 메서드"""
        spec = build_openapi_spec()
        generate = spec['paths']['/generate']
        self.assertIn('post', generate)
        self.assertEqual(generate['post']['operationId'], 'generateContent')


if __name__ == '__main__':
    unittest.main()
