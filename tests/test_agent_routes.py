"""routes/agent_routes — 에이전트 API 라우트 단위 테스트

AIAgent / memory_store / registry를 모의하여 라우트 응답만 검증.
"""
import json
import unittest
from unittest.mock import patch, MagicMock

from flask import Flask

from routes.agent_routes import agent_bp


def _client():
    app = Flask(__name__)
    app.register_blueprint(agent_bp)
    app.config['TESTING'] = True
    return app.test_client()


class TestAgentChat(unittest.TestCase):

    def test_empty_message_returns_400(self):
        client = _client()
        resp = client.post('/api/agent/chat', json={'message': ''})
        self.assertEqual(resp.status_code, 400)

    def test_missing_message_returns_400(self):
        client = _client()
        resp = client.post('/api/agent/chat', json={})
        self.assertEqual(resp.status_code, 400)

    def test_success_returns_combined_result(self):
        fake_response = MagicMock(
            content='응답',
            session_id='s-1',
            tool_calls_count=3,
            iterations_used=5,
            elapsed_seconds=2.345,
            metadata={'cost': 0.01},
        )
        fake_agent = MagicMock()
        fake_agent.run.return_value = fake_response

        with patch('agent.AIAgent', return_value=fake_agent):
            client = _client()
            resp = client.post('/api/agent/chat', json={
                'message': '안녕', 'toolsets': ['role_writer'],
            })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['content'], '응답')
        self.assertEqual(data['session_id'], 's-1')
        self.assertEqual(data['tool_calls_count'], 3)
        self.assertEqual(data['elapsed_seconds'], 2.35)  # round 2

    def test_agent_exception_returns_500(self):
        with patch('agent.AIAgent', side_effect=RuntimeError('AI fail')):
            client = _client()
            resp = client.post('/api/agent/chat', json={'message': '테스트'})
        self.assertEqual(resp.status_code, 500)


class TestAgentSdkChat(unittest.TestCase):

    def test_empty_message_returns_400(self):
        client = _client()
        resp = client.post('/api/agent/sdk', json={'message': ''})
        self.assertEqual(resp.status_code, 400)

    def test_success_returns_result(self):
        with patch('agent.sdk_agent.run_sdk_agent_sync',
                   return_value={'content': '응답', 'tool_calls': 2, 'elapsed': 1.5}):
            client = _client()
            resp = client.post('/api/agent/sdk', json={'message': '분석해줘'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['content'], '응답')

    def test_sdk_exception_returns_500(self):
        with patch('agent.sdk_agent.run_sdk_agent_sync',
                   side_effect=RuntimeError('SDK 오류')):
            client = _client()
            resp = client.post('/api/agent/sdk', json={'message': '테스트'})
        self.assertEqual(resp.status_code, 500)


class TestAgentSessions(unittest.TestCase):

    def test_list_sessions(self):
        fake_store = MagicMock()
        fake_store.list_sessions.return_value = [
            {'session_id': 's1', 'model': 'gemini'},
            {'session_id': 's2', 'model': 'gemini'},
        ]
        with patch('agent.memory_store', fake_store):
            client = _client()
            resp = client.get('/api/agent/sessions?limit=10')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.get_json()['sessions']), 2)

    def test_sessions_exception_returns_500(self):
        fake_store = MagicMock()
        fake_store.list_sessions.side_effect = RuntimeError('DB down')
        with patch('agent.memory_store', fake_store):
            client = _client()
            resp = client.get('/api/agent/sessions')
        self.assertEqual(resp.status_code, 500)


class TestAgentTools(unittest.TestCase):

    def test_lists_tools_with_stats(self):
        fake_reg = MagicMock()
        fake_reg.tool_count = 5
        fake_entry = MagicMock(name='ent', toolset='ts', description='d', available=True)
        fake_entry.name = 'tool_a'  # MagicMock의 'name' 속성 override
        fake_reg.list_tools.return_value = [fake_entry]
        fake_reg.stats.return_value = {'total_tools': 5, 'available_tools': 5}

        with patch('agent.registry', fake_reg):
            client = _client()
            resp = client.get('/api/agent/tools')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(len(data['tools']), 1)
        self.assertEqual(data['stats']['total_tools'], 5)

    def test_toolset_filter_passed(self):
        fake_reg = MagicMock()
        fake_reg.tool_count = 5
        fake_reg.list_tools.return_value = []
        fake_reg.stats.return_value = {}
        with patch('agent.registry', fake_reg):
            client = _client()
            client.get('/api/agent/tools?toolset=seo')
        # toolsets=['seo'] 로 호출되었는지
        call_args = fake_reg.list_tools.call_args
        self.assertEqual(call_args.kwargs.get('toolsets'), ['seo'])


class TestAgentToolsets(unittest.TestCase):

    def test_returns_toolset_summary(self):
        client = _client()
        resp = client.get('/api/agent/toolsets')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        # 실제 TOOLSETS 사용 — 'collector', 'core' 같은 핵심은 존재
        self.assertIn('toolsets', data)
        self.assertIn('collector', data['toolsets'])
        # 각 항목에 description/direct_tools/includes/resolved_total 필드
        for name, info in data['toolsets'].items():
            self.assertIn('description', info)
            self.assertIn('direct_tools', info)
            self.assertIn('includes', info)
            self.assertIn('resolved_total', info)


if __name__ == '__main__':
    unittest.main()
