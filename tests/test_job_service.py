import sys
import time
import types
import unittest
from unittest.mock import Mock, patch

from services.core import job_service

_H = {'Origin': 'http://localhost:3000'}


def _fake_fusion_module(generate_fusion):
    module = types.ModuleType('services.core.fusion_service')
    module.generate_fusion = generate_fusion
    return module


def _wait_for_terminal_job(client, job_id):
    last = None
    for _ in range(50):
        resp = client.get(f'/api/jobs/{job_id}', headers=_H)
        if resp.status_code != 200:
            return resp, resp.get_json()
        data = resp.get_json()
        last = data
        if data['job']['status'] in {'succeeded', 'failed', 'cancelled'}:
            return resp, data
        time.sleep(0.02)
    raise AssertionError(f'job did not finish: {last}')


class TestJobService(unittest.TestCase):
    def setUp(self):
        job_service.clear_jobs()

    def tearDown(self):
        job_service.clear_jobs()

    def test_job_success_preserves_result(self):
        job = job_service.create_job(
            'test',
            {'source': 'unit'},
            lambda: {'ok': True, 'value': 3},
        )

        for _ in range(50):
            snapshot = job_service.get_job(job['id'])
            if snapshot and snapshot['status'] == 'succeeded':
                break
            time.sleep(0.02)
        else:
            self.fail('job did not finish')

        self.assertEqual(snapshot['result'], {'ok': True, 'value': 3})
        self.assertIsNone(snapshot['error'])
        self.assertEqual(snapshot['steps'][0]['status'], 'succeeded')
        self.assertNotIn('owner_user_id', snapshot)
        self.assertFalse(any(key.startswith('_') for key in snapshot))

    def test_job_failure_preserves_error_message(self):
        def fail():
            raise RuntimeError('boom preserved')

        with patch.object(job_service.logger, 'warning'):
            job = job_service.create_job('test', {}, fail)

            for _ in range(50):
                snapshot = job_service.get_job(job['id'])
                if snapshot and snapshot['status'] == 'failed':
                    break
                time.sleep(0.02)
            else:
                self.fail('job did not fail')

        self.assertEqual(snapshot['error'], 'boom preserved')
        self.assertEqual(snapshot['steps'][0]['error'], 'boom preserved')


class TestJobRoutes(unittest.TestCase):
    def setUp(self):
        from app import create_app

        job_service.clear_jobs()
        self.app = create_app({'TESTING': True, 'RATELIMIT_ENABLED': False})
        self.client = self.app.test_client()

    def tearDown(self):
        job_service.clear_jobs()

    @patch('services.usage.usage_decorator.is_supabase_enabled', return_value=False)
    @patch('src.contexts.identity.interface.auth_decorators.is_supabase_enabled', return_value=False)
    def test_get_missing_job(self, *_):
        resp = self.client.get('/api/jobs/missing', headers=_H)
        self.assertEqual(resp.status_code, 404)

    @patch('services.usage.usage_decorator.is_supabase_enabled', return_value=False)
    @patch('src.contexts.identity.interface.auth_decorators.is_supabase_enabled', return_value=False)
    def test_fusion_sync_api_still_returns_result(self, *_):
        from services import core as services_core

        generate_fusion = Mock(return_value={
            'title': 'Sync fused',
            'content': 'sync done',
            'html': '<p>sync done</p>',
            'sections': {},
            'fusion_meta': {'processing_time': 0.8},
            'usage': {'total_tokens': 8},
        })
        fake_module = _fake_fusion_module(generate_fusion)

        with (
            patch.dict(sys.modules, {'services.core.fusion_service': fake_module}),
            patch.object(services_core, 'fusion_service', fake_module, create=True),
        ):
            resp = self.client.post(
                '/api/generate-fusion',
                json={
                    'urls': ['https://youtube.com/watch?v=a', 'https://youtube.com/watch?v=b'],
                    'model': 'gemini/test',
                    'style': 'blog_seo',
                },
                headers=_H,
            )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['title'], 'Sync fused')
        self.assertNotIn('job_id', data)
        self.assertNotIn('job', data)
        generate_fusion.assert_called_once()

    @patch('services.usage.usage_decorator.is_supabase_enabled', return_value=False)
    @patch('src.contexts.identity.interface.auth_decorators.is_supabase_enabled', return_value=False)
    def test_fusion_async_job_success(self, *_):
        from services import core as services_core

        generate_fusion = Mock(return_value={
            'title': 'Fused',
            'content': 'done',
            'html': '<p>done</p>',
            'sections': {},
            'fusion_meta': {'processing_time': 1.2},
            'usage': {'total_tokens': 10},
        })
        fake_module = _fake_fusion_module(generate_fusion)

        with (
            patch.dict(sys.modules, {'services.core.fusion_service': fake_module}),
            patch.object(services_core, 'fusion_service', fake_module, create=True),
        ):
            resp = self.client.post(
                '/api/generate-fusion',
                json={
                    'async': True,
                    'urls': ['https://youtube.com/watch?v=a', 'https://youtube.com/watch?v=b'],
                    'model': 'gemini/test',
                    'style': 'blog_seo',
                },
                headers=_H,
            )

            self.assertEqual(resp.status_code, 202)
            job_id = resp.get_json()['job_id']
            job_resp, data = _wait_for_terminal_job(self.client, job_id)

        self.assertEqual(job_resp.status_code, 200)
        self.assertEqual(data['job']['status'], 'succeeded')
        self.assertEqual(data['job']['result']['title'], 'Fused')
        self.assertIsNone(data['job']['error'])

    @patch('services.usage.usage_decorator.is_supabase_enabled', return_value=False)
    @patch('src.contexts.identity.interface.auth_decorators.is_supabase_enabled', return_value=False)
    def test_fusion_async_job_failure_preserves_error(self, *_):
        from services import core as services_core

        generate_fusion = Mock(side_effect=ValueError('bad input preserved'))
        fake_module = _fake_fusion_module(generate_fusion)

        with (
            patch.dict(sys.modules, {'services.core.fusion_service': fake_module}),
            patch.object(services_core, 'fusion_service', fake_module, create=True),
        ):
            resp = self.client.post(
                '/api/generate-fusion',
                json={
                    'async': True,
                    'urls': ['https://youtube.com/watch?v=a', 'https://youtube.com/watch?v=b'],
                    'model': 'gemini/test',
                },
                headers=_H,
            )

            self.assertEqual(resp.status_code, 202)
            job_id = resp.get_json()['job_id']
            job_resp, data = _wait_for_terminal_job(self.client, job_id)

        self.assertEqual(job_resp.status_code, 200)
        self.assertEqual(data['job']['status'], 'failed')
        self.assertEqual(data['job']['error'], 'bad input preserved')
