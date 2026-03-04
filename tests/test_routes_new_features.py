"""
신규 기능 라우트 통합 테스트

Phase 1-4에서 추가된 17개 API 엔드포인트의 Flask test_client 기반 통합 테스트.
5개 그룹: /generate 모디파이어, /api/schedule, /api/knowledge, /api/mcp+pipeline, /api/workspaces
"""
import io
import unittest
from contextlib import ExitStack
from unittest.mock import patch, MagicMock


class _BaseRouteTest(unittest.TestCase):
    """공통 setUp: Flask test_client 생성"""

    def setUp(self):
        from app import create_app
        self.app = create_app({'TESTING': True})
        self.client = self.app.test_client()

    def _make_generate_patches(self):
        """test_routes_smoke.py 패턴 재사용 — patch 객체 튜플 반환"""
        fake_result = {
            'title': '테스트 제목',
            'content': '테스트 본문',
            'html': '<p>테스트 본문</p>',
            'usage': {'prompt_tokens': 10, 'completion_tokens': 20, 'total_tokens': 30},
        }
        fake_transcript = {'text': '테스트 자막 내용입니다. 충분히 긴 자막 텍스트를 작성합니다.' * 10, 'source': 'api'}

        def fake_create_content(content, model, style_prompt=None,
                                return_prompt=False, modifiers=None, style_id=None,
                                user_id=None, **kwargs):
            if return_prompt:
                return fake_result, 'PROMPT'
            return fake_result

        return (
            patch('services.supabase_service.is_supabase_enabled', return_value=False),
            patch('routes.blog_routes.content_service.is_youtube_url', return_value=True),
            patch('routes.blog_routes.content_service.get_video_id', return_value='test123'),
            patch('routes.blog_routes.content_service.get_content_title', return_value='테스트 영상 제목'),
            patch('routes.blog_routes.content_service.get_transcript', return_value=fake_transcript),
            patch('routes.blog_routes.content_service.get_top_comments', return_value=[]),
            patch('routes.blog_routes.content_service.truncate_text', side_effect=lambda t, _max: t),
            patch('routes.blog_routes.ai_service.create_content', side_effect=fake_create_content),
        )


# =============================================
# 1. /generate 모디파이어/스타일 통합 (6건)
# =============================================

class TestGenerateModifiers(_BaseRouteTest):
    """language, length, writing_style 모디파이어 및 신규 스타일 검증"""

    def _post_generate(self, **overrides):
        payload = {
            'url': 'https://www.youtube.com/watch?v=test123',
            'model': 'gpt-4o-mini',
            'style': 'blog_seo',
        }
        payload.update(overrides)
        with ExitStack() as stack:
            for p in self._make_generate_patches():
                stack.enter_context(p)
            return self.client.post('/generate', json=payload)

    def test_language_en(self):
        """language='en' 전달 시 정상 응답"""
        res = self._post_generate(modifiers={'language': 'en'})
        self.assertEqual(res.status_code, 200)
        self.assertIn('content', res.get_json())

    def test_language_ja(self):
        """language='ja' 전달 시 정상 응답"""
        res = self._post_generate(modifiers={'language': 'ja'})
        self.assertEqual(res.status_code, 200)
        self.assertIn('content', res.get_json())

    def test_style_geo_seo(self):
        """style='geo_seo' 선택 시 정상 응답"""
        res = self._post_generate(style='geo_seo')
        self.assertEqual(res.status_code, 200)
        self.assertIn('content', res.get_json())

    def test_style_shorts_script(self):
        """style='shorts_script' 선택 시 정상 응답"""
        res = self._post_generate(style='shorts_script')
        self.assertEqual(res.status_code, 200)
        self.assertIn('content', res.get_json())

    def test_combined_modifiers(self):
        """language + length + writing_style 조합 전달"""
        res = self._post_generate(modifiers={
            'language': 'en',
            'length': 'long',
            'writing_style': 'expert',
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn('content', res.get_json())

    def test_unknown_language_graceful(self):
        """존재하지 않는 language 값 → 에러 없이 기본 동작"""
        res = self._post_generate(modifiers={'language': 'zz_invalid'})
        self.assertEqual(res.status_code, 200)
        self.assertIn('content', res.get_json())


# =============================================
# 2. /api/schedule CRUD (5건)
# =============================================

class TestScheduleRoutes(_BaseRouteTest):
    """예약 발행 API 테스트 (Supabase 비활성화 → require_auth 통과)"""

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_create_schedule(self, mock_enabled):
        """POST /api/schedule — 정상 생성"""
        mock_svc = MagicMock()
        mock_svc.create.return_value = {
            'id': 'sched-1', 'title': '제목', 'status': 'pending',
        }
        with patch('services.schedule_service.schedule_service', mock_svc):
            res = self.client.post('/api/schedule', json={
                'title': '제목',
                'content': '본문',
                'target_plugin': 'naver_blog',
                'scheduled_at': '2026-12-01T09:00:00Z',
            })
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.get_json()['id'], 'sched-1')

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_create_schedule_missing_fields(self, mock_enabled):
        """POST /api/schedule — 필수 필드 누락 → 400"""
        res = self.client.post('/api/schedule', json={
            'title': '제목만',
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn('error', res.get_json())

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_list_schedule(self, mock_enabled):
        """GET /api/schedule — 목록 반환"""
        mock_svc = MagicMock()
        mock_svc.list_by_user.return_value = [{'id': 's1'}, {'id': 's2'}]
        with patch('services.schedule_service.schedule_service', mock_svc):
            res = self.client.get('/api/schedule')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('schedules', data)
        self.assertEqual(len(data['schedules']), 2)

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_delete_schedule(self, mock_enabled):
        """DELETE /api/schedule/<id> — 정상 삭제"""
        mock_svc = MagicMock()
        mock_svc.delete.return_value = True
        with patch('services.schedule_service.schedule_service', mock_svc):
            res = self.client.delete('/api/schedule/sched-1')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()['success'])

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_delete_schedule_not_found(self, mock_enabled):
        """DELETE /api/schedule/<id> — 존재하지 않는 ID → 404"""
        mock_svc = MagicMock()
        mock_svc.delete.return_value = False
        with patch('services.schedule_service.schedule_service', mock_svc):
            res = self.client.delete('/api/schedule/nonexistent')
        self.assertEqual(res.status_code, 404)


# =============================================
# 3. /api/knowledge CRUD (6건)
# =============================================

class TestKnowledgeRoutes(_BaseRouteTest):
    """RAG 지식 베이스 API 테스트"""

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_list_knowledge_rag_disabled(self, mock_enabled):
        """GET /api/knowledge/list — RAG 비활성 시 빈 배열"""
        with patch('config.RAG_ENABLED', False):
            res = self.client.get('/api/knowledge/list')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()['documents'], [])

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_list_knowledge_rag_enabled(self, mock_enabled):
        """GET /api/knowledge/list — RAG 활성 시 문서 목록"""
        mock_vs = MagicMock()
        mock_vs.list_documents.return_value = [
            {'id': 'doc1', 'filename': 'test.txt'},
        ]
        with patch('config.RAG_ENABLED', True), \
             patch('services.rag.vector_store', mock_vs):
            res = self.client.get('/api/knowledge/list')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.get_json()['documents']), 1)

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_upload_knowledge(self, mock_enabled):
        """POST /api/knowledge/upload — 정상 업로드"""
        mock_extract = MagicMock(return_value='문서 내용입니다.')
        mock_chunk = MagicMock(return_value=['청크1', '청크2'])
        mock_vs = MagicMock()

        with patch('config.RAG_ENABLED', True), \
             patch('services.rag.chunker.extract_text_from_file', mock_extract), \
             patch('services.rag.chunker.chunk_text', mock_chunk), \
             patch('services.rag.vector_store', mock_vs):
            data = {
                'file': (io.BytesIO(b'hello world'), 'test.txt'),
            }
            res = self.client.post(
                '/api/knowledge/upload',
                data=data,
                content_type='multipart/form-data',
            )
        self.assertEqual(res.status_code, 201)
        resp = res.get_json()
        self.assertIn('id', resp)
        self.assertEqual(resp['chunk_count'], 2)

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_upload_unsupported_ext(self, mock_enabled):
        """POST /api/knowledge/upload — 지원하지 않는 확장자 → 400"""
        with patch('config.RAG_ENABLED', True):
            data = {
                'file': (io.BytesIO(b'data'), 'image.png'),
            }
            res = self.client.post(
                '/api/knowledge/upload',
                data=data,
                content_type='multipart/form-data',
            )
        self.assertEqual(res.status_code, 400)
        self.assertIn('지원하지 않는', res.get_json()['error'])

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_upload_rag_disabled(self, mock_enabled):
        """POST /api/knowledge/upload — RAG 비활성 시 → 400"""
        with patch('config.RAG_ENABLED', False):
            data = {
                'file': (io.BytesIO(b'data'), 'test.txt'),
            }
            res = self.client.post(
                '/api/knowledge/upload',
                data=data,
                content_type='multipart/form-data',
            )
        self.assertEqual(res.status_code, 400)
        self.assertIn('RAG', res.get_json()['error'])

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_delete_knowledge(self, mock_enabled):
        """DELETE /api/knowledge/<id> — 정상 삭제"""
        mock_vs = MagicMock()
        with patch('config.RAG_ENABLED', True), \
             patch('services.rag.vector_store', mock_vs):
            res = self.client.delete('/api/knowledge/doc-123')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()['success'])


# =============================================
# 4. /api/mcp + /api/pipeline (5건)
# =============================================

class TestMcpAndPipelineRoutes(_BaseRouteTest):
    """MCP 플러그인 및 파이프라인 API 테스트"""

    def test_mcp_list_plugins(self):
        """GET /api/mcp/plugins — 플러그인 목록 반환"""
        mock_registry = MagicMock()
        mock_registry.list_plugins.return_value = [
            {'id': 'naver_blog', 'name': 'Naver Blog', 'description': '네이버 블로그 발행'},
        ]
        with patch('services.mcp.plugin_registry', mock_registry):
            res = self.client.get('/api/mcp/plugins')
        self.assertEqual(res.status_code, 200)
        plugins = res.get_json()['plugins']
        self.assertEqual(len(plugins), 1)
        self.assertEqual(plugins[0]['id'], 'naver_blog')

    def test_mcp_publish_success(self):
        """POST /api/mcp/publish — 정상 발행"""
        mock_registry = MagicMock()
        mock_registry.execute.return_value = {
            'success': True, 'message': '발행 완료', 'url': 'https://blog.naver.com/test',
        }
        with patch('services.mcp.plugin_registry', mock_registry):
            res = self.client.post('/api/mcp/publish', json={
                'plugin_id': 'naver_blog',
                'title': '테스트 제목',
                'content': '테스트 본문',
            })
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()['success'])

    def test_mcp_publish_missing_fields(self):
        """POST /api/mcp/publish — 필수 필드 누락 → 400"""
        res = self.client.post('/api/mcp/publish', json={
            'plugin_id': 'naver_blog',
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn('error', res.get_json())

    def test_mcp_publish_unknown_plugin(self):
        """POST /api/mcp/publish — 존재하지 않는 플러그인 → 404"""
        mock_registry = MagicMock()
        mock_registry.execute.return_value = {
            'success': False, 'message': "플러그인 'unknown'을(를) 찾을 수 없습니다.", 'url': None,
        }
        with patch('services.mcp.plugin_registry', mock_registry):
            res = self.client.post('/api/mcp/publish', json={
                'plugin_id': 'unknown',
                'title': '제목',
                'content': '본문',
            })
        self.assertEqual(res.status_code, 404)
        self.assertFalse(res.get_json()['success'])

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_pipeline_invalid_id(self, mock_enabled):
        """POST /api/pipeline — 잘못된 pipeline_id → 400"""
        res = self.client.post('/api/pipeline', json={
            'pipeline_id': 'nonexistent_pipeline',
            'url': 'https://www.youtube.com/watch?v=test',
            'model': 'gpt-4o-mini',
            'style': 'blog_seo',
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn('error', res.get_json())


# =============================================
# 5. /api/workspaces CRUD (6건)
# =============================================

class TestWorkspaceRoutes(_BaseRouteTest):
    """워크스페이스 API 테스트

    require_auth: is_supabase_enabled=False → g.user_id=None 통과
    _check_supabase: 직접 mock하여 None 반환 (Supabase 불필요)
    """

    def _ws_patches(self, mock_ws):
        """워크스페이스 테스트 공통 patch 스택"""
        return (
            patch('services.supabase_service.is_supabase_enabled', return_value=False),
            patch('routes.auth_routes._check_supabase', return_value=None),
            patch('routes.auth_routes.workspace_service', mock_ws),
        )

    def test_create_workspace(self):
        """POST /api/workspaces — 정상 생성"""
        mock_ws = MagicMock()
        mock_ws.create_workspace.return_value = {
            'id': 'ws-1', 'name': '테스트 워크스페이스', 'owner_id': 'user-1',
        }
        with ExitStack() as stack:
            for p in self._ws_patches(mock_ws):
                stack.enter_context(p)
            res = self.client.post('/api/workspaces', json={'name': '테스트 워크스페이스'})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.get_json()['name'], '테스트 워크스페이스')

    def test_create_workspace_no_name(self):
        """POST /api/workspaces — 이름 미입력 → 400"""
        mock_ws = MagicMock()
        with ExitStack() as stack:
            for p in self._ws_patches(mock_ws):
                stack.enter_context(p)
            res = self.client.post('/api/workspaces', json={'name': ''})
        self.assertEqual(res.status_code, 400)
        self.assertIn('error', res.get_json())

    def test_list_workspaces(self):
        """GET /api/workspaces — 목록 반환"""
        mock_ws = MagicMock()
        mock_ws.list_workspaces.return_value = [
            {'id': 'ws-1', 'name': 'WS1'},
            {'id': 'ws-2', 'name': 'WS2'},
        ]
        with ExitStack() as stack:
            for p in self._ws_patches(mock_ws):
                stack.enter_context(p)
            res = self.client.get('/api/workspaces')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.get_json()['workspaces']), 2)

    def test_get_workspace_members(self):
        """GET /api/workspaces/<id>/members — 멤버 반환"""
        mock_ws = MagicMock()
        mock_ws.get_members.return_value = [
            {'user_id': 'u1', 'role': 'owner'},
            {'user_id': 'u2', 'role': 'editor'},
        ]
        with ExitStack() as stack:
            for p in self._ws_patches(mock_ws):
                stack.enter_context(p)
            res = self.client.get('/api/workspaces/ws-1/members')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.get_json()['members']), 2)

    def test_delete_workspace(self):
        """DELETE /api/workspaces/<id> — 정상 삭제"""
        mock_ws = MagicMock()
        mock_ws.delete_workspace.return_value = True
        with ExitStack() as stack:
            for p in self._ws_patches(mock_ws):
                stack.enter_context(p)
            res = self.client.delete('/api/workspaces/ws-1')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()['success'])

    def test_delete_workspace_not_owner(self):
        """DELETE /api/workspaces/<id> — 비소유자 → 403"""
        mock_ws = MagicMock()
        mock_ws.delete_workspace.return_value = False
        with ExitStack() as stack:
            for p in self._ws_patches(mock_ws):
                stack.enter_context(p)
            res = self.client.delete('/api/workspaces/ws-1')
        self.assertEqual(res.status_code, 403)


if __name__ == '__main__':
    unittest.main()
