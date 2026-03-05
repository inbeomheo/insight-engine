"""
WhitelabelService 단위 테스트 (F4-15)
"""
import unittest
from services.whitelabel_service import WhitelabelService


class TestWhitelabelService(unittest.TestCase):

    def setUp(self):
        self.svc = WhitelabelService()

    def test_get_default_branding(self):
        brand = self.svc.get_branding('ws-1')
        self.assertEqual(brand['app_name'], 'Insight Engine')

    def test_set_branding(self):
        result = self.svc.set_branding('ws-1', {'app_name': 'My App', 'primary_color': '#ff0000'})
        self.assertEqual(result['app_name'], 'My App')
        self.assertEqual(result['primary_color'], '#ff0000')

    def test_set_branding_ignores_unknown_keys(self):
        result = self.svc.set_branding('ws-1', {'unknown_key': 'value', 'app_name': 'X'})
        self.assertEqual(result['app_name'], 'X')
        self.assertNotIn('unknown_key', result)

    def test_reset_branding(self):
        self.svc.set_branding('ws-1', {'app_name': 'Custom'})
        result = self.svc.reset_branding('ws-1')
        self.assertEqual(result['app_name'], 'Insight Engine')

    def test_validate_domain(self):
        result = self.svc.validate_domain('example.com')
        self.assertTrue(result['valid'])

    def test_validate_domain_empty(self):
        result = self.svc.validate_domain('')
        self.assertFalse(result['valid'])

    def test_validate_domain_bad_format(self):
        result = self.svc.validate_domain('nodots')
        self.assertFalse(result['valid'])

    def test_validate_domain_duplicate(self):
        self.svc.set_branding('ws-1', {'custom_domain': 'taken.com'})
        result = self.svc.validate_domain('taken.com')
        self.assertFalse(result['valid'])


if __name__ == '__main__':
    unittest.main()
