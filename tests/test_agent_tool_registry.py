"""agent/registry — Tool Registry 단위 테스트

Hermes 패턴 기반 에이전트 도구 레지스트리:
등록/조회/스키마/필터/디스패치/가용성 체크.
싱글톤이므로 각 테스트에서 reset() 으로 격리.
"""
import json
import unittest

from agent.registry import ToolRegistry, ToolEntry, registry


class _RegistryTestBase(unittest.TestCase):
    """싱글톤 격리를 위한 reset 베이스"""

    def setUp(self):
        registry.reset()
        self.reg = registry

    def tearDown(self):
        registry.reset()

    def _register_sample(self, name='tool1', toolset='sample',
                        check_fn=None, handler=None, tags=None, is_async=False):
        self.reg.register(
            name=name,
            toolset=toolset,
            description=f'{name} 설명',
            parameters={'type': 'object', 'properties': {'x': {'type': 'string'}}, 'required': ['x']},
            handler=handler or (lambda args, **kw: {'echo': args.get('x', '')}),
            check_fn=check_fn,
            is_async=is_async,
            tags=tags or [],
        )


class TestToolEntrySchema(unittest.TestCase):

    def test_schema_format(self):
        entry = ToolEntry(
            name='analyze',
            toolset='ana',
            description='분석',
            parameters={'type': 'object'},
            handler=lambda a, **kw: a,
        )
        schema = entry.schema
        self.assertEqual(schema['type'], 'function')
        self.assertEqual(schema['function']['name'], 'analyze')
        self.assertEqual(schema['function']['description'], '분석')

    def test_available_no_check_fn(self):
        entry = ToolEntry(name='t', toolset='s', description='d', parameters={}, handler=lambda a: a)
        self.assertTrue(entry.available)

    def test_available_with_passing_check(self):
        entry = ToolEntry(name='t', toolset='s', description='d', parameters={},
                          handler=lambda a: a, check_fn=lambda: True)
        self.assertTrue(entry.available)

    def test_unavailable_when_check_returns_false(self):
        entry = ToolEntry(name='t', toolset='s', description='d', parameters={},
                          handler=lambda a: a, check_fn=lambda: False)
        self.assertFalse(entry.available)

    def test_unavailable_when_check_raises(self):
        entry = ToolEntry(name='t', toolset='s', description='d', parameters={},
                          handler=lambda a: a, check_fn=lambda: 1/0)
        self.assertFalse(entry.available)


class TestRegistryRegisterGet(_RegistryTestBase):

    def test_register_and_get(self):
        self._register_sample('tool_a')
        entry = self.reg.get('tool_a')
        self.assertIsNotNone(entry)
        self.assertEqual(entry.name, 'tool_a')

    def test_get_unknown_returns_none(self):
        self.assertIsNone(self.reg.get('unknown'))

    def test_re_register_overwrites(self):
        self._register_sample('t', toolset='ts1')
        self._register_sample('t', toolset='ts2')
        entry = self.reg.get('t')
        self.assertEqual(entry.toolset, 'ts2')

    def test_unregister(self):
        self._register_sample('t')
        self.assertTrue(self.reg.unregister('t'))
        self.assertIsNone(self.reg.get('t'))

    def test_unregister_unknown(self):
        self.assertFalse(self.reg.unregister('nonexistent'))


class TestRegistryListAndFilter(_RegistryTestBase):

    def test_list_all(self):
        self._register_sample('a', toolset='alpha')
        self._register_sample('b', toolset='beta')
        result = self.reg.list_tools()
        self.assertEqual(len(result), 2)

    def test_filter_by_toolset(self):
        self._register_sample('a', toolset='alpha')
        self._register_sample('b', toolset='beta')
        result = self.reg.list_tools(toolsets=['alpha'])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, 'a')

    def test_filter_available_only(self):
        self._register_sample('on')
        self._register_sample('off', check_fn=lambda: False)
        result = self.reg.list_tools(available_only=True)
        names = {e.name for e in result}
        self.assertEqual(names, {'on'})

    def test_include_unavailable_when_flag_false(self):
        self._register_sample('on')
        self._register_sample('off', check_fn=lambda: False)
        result = self.reg.list_tools(available_only=False)
        self.assertEqual(len(result), 2)

    def test_filter_by_tags(self):
        self._register_sample('a', tags=['fast', 'safe'])
        self._register_sample('b', tags=['slow'])
        result = self.reg.list_tools(tags=['fast'])
        self.assertEqual([e.name for e in result], ['a'])

    def test_get_schemas(self):
        self._register_sample('a')
        schemas = self.reg.get_schemas()
        self.assertEqual(len(schemas), 1)
        self.assertEqual(schemas[0]['function']['name'], 'a')

    def test_get_tool_names(self):
        self._register_sample('a')
        self._register_sample('b')
        names = self.reg.get_tool_names()
        self.assertEqual(set(names), {'a', 'b'})


class TestRegistryDispatch(_RegistryTestBase):

    def test_dispatch_string_result(self):
        self._register_sample('echo', handler=lambda args, **kw: 'plain string')
        result = self.reg.dispatch('echo', {'x': '1'})
        self.assertEqual(result, 'plain string')

    def test_dispatch_dict_result_serialized(self):
        self._register_sample('json', handler=lambda args, **kw: {'count': 5, 'data': '한글'})
        result = self.reg.dispatch('json', {'x': ''})
        parsed = json.loads(result)
        self.assertEqual(parsed['count'], 5)
        self.assertEqual(parsed['data'], '한글')

    def test_dispatch_unknown_raises_key_error(self):
        with self.assertRaises(KeyError):
            self.reg.dispatch('nope', {})

    def test_dispatch_unavailable_returns_error_payload(self):
        self._register_sample('off', check_fn=lambda: False)
        result = self.reg.dispatch('off', {})
        self.assertIn('사용할 수 없습니다', json.loads(result)['error'])

    def test_dispatch_handler_exception_returns_error_payload(self):
        def bad(args, **kw):
            raise RuntimeError('boom')
        self._register_sample('bad', handler=bad)
        result = self.reg.dispatch('bad', {'x': '1'})
        parsed = json.loads(result)
        self.assertIn('boom', parsed['error'])

    def test_dispatch_kwargs_passed(self):
        captured = {}
        def capture(args, **kw):
            captured.update(kw)
            return {}
        self._register_sample('cap', handler=capture)
        self.reg.dispatch('cap', {'x': '1'}, task_id='t-001', user_id='u-1')
        self.assertEqual(captured.get('task_id'), 't-001')
        self.assertEqual(captured.get('user_id'), 'u-1')


class TestRegistryStats(_RegistryTestBase):

    def test_empty_stats(self):
        stats = self.reg.stats()
        self.assertEqual(stats['total_tools'], 0)
        self.assertEqual(stats['available_tools'], 0)
        self.assertEqual(stats['toolsets'], {})

    def test_mixed_availability_stats(self):
        self._register_sample('on1', toolset='ts1')
        self._register_sample('on2', toolset='ts1')
        self._register_sample('off', toolset='ts2', check_fn=lambda: False)
        stats = self.reg.stats()
        self.assertEqual(stats['total_tools'], 3)
        self.assertEqual(stats['available_tools'], 2)
        self.assertEqual(stats['toolsets']['ts1'], 2)
        self.assertEqual(stats['toolsets']['ts2'], 1)

    def test_tool_count_property(self):
        self._register_sample('a')
        self._register_sample('b')
        self.assertEqual(self.reg.tool_count, 2)

    def test_toolset_names_property(self):
        self._register_sample('a', toolset='alpha')
        self._register_sample('b', toolset='beta')
        self.assertEqual(set(self.reg.toolset_names), {'alpha', 'beta'})


class TestSingletonBehavior(unittest.TestCase):

    def test_module_registry_is_singleton(self):
        from agent.registry import registry as r1
        from agent.registry import ToolRegistry
        r2 = ToolRegistry()
        self.assertIs(r1, r2)


if __name__ == '__main__':
    unittest.main()
