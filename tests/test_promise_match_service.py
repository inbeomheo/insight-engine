"""promise_match_service 단위 테스트"""
import unittest


class TestPromiseMatchService(unittest.TestCase):
    """audit_promise_match 함수의 핵심 동작을 검증합니다."""

    def _audit(self, content: str) -> dict:
        from services.quality.promise_match_service import audit_promise_match
        return audit_promise_match(content)

    # --- 엣지 케이스 ---

    def test_empty_content(self):
        """빈 콘텐츠는 빈 결과와 안내 메시지를 반환해야 합니다."""
        result = self._audit('')
        self.assertEqual(result['promises'], [])
        self.assertEqual(result['fulfillment_score'], 0.0)
        self.assertTrue(any('비어' in s for s in result['suggestions']))

    def test_none_content(self):
        """None 입력도 빈 결과를 반환해야 합니다."""
        result = self._audit(None)
        self.assertEqual(result['promises'], [])
        self.assertEqual(result['fulfillment_score'], 0.0)

    def test_no_headings(self):
        """헤딩 없는 일반 텍스트에서도 첫 줄을 제목으로 처리해야 합니다."""
        content = (
            '머신러닝 기초 가이드\n'
            '머신러닝은 인공지능의 한 분야입니다.\n'
            '머신러닝을 통해 데이터를 분석할 수 있습니다.\n'
            '머신러닝 모델은 학습 데이터가 필요합니다.\n'
        )
        result = self._audit(content)
        # 첫 줄에서 키워드 추출
        self.assertTrue(len(result['promises']) > 0)
        sources = {p['source'] for p in result['promises']}
        self.assertIn('title', sources)

    # --- 키워드 추출 ---

    def test_title_keyword_extraction(self):
        """# 마크다운 제목에서 핵심 키워드를 추출해야 합니다."""
        content = (
            '# 파이썬 데이터 분석 입문\n\n'
            '파이썬은 프로그래밍 언어입니다.\n'
            '데이터 분석에 파이썬을 활용합니다.\n'
        )
        result = self._audit(content)
        keywords = [p['keyword'] for p in result['promises']]
        # '파이썬', '데이터', '분석', '입문' 중 일부가 추출되어야 함
        self.assertTrue(any('파이썬' in kw for kw in keywords) or
                        any('데이터' in kw for kw in keywords))
        # source가 title인 항목 존재
        self.assertTrue(any(p['source'] == 'title' for p in result['promises']))

    def test_heading_keyword_extraction(self):
        """## 소제목에서 키워드를 추출해야 합니다."""
        content = (
            '# 웹 개발 가이드\n\n'
            '## 프론트엔드 기초\n'
            '프론트엔드는 사용자 화면을 담당합니다.\n'
            '프론트엔드 개발에는 HTML이 필요합니다.\n'
            '프론트엔드 프레임워크도 중요합니다.\n\n'
            '## 백엔드 구조\n'
            '백엔드는 서버를 담당합니다.\n'
            '백엔드 개발에는 데이터베이스가 필요합니다.\n'
            '백엔드 API를 설계해야 합니다.\n'
        )
        result = self._audit(content)
        heading_promises = [p for p in result['promises'] if p['source'] == 'heading']
        self.assertTrue(len(heading_promises) > 0)
        heading_keywords = [p['keyword'] for p in heading_promises]
        self.assertTrue(
            any('프론트엔드' in kw for kw in heading_keywords) or
            any('백엔드' in kw for kw in heading_keywords)
        )

    # --- 이행 상태 검증 ---

    def test_fulfilled_promise(self):
        """본문에 충분히 등장하는 키워드는 fulfilled 상태여야 합니다."""
        content = (
            '# 클라우드 컴퓨팅 활용법\n\n'
            '클라우드 컴퓨팅은 현대 IT의 핵심입니다.\n'
            '클라우드 환경에서는 자원을 유연하게 배분합니다.\n'
            '클라우드 서비스를 선택할 때 주의가 필요합니다.\n'
            '클라우드 비용 최적화도 중요한 과제입니다.\n'
        )
        result = self._audit(content)
        cloud_promise = next(
            (p for p in result['promises'] if '클라우드' in p['keyword']), None
        )
        self.assertIsNotNone(cloud_promise)
        self.assertTrue(cloud_promise['found_in_body'])
        self.assertEqual(cloud_promise['status'], 'fulfilled')
        self.assertGreaterEqual(cloud_promise['frequency'], 3)

    def test_missing_promise(self):
        """본문에 전혀 등장하지 않는 키워드는 missing 상태여야 합니다."""
        content = (
            '# 블록체인과 암호화폐 이해하기\n\n'
            '이 글에서는 기술의 발전에 대해 알아봅니다.\n'
            '최근 많은 관심을 받고 있는 분야입니다.\n'
            '관련 기술은 계속 진화하고 있습니다.\n'
        )
        result = self._audit(content)
        blockchain = next(
            (p for p in result['promises'] if '블록체인' in p['keyword']), None
        )
        # '블록체인'이 제목에서 추출되었지만 본문에 없음
        if blockchain:
            self.assertFalse(blockchain['found_in_body'])
            self.assertEqual(blockchain['status'], 'missing')
            self.assertEqual(blockchain['frequency'], 0)

    def test_weak_promise(self):
        """본문에 1회만 등장하는 키워드는 weak 상태여야 합니다."""
        content = (
            '# 도커 컨테이너 배포 전략\n\n'
            '도커는 가상화 기술의 하나입니다.\n'
            '서버 환경을 구성할 때 다양한 도구가 활용됩니다.\n'
            '자동화된 파이프라인이 중요합니다.\n'
        )
        result = self._audit(content)
        docker_promise = next(
            (p for p in result['promises'] if '도커' in p['keyword']), None
        )
        if docker_promise:
            # 1회만 등장하면 weak
            self.assertEqual(docker_promise['status'], 'weak')

    # --- 위치 감지 ---

    def test_intro_detection(self):
        """도입부(첫 20%)에 키워드가 있으면 in_intro가 True여야 합니다."""
        # 10줄 중 앞 2줄이 도입부 (20%)
        body_lines = ['키워드가 첫 문장에 나옵니다.']
        body_lines += ['일반 텍스트입니다.'] * 9
        content = '# 키워드 테스트\n\n' + '\n'.join(body_lines)

        result = self._audit(content)
        kw_promise = next(
            (p for p in result['promises'] if '키워드' in p['keyword']), None
        )
        if kw_promise:
            self.assertTrue(kw_promise['in_intro'])

    def test_conclusion_detection(self):
        """결론부(마지막 20%)에 키워드가 있으면 in_conclusion이 True여야 합니다."""
        body_lines = ['일반 내용입니다.'] * 8
        body_lines += ['보안이 결론에서 다시 등장합니다.']
        body_lines += ['보안 관련 마무리를 합니다.']
        content = '# 보안 가이드\n\n' + '\n'.join(body_lines)

        result = self._audit(content)
        security_promise = next(
            (p for p in result['promises'] if '보안' in p['keyword']), None
        )
        if security_promise:
            self.assertTrue(security_promise['in_conclusion'])

    # --- 점수 및 복합 시나리오 ---

    def test_fulfillment_score_range(self):
        """이행 점수는 항상 0-100 범위여야 합니다."""
        # 모든 약속 이행
        content_full = (
            '# API 설계\n\n'
            'API 설계는 중요합니다. API를 잘 만들어야 합니다.\n'
            'API 문서화도 필수입니다. API 버전 관리도 해야 합니다.\n'
        )
        result_full = self._audit(content_full)
        self.assertGreaterEqual(result_full['fulfillment_score'], 0.0)
        self.assertLessEqual(result_full['fulfillment_score'], 100.0)

        # 약속 미이행
        content_miss = (
            '# 쿠버네티스 오케스트레이션\n\n'
            '서버를 관리하는 방법은 여러 가지입니다.\n'
            '자동화 도구를 활용하면 편리합니다.\n'
        )
        result_miss = self._audit(content_miss)
        self.assertGreaterEqual(result_miss['fulfillment_score'], 0.0)
        self.assertLessEqual(result_miss['fulfillment_score'], 100.0)

    def test_multiple_promises(self):
        """여러 소제목에서 각각의 약속이 독립적으로 검증되어야 합니다."""
        content = (
            '# 풀스택 개발 로드맵\n\n'
            '## React 프론트엔드\n'
            'React는 컴포넌트 기반 라이브러리입니다.\n'
            'React를 활용하면 UI를 효율적으로 만들 수 있습니다.\n'
            'React 생태계에는 다양한 도구가 있습니다.\n\n'
            '## Django 백엔드\n'
            'Django는 파이썬 웹 프레임워크입니다.\n'
            'Django를 사용하면 빠르게 개발할 수 있습니다.\n'
            'Django ORM으로 데이터를 관리합니다.\n\n'
            '## GraphQL 연동\n'
            '데이터 통신 방식에 대해 알아봅니다.\n'
        )
        result = self._audit(content)
        # 최소 2개 이상의 약속이 있어야 함
        self.assertGreaterEqual(len(result['promises']), 2)

        # React/Django는 fulfilled, GraphQL은 missing 또는 weak
        statuses = {p['keyword']: p['status'] for p in result['promises']}
        react = next((v for k, v in statuses.items() if 'React' in k), None)
        django = next((v for k, v in statuses.items() if 'Django' in k), None)
        graphql = next((v for k, v in statuses.items() if 'GraphQL' in k), None)

        if react:
            self.assertEqual(react, 'fulfilled')
        if django:
            self.assertEqual(django, 'fulfilled')
        if graphql:
            self.assertIn(graphql, ('weak', 'missing'))

    def test_suggestions(self):
        """missing/weak 약속에 대해 적절한 개선 제안이 생성되어야 합니다."""
        content = (
            '# 마이크로서비스와 모놀리스 비교\n\n'
            '소프트웨어 아키텍처는 중요한 결정입니다.\n'
            '적절한 설계가 프로젝트 성공의 열쇠입니다.\n'
            '팀 규모에 따라 선택이 달라질 수 있습니다.\n'
        )
        result = self._audit(content)
        # missing 키워드가 있으므로 제안이 생성되어야 함
        self.assertTrue(len(result['suggestions']) > 0)
        # 제안 중 하나에 '언급되지 않았습니다' 포함
        has_missing_suggestion = any('언급되지 않았습니다' in s for s in result['suggestions'])
        # 마이크로서비스/모놀리스가 missing이면 해당 제안 있어야 함
        missing_promises = [p for p in result['promises'] if p['status'] == 'missing']
        if missing_promises:
            self.assertTrue(has_missing_suggestion)

    def test_english_keywords(self):
        """영어 키워드도 올바르게 추출 및 검증되어야 합니다."""
        content = (
            '# Python FastAPI Tutorial\n\n'
            'Python is a versatile programming language.\n'
            'FastAPI is built on Python and provides fast development.\n'
            'This Tutorial covers the basics of FastAPI with Python.\n'
        )
        result = self._audit(content)
        keywords = [p['keyword'] for p in result['promises']]
        self.assertTrue(
            any('Python' in kw for kw in keywords) or
            any('FastAPI' in kw for kw in keywords)
        )

    def test_perfect_score(self):
        """모든 약속이 이행되면 100점이어야 합니다."""
        content = (
            '# 테스트 자동화\n\n'
            '테스트 자동화는 소프트웨어 품질의 핵심입니다.\n'
            '테스트를 자동으로 실행하면 효율이 높아집니다.\n'
            '자동화 도구를 활용한 테스트 전략을 살펴봅니다.\n'
            '테스트 자동화 프레임워크 선택이 중요합니다.\n'
            '결론적으로 테스트 자동화는 필수 역량입니다.\n'
        )
        result = self._audit(content)
        # 모든 약속이 fulfilled이면 100점
        all_fulfilled = all(p['status'] == 'fulfilled' for p in result['promises'])
        if all_fulfilled:
            self.assertEqual(result['fulfillment_score'], 100.0)


if __name__ == '__main__':
    unittest.main()
