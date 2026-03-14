"""
내부 링크 기회 탐지 서비스 테스트

find_link_opportunities() 함수의 키워드 매칭, 관련성 점수,
앵커 텍스트 추천, 고립 콘텐츠 감지 등을 검증합니다.
"""
import unittest

from services.seo.internal_link_service import find_link_opportunities


class TestInternalLinkService(unittest.TestCase):
    """find_link_opportunities 함수 테스트"""

    # ============================================================
    # 1. 빈 리스트
    # ============================================================
    def test_empty_contents(self):
        """빈 리스트를 입력하면 기회 없음 결과를 반환해야 한다."""
        result = find_link_opportunities([])

        self.assertEqual(result['opportunities'], [])
        self.assertEqual(result['summary']['total_opportunities'], 0)
        self.assertEqual(result['summary']['high_relevance'], 0)
        self.assertEqual(result['summary']['linked_pairs'], 0)
        self.assertIsInstance(result['orphan_contents'], list)
        self.assertIsInstance(result['suggestions'], list)
        self.assertTrue(len(result['suggestions']) > 0)

    # ============================================================
    # 2. 단일 콘텐츠
    # ============================================================
    def test_single_content(self):
        """콘텐츠가 1개뿐이면 링크 기회가 없어야 한다."""
        contents = [
            {
                'id': 'c1',
                'title': '파이썬 기초 문법',
                'content': '파이썬은 간결한 문법을 가진 프로그래밍 언어입니다. '
                           '파이썬 문법은 배우기 쉽습니다.',
            }
        ]
        result = find_link_opportunities(contents)

        self.assertEqual(result['summary']['total_opportunities'], 0)
        self.assertEqual(len(result['opportunities']), 0)
        # 단일 콘텐츠는 고립으로 간주
        self.assertIn('c1', result['orphan_contents'])

    # ============================================================
    # 3. 기본 기회 탐지 (2개 콘텐츠 간 키워드 겹침)
    # ============================================================
    def test_basic_opportunity(self):
        """2개 콘텐츠가 공통 키워드를 공유하면 기회를 찾아야 한다."""
        contents = [
            {
                'id': 'c1',
                'title': '머신러닝 입문 가이드',
                'content': '머신러닝은 데이터를 학습하는 기술입니다. '
                           '머신러닝 알고리즘은 다양합니다. '
                           '데이터 전처리가 중요합니다. 데이터 분석 기법을 알아봅시다.',
            },
            {
                'id': 'c2',
                'title': '데이터 분석 실전',
                'content': '데이터 분석은 비즈니스 의사결정에 중요합니다. '
                           '데이터 시각화 도구를 활용합시다. '
                           '머신러닝 모델을 적용할 수 있습니다. 머신러닝 학습 과정을 소개합니다.',
            },
        ]
        result = find_link_opportunities(contents)

        self.assertGreater(result['summary']['total_opportunities'], 0)
        self.assertGreater(len(result['opportunities']), 0)

        # 기회에 필수 필드가 있는지 확인
        opp = result['opportunities'][0]
        self.assertIn('source_text', opp)
        self.assertIn('target_id', opp)
        self.assertIn('target_title', opp)
        self.assertIn('relevance_score', opp)
        self.assertIn('anchor_suggestion', opp)
        self.assertIn('context', opp)

    # ============================================================
    # 4. current_content 기준 기회 탐지
    # ============================================================
    def test_with_current_content(self):
        """current_content를 지정하면 해당 콘텐츠에서 다른 콘텐츠로의 기회만 찾아야 한다."""
        contents = [
            {
                'id': 'c1',
                'title': '리액트 컴포넌트 설계',
                'content': '리액트 컴포넌트는 재사용 가능합니다. '
                           '리액트 훅을 활용합시다. 컴포넌트 설계 패턴이 중요합니다. '
                           '컴포넌트 테스트도 빼놓을 수 없습니다.',
            },
            {
                'id': 'c2',
                'title': '타입스크립트 기초',
                'content': '타입스크립트는 정적 타입 언어입니다. '
                           '타입스크립트 인터페이스를 정의합시다. '
                           '제네릭 타입을 활용합시다. 타입스크립트 컴파일러 설정을 알아봅시다.',
            },
        ]
        current = (
            '프론트엔드 개발에서 리액트 컴포넌트를 잘 설계하는 것이 중요합니다. '
            '리액트 훅과 타입스크립트를 함께 사용하면 생산성이 올라갑니다. '
            '타입스크립트 타입 정의는 버그를 줄여줍니다. '
            '컴포넌트 재사용성을 높이는 패턴을 소개합니다.'
        )

        result = find_link_opportunities(contents, current_content=current)

        self.assertGreater(result['summary']['total_opportunities'], 0)
        # 모든 기회는 contents 내 ID를 target으로 가져야 함
        target_ids = {o['target_id'] for o in result['opportunities']}
        self.assertTrue(target_ids.issubset({'c1', 'c2'}))

    # ============================================================
    # 5. 관련성 점수 범위
    # ============================================================
    def test_relevance_scoring(self):
        """관련성 점수는 0-100 범위여야 한다."""
        contents = [
            {
                'id': 'c1',
                'title': '딥러닝 신경망 구조',
                'content': '딥러닝은 인공 신경망을 사용합니다. '
                           '딥러닝 모델은 다양한 구조를 가집니다. '
                           '신경망 레이어를 쌓아 성능을 높입니다. 신경망 학습은 복잡합니다.',
            },
            {
                'id': 'c2',
                'title': '자연어처리 딥러닝 활용',
                'content': '자연어처리에 딥러닝을 적용합니다. '
                           '딥러닝 기반 번역 모델이 발전하고 있습니다. '
                           '신경망 아키텍처가 핵심입니다. 신경망 훈련에 GPU가 필요합니다.',
            },
        ]
        result = find_link_opportunities(contents)

        for opp in result['opportunities']:
            self.assertGreaterEqual(opp['relevance_score'], 0)
            self.assertLessEqual(opp['relevance_score'], 100)

    # ============================================================
    # 6. 앵커 텍스트 추천
    # ============================================================
    def test_anchor_suggestion(self):
        """앵커 텍스트 추천이 비어 있지 않고 적절한 길이여야 한다."""
        contents = [
            {
                'id': 'c1',
                'title': '쿠버네티스 클러스터 관리',
                'content': '쿠버네티스 클러스터를 관리하는 방법을 알아봅시다. '
                           '쿠버네티스 파드 배포 전략을 설명합니다. '
                           '클러스터 스케일링이 중요합니다. 클러스터 모니터링도 필요합니다.',
            },
            {
                'id': 'c2',
                'title': '도커 컨테이너 입문',
                'content': '도커 컨테이너는 경량 가상화 기술입니다. '
                           '쿠버네티스와 도커를 함께 사용합니다. '
                           '쿠버네티스 오케스트레이션이 핵심입니다. '
                           '컨테이너 이미지를 빌드합시다.',
            },
        ]
        result = find_link_opportunities(contents)

        for opp in result['opportunities']:
            anchor = opp['anchor_suggestion']
            self.assertIsInstance(anchor, str)
            self.assertGreater(len(anchor), 0, "앵커 텍스트가 비어 있음")

    # ============================================================
    # 7. 제목 키워드 매칭 시 관련성 상승
    # ============================================================
    def test_title_keyword_boost(self):
        """타겟 제목에 포함된 키워드가 매칭되면 관련성이 더 높아야 한다."""
        # 제목에 '블록체인'이 포함된 콘텐츠
        contents_title_match = [
            {
                'id': 'title_match',
                'title': '블록체인 기술 이해',
                'content': '블록체인은 분산 원장 기술입니다. 블록체인 네트워크를 구축합시다.',
            },
            {
                'id': 'source',
                'title': '핀테크 트렌드',
                'content': '핀테크에서 블록체인 기술이 주목받고 있습니다. '
                           '블록체인 기반 결제 시스템이 발전합니다. '
                           '암호화폐 거래소가 늘어나고 있습니다. 암호화폐 규제도 논의됩니다.',
            },
        ]
        result_title = find_link_opportunities(contents_title_match)

        # 제목에 '분석'이 없는 콘텐츠
        contents_no_title = [
            {
                'id': 'no_title_match',
                'title': '최신 기술 동향',  # 제목에 블록체인 없음
                'content': '블록체인은 분산 원장 기술입니다. 블록체인 네트워크를 구축합시다.',
            },
            {
                'id': 'source2',
                'title': '핀테크 트렌드',
                'content': '핀테크에서 블록체인 기술이 주목받고 있습니다. '
                           '블록체인 기반 결제 시스템이 발전합니다. '
                           '암호화폐 거래소가 늘어나고 있습니다. 암호화폐 규제도 논의됩니다.',
            },
        ]
        result_no_title = find_link_opportunities(contents_no_title)

        # 둘 다 기회가 있을 때 비교
        if result_title['opportunities'] and result_no_title['opportunities']:
            # 제목에 포함된 키워드 매칭 시 점수가 더 높거나 같아야 함
            title_score = max(
                o['relevance_score'] for o in result_title['opportunities']
            )
            no_title_score = max(
                o['relevance_score'] for o in result_no_title['opportunities']
            )
            self.assertGreaterEqual(title_score, no_title_score)

    # ============================================================
    # 8. 고립 콘텐츠 감지
    # ============================================================
    def test_orphan_detection(self):
        """다른 콘텐츠와 키워드 겹침이 없는 콘텐츠는 고립으로 감지해야 한다."""
        contents = [
            {
                'id': 'c1',
                'title': '파이썬 웹 프레임워크',
                'content': '파이썬 장고 프레임워크를 소개합니다. '
                           '파이썬 플라스크도 인기 있습니다. '
                           '프레임워크 선택 기준을 알아봅시다. 프레임워크 비교를 해봅시다.',
            },
            {
                'id': 'c2',
                'title': '파이썬 데이터 과학',
                'content': '파이썬으로 데이터 과학을 시작합니다. '
                           '판다스 라이브러리를 활용합시다. '
                           '파이썬 시각화 도구를 알아봅시다. 파이썬 넘파이도 중요합니다.',
            },
            {
                'id': 'orphan',
                'title': '요리 레시피 모음',
                'content': '맛있는 파스타를 만들어 봅시다. '
                           '토마토 소스 레시피를 공유합니다. '
                           '이탈리안 요리의 매력을 느껴보세요. 요리 팁을 알려드립니다.',
            },
        ]
        result = find_link_opportunities(contents)

        self.assertIn('orphan', result['orphan_contents'])

    # ============================================================
    # 9. 요약 카운트
    # ============================================================
    def test_summary_counts(self):
        """summary 필드에 올바른 카운트가 포함되어야 한다."""
        contents = [
            {
                'id': 'c1',
                'title': '클라우드 컴퓨팅 기초',
                'content': '클라우드 컴퓨팅은 인프라를 가상화합니다. '
                           '클라우드 서비스 종류를 알아봅시다. '
                           '컴퓨팅 자원을 효율적으로 배분합니다. 컴퓨팅 성능을 측정합시다.',
            },
            {
                'id': 'c2',
                'title': '클라우드 보안 전략',
                'content': '클라우드 보안은 필수적입니다. '
                           '클라우드 접근 제어를 설정합시다. '
                           '보안 감사를 실시합니다. 보안 정책을 수립합시다.',
            },
        ]
        result = find_link_opportunities(contents)
        summary = result['summary']

        self.assertIn('total_opportunities', summary)
        self.assertIn('high_relevance', summary)
        self.assertIn('linked_pairs', summary)
        self.assertIsInstance(summary['total_opportunities'], int)
        self.assertIsInstance(summary['high_relevance'], int)
        self.assertIsInstance(summary['linked_pairs'], int)
        self.assertEqual(summary['total_opportunities'], len(result['opportunities']))
        self.assertGreaterEqual(summary['high_relevance'], 0)
        self.assertLessEqual(summary['high_relevance'], summary['total_opportunities'])

    # ============================================================
    # 10. 높은 관련성 기회 필터
    # ============================================================
    def test_high_relevance_filter(self):
        """high_relevance 카운트는 70점 이상 기회만 세야 한다."""
        contents = [
            {
                'id': 'c1',
                'title': '자바스크립트 비동기 프로그래밍',
                'content': '자바스크립트 비동기 처리를 알아봅시다. '
                           '자바스크립트 프로미스를 활용합니다. '
                           '비동기 패턴을 정리합니다. 비동기 에러 처리도 중요합니다.',
            },
            {
                'id': 'c2',
                'title': '노드 비동기 이벤트루프',
                'content': '노드 이벤트루프는 비동기의 핵심입니다. '
                           '비동기 콜백을 관리합시다. '
                           '자바스크립트 런타임을 이해합시다. 자바스크립트 엔진을 분석합니다.',
            },
        ]
        result = find_link_opportunities(contents)

        high_count = sum(
            1 for o in result['opportunities'] if o['relevance_score'] >= 70
        )
        self.assertEqual(result['summary']['high_relevance'], high_count)

    # ============================================================
    # 11. 문맥 포함
    # ============================================================
    def test_context_included(self):
        """기회 항목에 source_text 주변 문맥이 포함되어야 한다."""
        contents = [
            {
                'id': 'c1',
                'title': '도커 컨테이너화',
                'content': '도커를 사용하면 애플리케이션을 컨테이너화할 수 있습니다. '
                           '도커 이미지를 빌드합시다. '
                           '컨테이너 오케스트레이션을 알아봅시다. 컨테이너 런타임을 설정합시다.',
            },
            {
                'id': 'c2',
                'title': '마이크로서비스 아키텍처',
                'content': '마이크로서비스는 도커 컨테이너로 배포합니다. '
                           '도커 컴포즈를 활용합시다. '
                           '서비스 디스커버리를 구현합니다. 서비스 메시를 설정합시다.',
            },
        ]
        result = find_link_opportunities(contents)

        for opp in result['opportunities']:
            context = opp['context']
            self.assertIsInstance(context, str)
            self.assertGreater(len(context), 0, "문맥이 비어 있음")
            # 문맥에 source_text가 대괄호로 표시되어야 함
            self.assertIn('[', context)
            self.assertIn(']', context)

    # ============================================================
    # 12. 3개 이상 콘텐츠
    # ============================================================
    def test_multiple_contents(self):
        """3개 이상 콘텐츠에서도 올바르게 기회를 탐지해야 한다."""
        contents = [
            {
                'id': 'c1',
                'title': '검색엔진 최적화 전략',
                'content': '검색엔진 최적화는 검색 순위를 올립니다. '
                           '검색엔진 키워드 연구가 중요합니다. '
                           '메타태그 최적화를 합시다. 메타태그 작성 팁을 공유합니다. '
                           '마케팅 관점에서 검색엔진을 이해합시다. 마케팅 효과를 높입시다.',
            },
            {
                'id': 'c2',
                'title': '콘텐츠 마케팅 가이드',
                'content': '콘텐츠 마케팅으로 트래픽을 늘립시다. '
                           '검색엔진과 콘텐츠 마케팅은 연관됩니다. '
                           '마케팅 전략을 수립합시다. 마케팅 성과를 측정합니다. '
                           '트래픽 분석이 필수입니다. 검색엔진 알고리즘을 파악합시다. '
                           '트래픽 증대 방안을 모색합니다.',
            },
            {
                'id': 'c3',
                'title': '구글 애널리틱스 트래픽 분석',
                'content': '구글 애널리틱스로 트래픽을 분석합니다. '
                           '검색엔진 성과를 측정합시다. 검색엔진 유입을 추적합니다. '
                           '트래픽 소스를 파악합니다. 트래픽 증가 추세를 확인합시다. '
                           '마케팅 캠페인 효과를 분석합니다. 마케팅 데이터를 활용합시다.',
            },
        ]
        result = find_link_opportunities(contents)

        self.assertGreater(result['summary']['total_opportunities'], 0)
        # 여러 콘텐츠 쌍에서 기회를 찾아야 함
        target_ids = {o['target_id'] for o in result['opportunities']}
        self.assertGreater(len(target_ids), 0)
        # orphan이 없어야 함 (검색엔진, 마케팅, 트래픽이 공통 키워드)
        self.assertEqual(len(result['orphan_contents']), 0)

    # ============================================================
    # 13. 제안 목록
    # ============================================================
    def test_suggestions(self):
        """suggestions 리스트가 항상 존재하고 문자열 리스트여야 한다."""
        # 기회가 없는 경우
        result_empty = find_link_opportunities([])
        self.assertIsInstance(result_empty['suggestions'], list)
        self.assertTrue(all(isinstance(s, str) for s in result_empty['suggestions']))

        # 기회가 있는 경우
        contents = [
            {
                'id': 'c1',
                'title': '인공지능 윤리학',
                'content': '인공지능 윤리 문제를 논의합니다. '
                           '인공지능 편향성을 줄여야 합니다. '
                           '윤리적 가이드라인을 수립합시다. 윤리 교육도 필요합니다.',
            },
            {
                'id': 'c2',
                'title': '인공지능 규제 동향',
                'content': '인공지능 규제가 전 세계적으로 논의됩니다. '
                           '인공지능 법안을 분석합니다. '
                           '윤리 기준을 준수해야 합니다. 윤리 위원회를 구성합시다.',
            },
        ]
        result = find_link_opportunities(contents)
        self.assertIsInstance(result['suggestions'], list)
        self.assertTrue(all(isinstance(s, str) for s in result['suggestions']))


if __name__ == '__main__':
    unittest.main()
