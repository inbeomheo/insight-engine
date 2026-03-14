"""workflow_service 단위 테스트"""
import unittest

from services.data import workflow_service


class TestWorkflowService(unittest.TestCase):

    def setUp(self):
        with workflow_service._lock:
            workflow_service._workflows.clear()
            workflow_service._execution_log.clear()
            workflow_service._action_handlers.clear()

    def test_create_workflow(self):
        """워크플로우 생성"""
        wf = workflow_service.create_workflow(
            'auto-notify', 'ws1', 'status_change',
            {'to_status': 'review'}, [{'type': 'notify'}]
        )
        self.assertIn('id', wf)
        self.assertEqual(wf['trigger'], 'status_change')

    def test_invalid_trigger(self):
        """잘못된 트리거"""
        with self.assertRaises(ValueError):
            workflow_service.create_workflow('wf', 'ws1', 'invalid', {}, [])

    def test_update_workflow(self):
        """워크플로우 업데이트"""
        wf = workflow_service.create_workflow('wf', 'ws1', 'created', {}, [])
        updated = workflow_service.update_workflow(wf['id'], name='renamed')
        self.assertEqual(updated['name'], 'renamed')

    def test_update_nonexistent(self):
        """없는 워크플로우 업데이트"""
        self.assertIsNone(workflow_service.update_workflow('bad', name='x'))

    def test_delete_workflow(self):
        """워크플로우 삭제"""
        wf = workflow_service.create_workflow('wf', 'ws1', 'created', {}, [])
        self.assertTrue(workflow_service.delete_workflow(wf['id']))
        self.assertFalse(workflow_service.delete_workflow(wf['id']))

    def test_list_workflows(self):
        """워크플로우 목록"""
        workflow_service.create_workflow('wf1', 'ws1', 'created', {}, [])
        workflow_service.create_workflow('wf2', 'ws2', 'created', {}, [])
        self.assertEqual(len(workflow_service.list_workflows('ws1')), 1)
        self.assertEqual(len(workflow_service.list_workflows()), 2)

    def test_fire_trigger_matches(self):
        """트리거 발동 — 조건 일치"""
        workflow_service.create_workflow(
            'auto', 'ws1', 'status_change',
            {'to_status': 'review'}, [{'type': 'notify'}]
        )
        results = workflow_service.fire_trigger(
            'status_change', 'item1', 'ws1', {'to_status': 'review'}
        )
        self.assertEqual(len(results), 1)

    def test_fire_trigger_no_match(self):
        """트리거 발동 — 조건 불일치"""
        workflow_service.create_workflow(
            'auto', 'ws1', 'status_change',
            {'to_status': 'review'}, [{'type': 'notify'}]
        )
        results = workflow_service.fire_trigger(
            'status_change', 'item1', 'ws1', {'to_status': 'published'}
        )
        self.assertEqual(len(results), 0)

    def test_handler_execution(self):
        """등록된 핸들러 실행"""
        called = []
        workflow_service.register_handler('notify', lambda **kw: called.append(kw))
        workflow_service.create_workflow(
            'wf', 'ws1', 'created', {}, [{'type': 'notify'}]
        )
        workflow_service.fire_trigger('created', 'item1', 'ws1')
        self.assertEqual(len(called), 1)

    def test_execution_log(self):
        """실행 로그 기록"""
        workflow_service.create_workflow('wf', 'ws1', 'created', {}, [])
        workflow_service.fire_trigger('created', 'item1', 'ws1')
        log = workflow_service.get_execution_log()
        self.assertEqual(len(log), 1)

    def test_disabled_workflow_skipped(self):
        """비활성 워크플로우 건너뜀"""
        wf = workflow_service.create_workflow('wf', 'ws1', 'created', {}, [], is_enabled=False)
        results = workflow_service.fire_trigger('created', 'item1', 'ws1')
        self.assertEqual(len(results), 0)


if __name__ == '__main__':
    unittest.main()
