"""allhands_briefing_service 단위 테스트"""
import unittest

from services.allhands_briefing_service import (
    BriefingPack,
    create_briefing_pack,
    _extract_decisions,
    _extract_action_items,
    _extract_clip_segments,
    _extract_attendee_topics,
    _generate_summary,
    _strip_timestamp,
    _extract_owner,
    _extract_deadline,
    _add_minutes,
    _split_lines,
)


class TestCreateBriefingPack(unittest.TestCase):
    """create_briefing_pack 함수 통합 테스트"""

    def test_empty_transcript_raises(self):
        """빈 자막이면 ValueError 발생"""
        with self.assertRaises(ValueError):
            create_briefing_pack('')

    def test_whitespace_only_raises(self):
        """공백만 있는 자막이면 ValueError 발생"""
        with self.assertRaises(ValueError):
            create_briefing_pack('   \n  \t  ')

    def test_none_raises(self):
        """None 입력이면 ValueError 발생"""
        with self.assertRaises(ValueError):
            create_briefing_pack(None)

    def test_basic_briefing_generation(self):
        """기본 미팅 자막에서 브리핑 팩 생성"""
        transcript = (
            '[0:00] 안녕하세요 오늘 올핸즈 미팅을 시작하겠습니다\n'
            '[1:30] 주제: Q4 매출 실적 리뷰\n'
            '[3:00] 매출 목표 120% 달성으로 확정했습니다\n'
            '[5:00] 다음 주제: 신규 프로젝트 킥오프\n'
            '[7:00] 김팀장님이 프로젝트 계획서를 다음 주까지 준비해주세요\n'
            '[9:00] 다음 안건: 채용 계획\n'
            '[11:00] 개발팀 3명 추가 채용으로 결정했습니다\n'
            '[13:00] 박매니저님이 채용 공고를 이번 주까지 작성해주세요\n'
            '[15:00] 오늘 미팅 마무리하겠습니다\n'
        )
        result = create_briefing_pack(transcript)

        self.assertIsInstance(result, BriefingPack)
        self.assertGreaterEqual(len(result.clip_segments), 3)
        self.assertTrue(result.summary)

    def test_clip_segments_minimum_three(self):
        """클립 구간이 최소 3개 보장되는지 확인"""
        transcript = (
            '오늘 회의를 시작하겠습니다\n'
            '첫 번째 안건입니다\n'
            '두 번째 안건입니다\n'
            '세 번째 안건입니다\n'
            '회의를 마치겠습니다\n'
        )
        result = create_briefing_pack(transcript)
        self.assertGreaterEqual(len(result.clip_segments), 3)

    def test_clip_segments_have_required_fields(self):
        """각 클립 구간에 start, end, topic 필드 존재"""
        transcript = (
            '[0:00] 시작합니다\n'
            '[5:00] 다음 주제: 매출 현황\n'
            '[10:00] 다음으로 넘어가겠습니다\n'
            '[15:00] 주제: 인사 관련\n'
            '[20:00] 끝\n'
        )
        result = create_briefing_pack(transcript)
        for seg in result.clip_segments:
            self.assertIn('start', seg)
            self.assertIn('end', seg)
            self.assertIn('topic', seg)

    def test_key_decisions_extracted(self):
        """결정 사항이 올바르게 추출되는지 확인"""
        transcript = (
            '예산 200만원으로 확정했습니다\n'
            '일정은 다음 달 시작으로 결정했습니다\n'
            '그냥 지나가는 말입니다\n'
            'A안으로 하겠습니다\n'
            '점심 뭐 먹을까요\n'
        )
        result = create_briefing_pack(transcript)
        self.assertGreaterEqual(len(result.key_decisions), 2)

    def test_action_items_extracted(self):
        """액션 아이템이 올바르게 추출되는지 확인"""
        transcript = (
            '김팀장님이 보고서를 다음 주까지 작성해주세요\n'
            '이매니저님이 예산 검토를 진행해주세요\n'
            '일반적인 논의 내용입니다\n'
            'TODO: 회의록 공유\n'
            '주제: 분기 실적\n'
        )
        result = create_briefing_pack(transcript)
        self.assertGreaterEqual(len(result.action_items), 2)
        for item in result.action_items:
            self.assertIn('owner', item)
            self.assertIn('task', item)
            self.assertIn('deadline', item)

    def test_summary_not_empty(self):
        """요약이 비어있지 않은지 확인"""
        transcript = '오늘 회의를 시작합니다\n결론은 A안으로 결정했습니다\n회의 끝'
        result = create_briefing_pack(transcript)
        self.assertTrue(result.summary)

    def test_attendee_topics_extracted(self):
        """참석자 토픽이 추출되는지 확인"""
        transcript = (
            '주제: 매출 리뷰\n'
            '안건: 채용 계획\n'
            '이슈: 서버 장애 대응\n'
            '일반 대화입니다\n'
        )
        result = create_briefing_pack(transcript)
        self.assertGreaterEqual(len(result.attendee_topics), 2)

    def test_english_meeting_transcript(self):
        """영어 미팅 자막도 처리되는지 확인"""
        transcript = (
            '[0:00] Let us start the all-hands meeting\n'
            '[2:00] Next topic: Q4 revenue review\n'
            '[5:00] We decided to increase the budget by 20%\n'
            '[8:00] John will prepare the report by next week\n'
            '[10:00] Moving on to hiring plans\n'
            '[12:00] We agreed to hire 3 developers\n'
            '[14:00] Sarah needs to post the job listings\n'
            '[16:00] That concludes today\'s meeting\n'
        )
        result = create_briefing_pack(transcript)
        self.assertGreaterEqual(len(result.clip_segments), 3)
        self.assertGreaterEqual(len(result.key_decisions), 1)


class TestExtractDecisions(unittest.TestCase):
    """_extract_decisions 함수 단위 테스트"""

    def test_korean_decision_keywords(self):
        lines = ['예산이 확정되었습니다', '일정을 결정했습니다', '일반 문장']
        result = _extract_decisions(lines)
        self.assertEqual(len(result), 2)

    def test_no_decisions(self):
        lines = ['오늘 날씨가 좋습니다', '점심 뭐 먹을까요']
        result = _extract_decisions(lines)
        self.assertEqual(len(result), 0)

    def test_duplicate_decisions_removed(self):
        lines = ['A안으로 결정했습니다', 'A안으로 결정했습니다']
        result = _extract_decisions(lines)
        self.assertEqual(len(result), 1)

    def test_approval_detected(self):
        lines = ['예산안이 승인되었습니다']
        result = _extract_decisions(lines)
        self.assertEqual(len(result), 1)

    def test_direction_phrase(self):
        lines = ['이 방향으로 진행하겠습니다']
        result = _extract_decisions(lines)
        self.assertEqual(len(result), 1)


class TestExtractActionItems(unittest.TestCase):
    """_extract_action_items 함수 단위 테스트"""

    def test_korean_owner_detected(self):
        lines = ['김팀장님이 보고서를 작성해주세요']
        result = _extract_action_items(lines)
        self.assertGreaterEqual(len(result), 1)
        self.assertEqual(result[0]['owner'], '김')

    def test_todo_keyword(self):
        lines = ['TODO: 회의록 배포']
        result = _extract_action_items(lines)
        self.assertGreaterEqual(len(result), 1)

    def test_deadline_extracted(self):
        lines = ['박매니저님이 기획서를 다음 주까지 준비해주세요']
        result = _extract_action_items(lines)
        if result:
            self.assertIn('deadline', result[0])

    def test_no_action_items(self):
        lines = ['오늘 날씨가 좋습니다', '커피 한잔 하실래요']
        result = _extract_action_items(lines)
        self.assertEqual(len(result), 0)


class TestExtractClipSegments(unittest.TestCase):
    """_extract_clip_segments 함수 단위 테스트"""

    def test_minimum_three_segments(self):
        lines = ['짧은 미팅', '안건 하나만', '끝']
        result = _extract_clip_segments(lines, '\n'.join(lines))
        self.assertGreaterEqual(len(result), 3)

    def test_timestamps_preserved(self):
        lines = [
            '[0:00] 시작',
            '[5:00] 다음 주제: 매출',
            '[10:00] 넘어가겠습니다',
            '[15:00] 주제: 채용',
        ]
        result = _extract_clip_segments(lines, '\n'.join(lines))
        # 타임스탬프가 포함된 세그먼트 확인
        for seg in result:
            self.assertTrue(':' in seg['start'])

    def test_max_ten_segments(self):
        """최대 10개 세그먼트로 제한"""
        lines = [f'[{i}:00] 다음 주제: 안건 {i}' for i in range(15)]
        result = _extract_clip_segments(lines, '\n'.join(lines))
        self.assertLessEqual(len(result), 10)


class TestUtilityFunctions(unittest.TestCase):
    """유틸리티 함수 테스트"""

    def test_strip_timestamp_mm_ss(self):
        result = _strip_timestamp('[3:45] 안녕하세요')
        self.assertEqual(result, '안녕하세요')

    def test_strip_timestamp_hh_mm_ss(self):
        result = _strip_timestamp('[1:23:45] 시작합니다')
        self.assertEqual(result, '시작합니다')

    def test_strip_no_timestamp(self):
        result = _strip_timestamp('타임스탬프 없는 문장')
        self.assertEqual(result, '타임스탬프 없는 문장')

    def test_extract_owner_korean(self):
        result = _extract_owner('김팀장님이 처리')
        self.assertEqual(result, '김')

    def test_extract_owner_english(self):
        result = _extract_owner('John will handle this')
        self.assertEqual(result, 'John')

    def test_extract_owner_fallback(self):
        result = _extract_owner('누군가 해야 합니다')
        self.assertEqual(result, '미정')

    def test_extract_deadline_korean_date(self):
        result = _extract_deadline('3월 15일까지 완료')
        self.assertTrue(result != '미정')

    def test_extract_deadline_relative(self):
        result = _extract_deadline('다음 주까지 보고서 제출')
        self.assertTrue(result != '미정')

    def test_extract_deadline_none(self):
        result = _extract_deadline('그냥 하면 됩니다')
        self.assertEqual(result, '미정')

    def test_add_minutes_mm_ss(self):
        result = _add_minutes('5:30', 2)
        self.assertEqual(result, '7:30')

    def test_add_minutes_hh_mm_ss(self):
        result = _add_minutes('1:58:00', 5)
        self.assertEqual(result, '2:03:00')

    def test_generate_summary_with_data(self):
        result = _generate_summary(
            ['결정1', '결정2'],
            [{'owner': 'A', 'task': 'T', 'deadline': 'D'}],
            ['토픽1'],
        )
        self.assertIn('결정 2건', result)
        self.assertIn('액션 아이템 1건', result)

    def test_generate_summary_empty(self):
        result = _generate_summary([], [], [])
        self.assertEqual(result, '미팅 브리핑 요약')

    def test_split_lines_basic(self):
        result = _split_lines('첫째\n둘째\n셋째')
        self.assertEqual(len(result), 3)

    def test_split_lines_empty_removed(self):
        result = _split_lines('첫째\n\n둘째\n\n셋째')
        self.assertEqual(len(result), 3)


if __name__ == '__main__':
    unittest.main()
