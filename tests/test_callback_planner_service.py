"""콜백 플래너 서비스 테스트."""
import unittest
from services.callback_planner_service import (
    plan_callbacks,
    check_callback_resolution,
    suggest_resolution,
    CallbackPoint,
    UnresolvedCallback,
)


class TestPlanCallbacksEmpty(unittest.TestCase):
    """빈 입력 처리 테스트."""

    def test_empty_list(self):
        result = plan_callbacks([])
        self.assertEqual(result, [])

    def test_empty_content(self):
        result = plan_callbacks([{'episode': 1, 'content': ''}])
        self.assertEqual(result, [])

    def test_none_content(self):
        result = plan_callbacks([{'episode': 1, 'content': None}])
        self.assertEqual(result, [])


class TestPlanCallbacksForeshadowing(unittest.TestCase):
    """떡밥(foreshadowing) 감지 테스트."""

    def test_foreshadow_detected(self):
        """'나중에' 키워드로 떡밥 감지."""
        episodes = [
            {'episode': 1, 'content': '이 기능은 나중에 자세히 다루겠습니다.'},
        ]
        result = plan_callbacks(episodes)
        foreshadows = [p for p in result if p.callback_type == 'foreshadowing']
        self.assertGreater(len(foreshadows), 0)

    def test_foreshadow_not_resolved(self):
        """감지된 떡밥은 기본적으로 미회수 상태."""
        episodes = [
            {'episode': 1, 'content': '이 주제는 추후 다시 다루겠습니다.'},
        ]
        result = plan_callbacks(episodes)
        foreshadows = [p for p in result if p.callback_type == 'foreshadowing']
        self.assertTrue(all(not p.resolved for p in foreshadows))


class TestPlanCallbacksQuestion(unittest.TestCase):
    """질문형 감지 테스트."""

    def test_question_detected(self):
        episodes = [
            {'episode': 1, 'content': '과연 이 방법이 효과가 있을까?'},
        ]
        result = plan_callbacks(episodes)
        questions = [p for p in result if p.callback_type == 'question']
        self.assertGreater(len(questions), 0)

    def test_wonder_keyword(self):
        episodes = [
            {'episode': 1, 'content': '많은 사람들이 궁금하게 여기는 주제입니다.'},
        ]
        result = plan_callbacks(episodes)
        questions = [p for p in result if p.callback_type == 'question']
        self.assertGreater(len(questions), 0)


class TestPlanCallbacksCliffhanger(unittest.TestCase):
    """클리프행어 감지 테스트."""

    def test_cliffhanger_detected(self):
        episodes = [
            {'episode': 1, 'content': '결과는 다음 편에서 공개합니다.'},
        ]
        result = plan_callbacks(episodes)
        cliffhangers = [p for p in result if p.callback_type == 'cliffhanger']
        self.assertGreater(len(cliffhangers), 0)

    def test_cliffhanger_target_next_episode(self):
        """클리프행어의 target_episode는 다음 에피소드."""
        episodes = [
            {'episode': 3, 'content': '다음 편에서 이어집니다.'},
        ]
        result = plan_callbacks(episodes)
        cliffhangers = [p for p in result if p.callback_type == 'cliffhanger']
        self.assertTrue(any(p.target_episode == 4 for p in cliffhangers))


class TestPlanCallbacksCallback(unittest.TestCase):
    """회수(callback) 감지 테스트."""

    def test_callback_detected(self):
        episodes = [
            {'episode': 2, 'content': '앞서 언급했던 내용을 정리하겠습니다.'},
        ]
        result = plan_callbacks(episodes)
        callbacks = [p for p in result if p.callback_type == 'callback']
        self.assertGreater(len(callbacks), 0)

    def test_callback_resolved_by_default(self):
        """callback 타입은 기본적으로 resolved=True."""
        episodes = [
            {'episode': 2, 'content': '이전에 설명했던 방법을 적용합니다.'},
        ]
        result = plan_callbacks(episodes)
        callbacks = [p for p in result if p.callback_type == 'callback']
        self.assertTrue(all(p.resolved for p in callbacks))


class TestPlanCallbacksMatching(unittest.TestCase):
    """떡밥-회수 매칭 테스트."""

    def test_foreshadow_resolved_by_callback(self):
        """이전 에피소드의 떡밥이 이후 에피소드의 callback으로 회수됨."""
        episodes = [
            {'episode': 1, 'content': '이 기술은 나중에 자세히 설명하겠습니다.'},
            {'episode': 2, 'content': '일반적인 내용입니다. 특별한 키워드가 없습니다.'},
            {'episode': 3, 'content': '앞서 언급했던 기술에 대해 설명합니다.'},
        ]
        result = plan_callbacks(episodes)
        foreshadows = [p for p in result if p.callback_type == 'foreshadowing']
        # 매칭되면 resolved=True
        resolved = [p for p in foreshadows if p.resolved]
        self.assertGreater(len(resolved), 0)

    def test_position_detection(self):
        """포인트의 position이 유효한 값인지 확인."""
        episodes = [
            {'episode': 1, 'content': '나중에 다룰 내용. 중간 부분. 다음 편에서 계속.'},
        ]
        result = plan_callbacks(episodes)
        valid_positions = {'intro', 'middle', 'outro'}
        for point in result:
            self.assertIn(point.position, valid_positions)


class TestCheckCallbackResolution(unittest.TestCase):
    """미회수 떡밥 추적 테스트."""

    def test_empty_episodes(self):
        result = check_callback_resolution([])
        self.assertEqual(result, [])

    def test_unresolved_returned(self):
        """미회수 떡밥이 반환됨."""
        episodes = [
            {'episode': 1, 'content': '이 주제는 나중에 자세히 다루겠습니다.'},
            {'episode': 2, 'content': '일반 내용입니다. 특별한 것은 없습니다.'},
        ]
        result = check_callback_resolution(episodes)
        self.assertGreater(len(result), 0)
        self.assertIsInstance(result[0], UnresolvedCallback)

    def test_urgency_high_after_three_episodes(self):
        """3회 이상 미회수 시 urgency=high (완료 조건)."""
        episodes = [
            {'episode': 1, 'content': '이것은 나중에 설명하겠습니다.'},
            {'episode': 2, 'content': '일반 내용입니다.'},
            {'episode': 3, 'content': '일반 내용입니다.'},
            {'episode': 4, 'content': '일반 내용입니다.'},
        ]
        result = check_callback_resolution(episodes)
        high_urgency = [u for u in result if u.urgency == 'high']
        self.assertGreater(len(high_urgency), 0)

    def test_urgency_medium_after_two_episodes(self):
        """2회 미회수 시 urgency=medium."""
        episodes = [
            {'episode': 1, 'content': '추후 다시 다루겠습니다.'},
            {'episode': 2, 'content': '일반 내용입니다.'},
            {'episode': 3, 'content': '일반 내용입니다.'},
        ]
        result = check_callback_resolution(episodes)
        medium_or_high = [u for u in result if u.urgency in ('medium', 'high')]
        self.assertGreater(len(medium_or_high), 0)

    def test_resolved_not_in_unresolved(self):
        """회수된 떡밥은 미회수 목록에 없음."""
        episodes = [
            {'episode': 1, 'content': '이것은 나중에 설명하겠습니다.'},
            {'episode': 2, 'content': '앞서 언급했던 내용을 이제 설명합니다.'},
        ]
        result = check_callback_resolution(episodes)
        # 회수되었으므로 미회수 목록이 비어야 함
        foreshadow_unresolved = [
            u for u in result
            if u.point.callback_type == 'foreshadowing'
        ]
        self.assertEqual(len(foreshadow_unresolved), 0)

    def test_urgency_ordering(self):
        """결과가 urgency 순서로 정렬 (high > medium > low)."""
        episodes = [
            {'episode': 1, 'content': '나중에 다룰 주제입니다.'},
            {'episode': 1, 'content': '과연 어떻게 될까?'},
            {'episode': 2, 'content': '일반 내용입니다.'},
            {'episode': 3, 'content': '일반 내용입니다.'},
            {'episode': 4, 'content': '일반 내용입니다.'},
            {'episode': 5, 'content': '일반 내용입니다.'},
        ]
        result = check_callback_resolution(episodes)
        if len(result) >= 2:
            order = {'high': 0, 'medium': 1, 'low': 2}
            urgencies = [order[u.urgency] for u in result]
            self.assertEqual(urgencies, sorted(urgencies))


class TestSuggestResolution(unittest.TestCase):
    """회수 제안 테스트."""

    def test_empty_input(self):
        result = suggest_resolution([])
        self.assertEqual(result, [])

    def test_high_urgency_suggestion(self):
        """urgency=high일 때 '긴급' 포함."""
        point = CallbackPoint(
            episode=1, position='middle',
            callback_type='foreshadowing',
            description='나중에 다룰 내용',
            target_episode=None, resolved=False,
        )
        unresolved = [UnresolvedCallback(point=point, episodes_waiting=4, urgency='high')]
        result = suggest_resolution(unresolved)
        self.assertEqual(len(result), 1)
        self.assertIn('긴급', result[0]['suggestion'])

    def test_suggestion_structure(self):
        """반환 구조 확인."""
        point = CallbackPoint(
            episode=2, position='outro',
            callback_type='question',
            description='과연 어떻게 될까',
            target_episode=None, resolved=False,
        )
        unresolved = [UnresolvedCallback(point=point, episodes_waiting=1, urgency='low')]
        result = suggest_resolution(unresolved)
        self.assertEqual(len(result), 1)
        item = result[0]
        self.assertIn('episode_origin', item)
        self.assertIn('description', item)
        self.assertIn('urgency', item)
        self.assertIn('suggestion', item)
        self.assertIn('recommended_episode', item)
        self.assertEqual(item['episode_origin'], 2)

    def test_medium_urgency_suggestion(self):
        """urgency=medium일 때 적절한 메시지."""
        point = CallbackPoint(
            episode=1, position='intro',
            callback_type='foreshadowing',
            description='추후 설명할 내용',
            target_episode=None, resolved=False,
        )
        unresolved = [UnresolvedCallback(point=point, episodes_waiting=2, urgency='medium')]
        result = suggest_resolution(unresolved)
        self.assertIn('경과', result[0]['suggestion'])

    def test_recommended_episode_for_high(self):
        """high urgency에서 recommended_episode가 설정됨."""
        point = CallbackPoint(
            episode=1, position='middle',
            callback_type='cliffhanger',
            description='다음 편에서 계속',
            target_episode=2, resolved=False,
        )
        unresolved = [UnresolvedCallback(point=point, episodes_waiting=5, urgency='high')]
        result = suggest_resolution(unresolved)
        self.assertIsNotNone(result[0]['recommended_episode'])


class TestCallbackPointDataclass(unittest.TestCase):
    """CallbackPoint dataclass 구조 테스트."""

    def test_default_resolved_false(self):
        point = CallbackPoint(
            episode=1, position='intro',
            callback_type='foreshadowing',
            description='테스트', target_episode=None,
        )
        self.assertFalse(point.resolved)

    def test_all_fields_accessible(self):
        point = CallbackPoint(
            episode=1, position='outro',
            callback_type='cliffhanger',
            description='다음 편에서',
            target_episode=2, resolved=False,
        )
        self.assertEqual(point.episode, 1)
        self.assertEqual(point.position, 'outro')
        self.assertEqual(point.callback_type, 'cliffhanger')
        self.assertEqual(point.target_episode, 2)


if __name__ == '__main__':
    unittest.main()
