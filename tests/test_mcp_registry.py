"""mcp/registry 단위 테스트 — 플러그인 등록/조회/실행/예외 처리"""
import unittest
from typing import Any

from services.mcp.plugin_interface import MCPPlugin
from services.mcp.registry import PluginRegistry, plugin_registry


class _FakePlugin(MCPPlugin):
    """테스트용 가짜 플러그인"""

    def __init__(self, name='Fake', description='테스트용', result=None, raise_exc=None):
        self._name = name
        self._description = description
        self._result = result or {'success': True, 'message': 'ok', 'url': 'https://example.com/1'}
        self._raise_exc = raise_exc
        self.calls: list[dict] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def schema(self) -> dict:
        return {'type': 'object'}

    def execute(self, content: str, title: str, **kwargs: Any) -> dict:
        self.calls.append({'content': content, 'title': title, 'kwargs': kwargs})
        if self._raise_exc:
            raise self._raise_exc
        return self._result


class TestPluginRegistry(unittest.TestCase):
    """PluginRegistry 동작 검증"""

    def setUp(self):
        self.registry = PluginRegistry()

    def test_register_and_get(self):
        plugin = _FakePlugin(name='Naver Blog')
        self.registry.register('naver', plugin)
        self.assertIs(self.registry.get('naver'), plugin)

    def test_get_returns_none_for_unknown_id(self):
        self.assertIsNone(self.registry.get('unknown'))

    def test_register_overrides_existing(self):
        a = _FakePlugin(name='A')
        b = _FakePlugin(name='B')
        self.registry.register('p1', a)
        self.registry.register('p1', b)
        self.assertIs(self.registry.get('p1'), b)

    def test_list_plugins_returns_summary(self):
        self.registry.register('a', _FakePlugin(name='A', description='첫째'))
        self.registry.register('b', _FakePlugin(name='B', description='둘째'))
        result = self.registry.list_plugins()
        self.assertEqual(len(result), 2)
        ids = {item['id'] for item in result}
        self.assertEqual(ids, {'a', 'b'})
        for item in result:
            self.assertIn('name', item)
            self.assertIn('description', item)

    def test_list_plugins_empty(self):
        self.assertEqual(self.registry.list_plugins(), [])

    def test_execute_calls_plugin_with_args(self):
        plugin = _FakePlugin()
        self.registry.register('p', plugin)
        result = self.registry.execute('p', '본문', '제목', api_key='x')
        self.assertTrue(result['success'])
        self.assertEqual(len(plugin.calls), 1)
        self.assertEqual(plugin.calls[0]['content'], '본문')
        self.assertEqual(plugin.calls[0]['title'], '제목')
        self.assertEqual(plugin.calls[0]['kwargs'], {'api_key': 'x'})

    def test_execute_unknown_plugin_returns_failure(self):
        result = self.registry.execute('nope', '본문', '제목')
        self.assertFalse(result['success'])
        self.assertIn('찾을 수 없', result['message'])
        self.assertIsNone(result['url'])

    def test_execute_plugin_exception_wrapped(self):
        """플러그인 execute가 raise하면 success=False + 메시지로 변환"""
        plugin = _FakePlugin(raise_exc=RuntimeError('connection refused'))
        self.registry.register('p', plugin)
        result = self.registry.execute('p', 'body', 'title')
        self.assertFalse(result['success'])
        self.assertIn('connection refused', result['message'])
        self.assertIsNone(result['url'])

    def test_execute_passes_kwargs_through(self):
        plugin = _FakePlugin()
        self.registry.register('p', plugin)
        self.registry.execute('p', 'b', 't', foo=1, bar='baz')
        self.assertEqual(plugin.calls[0]['kwargs'], {'foo': 1, 'bar': 'baz'})


class TestSingletonRegistry(unittest.TestCase):
    """모듈 레벨 싱글턴 plugin_registry"""

    def test_singleton_instance_is_plugin_registry(self):
        self.assertIsInstance(plugin_registry, PluginRegistry)


if __name__ == '__main__':
    unittest.main()
