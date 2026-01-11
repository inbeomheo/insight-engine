import unittest


class TestAppLifecycleSmoke(unittest.TestCase):
    def setUp(self):
        from app import create_app
        self.app = create_app({
            'TESTING': True,
            'GENAI_API_KEY': 'test',
            'ALLOWED_MODELS': ['gemini-3-flash-preview'],
            'DEFAULT_MODEL': 'gemini-3-flash-preview',
            'SECRET_KEY': 'test-secret'
        })
        self.client = self.app.test_client()

        # tracker globals reset
        import routes.blog_routes as blog_routes
        blog_routes._CLIENT_TRACKER.clear()

    def test_heartbeat_registers_client(self):
        import routes.blog_routes as blog_routes

        res = self.client.post('/api/heartbeat', json={'clientId': 'c1'})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json().get('ok'))
        self.assertIn('c1', blog_routes._CLIENT_TRACKER)

    def test_close_removes_client(self):
        import routes.blog_routes as blog_routes

        self.client.post('/api/heartbeat', json={'clientId': 'c1'})
        res = self.client.post('/api/close', json={'clientId': 'c1'})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json().get('ok'))
        self.assertNotIn('c1', blog_routes._CLIENT_TRACKER)


if __name__ == '__main__':
    unittest.main()
