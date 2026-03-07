"""
시각 콘텐츠 제안 서비스 테스트

suggest_visuals()의 규칙 기반 분석 로직을 검증합니다.
"""
import unittest

from services.visual_content_service import suggest_visuals


class TestVisualContentService(unittest.TestCase):
    """시각 콘텐츠 제안 서비스 단위 테스트"""

    # ── 1. 빈 콘텐츠 ──

    def test_empty_content(self):
        """빈 문자열 입력 시 빈 결과를 반환한다"""
        result = suggest_visuals('')
        self.assertEqual(result['suggestions'], [])
        self.assertEqual(result['summary']['total_suggestions'], 0)
        self.assertEqual(result['summary']['by_type'], {})
        self.assertEqual(result['summary']['visual_density_score'], 0.0)
        self.assertEqual(result['existing_visuals'], [])
        self.assertEqual(result['recommendations'], [])

    # ── 2. None 입력 ──

    def test_none_content(self):
        """None 입력 시 빈 결과를 반환한다"""
        result = suggest_visuals(None)
        self.assertEqual(result['suggestions'], [])
        self.assertEqual(result['summary']['total_suggestions'], 0)

    # ── 3. 차트 제안 ──

    def test_chart_suggestion(self):
        """숫자 데이터가 3개 이상이면 차트를 제안한다"""
        content = (
            "2023년 매출은 500억원이었고, 2024년에는 700억원으로 증가했습니다. "
            "2025년에는 900억원을 달성할 것으로 예상됩니다."
        )
        result = suggest_visuals(content)
        chart_suggestions = [s for s in result['suggestions'] if s['type'] == 'chart']
        self.assertGreaterEqual(len(chart_suggestions), 1)
        self.assertEqual(chart_suggestions[0]['type'], 'chart')
        self.assertIn('priority', chart_suggestions[0])

    # ── 4. 표 제안 ──

    def test_table_suggestion(self):
        """비교 표현이 3개 이상이면 표를 제안한다"""
        content = (
            "React vs Vue vs Angular을 비교하면, "
            "React는 유연한 반면 Angular는 체계적입니다. "
            "Vue 대비 React는 생태계가 넓고, "
            "Angular 대비 Vue는 학습 곡선이 낮습니다. "
            "차이점을 정리하면 각 프레임워크의 장단점이 명확합니다."
        )
        result = suggest_visuals(content)
        table_suggestions = [s for s in result['suggestions'] if s['type'] == 'table']
        self.assertGreaterEqual(len(table_suggestions), 1)
        self.assertEqual(table_suggestions[0]['type'], 'table')

    # ── 5. 인포그래픽 제안 ──

    def test_infographic_suggestion(self):
        """단계 설명이 포함되면 인포그래픽을 제안한다"""
        content = (
            "프로젝트 진행 절차는 다음과 같습니다. "
            "1단계는 기획, 2단계는 디자인, 3단계는 개발, "
            "4단계는 테스트, 5단계는 배포입니다."
        )
        result = suggest_visuals(content)
        infographic_suggestions = [s for s in result['suggestions'] if s['type'] == 'infographic']
        self.assertGreaterEqual(len(infographic_suggestions), 1)
        # 4단계 이상이면 high
        high_priority = [s for s in infographic_suggestions if s['priority'] == 'high']
        self.assertGreaterEqual(len(high_priority), 1)

    # ── 6. 다이어그램 제안 ──

    def test_diagram_suggestion(self):
        """구조/흐름 설명이 포함되면 다이어그램을 제안한다"""
        content = (
            "시스템 아키텍처는 다음과 같은 구조로 구성됩니다. "
            "클라이언트에서 서버로 요청이 전달되고, "
            "서버는 데이터베이스와 연결되어 데이터 흐름을 관리합니다."
        )
        result = suggest_visuals(content)
        diagram_suggestions = [s for s in result['suggestions'] if s['type'] == 'diagram']
        self.assertGreaterEqual(len(diagram_suggestions), 1)
        self.assertEqual(diagram_suggestions[0]['type'], 'diagram')

    # ── 7. 이미지 제안 ──

    def test_image_suggestion(self):
        """긴 텍스트(300자+)가 있으면 이미지를 제안한다"""
        # 300자 이상의 단락 생성
        long_text = "이 서비스는 사용자에게 매우 유용한 기능을 제공합니다. " * 20
        result = suggest_visuals(long_text)
        image_suggestions = [s for s in result['suggestions'] if s['type'] == 'image']
        self.assertGreaterEqual(len(image_suggestions), 1)
        # 단순 긴 텍스트는 low 우선순위
        low_priority = [s for s in image_suggestions if s['priority'] == 'low']
        self.assertGreaterEqual(len(low_priority), 1)

    # ── 8. 스크린샷 제안 ──

    def test_screenshot_suggestion(self):
        """UI 가이드 키워드가 있으면 스크린샷을 제안한다"""
        content = (
            "설정 메뉴에서 '알림' 버튼을 클릭합니다. "
            "그 다음 드롭다운에서 원하는 옵션을 선택하고 저장 버튼을 누릅니다."
        )
        result = suggest_visuals(content)
        screenshot_suggestions = [s for s in result['suggestions'] if s['type'] == 'screenshot']
        self.assertGreaterEqual(len(screenshot_suggestions), 1)

    # ── 9. 기존 시각 요소 감지 ──

    def test_existing_visuals_detected(self):
        """마크다운 이미지, 테이블, 코드 블록을 감지한다"""
        content = (
            "다음은 예시 이미지입니다.\n\n"
            "![예시](image.png)\n\n"
            "| 항목 | 값 |\n|---|---|\n| A | 1 |\n\n"
            "```python\nprint('hello')\n```"
        )
        result = suggest_visuals(content)
        existing = result['existing_visuals']
        self.assertIn('마크다운 이미지', existing)
        self.assertIn('마크다운 테이블', existing)
        self.assertIn('코드 블록', existing)

    # ── 10. 밀도 점수 범위 ──

    def test_visual_density_score(self):
        """밀도 점수는 0~100 범위이다"""
        # 시각 요소 없는 긴 콘텐츠 → 낮은 밀도
        content = "단락1입니다.\n\n단락2입니다.\n\n단락3입니다.\n\n단락4입니다."
        result = suggest_visuals(content)
        score = result['summary']['visual_density_score']
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)

        # 시각 요소가 많은 콘텐츠 → 높은 밀도
        visual_content = (
            "![img1](a.png)\n\n"
            "![img2](b.png)\n\n"
            "![img3](c.png)\n\n"
            "단락입니다."
        )
        result2 = suggest_visuals(visual_content)
        score2 = result2['summary']['visual_density_score']
        self.assertGreater(score2, score)
        self.assertLessEqual(score2, 100.0)

    # ── 11. 타입별 요약 ──

    def test_summary_by_type(self):
        """by_type이 제안된 타입별 개수를 정확히 집계한다"""
        content = (
            "시스템의 구조와 아키텍처를 살펴보겠습니다. "
            "데이터 흐름은 클라이언트에서 서버로 연결됩니다.\n\n"
            "매출 500억원에서 700억원으로 증가했고, 800억원을 돌파했습니다."
        )
        result = suggest_visuals(content)
        by_type = result['summary']['by_type']
        total = result['summary']['total_suggestions']
        self.assertEqual(total, sum(by_type.values()))
        # 각 타입 키가 실제 suggestions의 type과 일치
        suggestion_types = {s['type'] for s in result['suggestions']}
        self.assertEqual(set(by_type.keys()), suggestion_types)

    # ── 12. 우선순위 레벨 ──

    def test_priority_levels(self):
        """모든 제안의 priority는 high/medium/low 중 하나이다"""
        content = (
            "1단계 기획, 2단계 개발, 3단계 테스트, 4단계 배포, 5단계 운영입니다.\n\n"
            "설정 메뉴에서 버튼을 클릭하고 선택합니다.\n\n"
            "매출 100억원, 200억원, 300억원, 400억원, 500억원으로 증가 추이를 보입니다."
        )
        result = suggest_visuals(content)
        valid_priorities = {'high', 'medium', 'low'}
        for s in result['suggestions']:
            self.assertIn(s['priority'], valid_priorities,
                          f"잘못된 priority: {s['priority']}")

    # ── 13. 위치 정보 ──

    def test_location_info(self):
        """모든 제안에 'N번째 단락 뒤' 형식의 location이 포함된다"""
        content = (
            "첫 번째 단락입니다.\n\n"
            "시스템 아키텍처의 구조와 흐름을 설명합니다. "
            "데이터는 연결되어 구성됩니다."
        )
        result = suggest_visuals(content)
        for s in result['suggestions']:
            self.assertRegex(s['location'], r'\d+번째 단락 뒤')

    # ── 14. 전체 제안 ──

    def test_recommendations(self):
        """밀도가 낮으면 가독성 향상 제안이 포함된다"""
        # 시각 요소 없는 여러 단락 → 밀도 0
        content = "단락1.\n\n단락2.\n\n단락3.\n\n단락4.\n\n단락5.\n\n단락6."
        result = suggest_visuals(content)
        self.assertIn(
            '시각 콘텐츠를 추가하면 가독성이 향상됩니다',
            result['recommendations']
        )


if __name__ == '__main__':
    unittest.main()
