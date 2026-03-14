"""Audience Persona Builder 서비스 테스트.

규칙 기반 타겟 독자 페르소나 추론 로직을 검증한다.
"""

import unittest

from services.content.audience_persona_service import build_persona


class TestAudiencePersonaService(unittest.TestCase):
    """build_persona() 함수의 동작을 검증한다."""

    # ------------------------------------------------------------------
    # 1. 빈 / None 입력
    # ------------------------------------------------------------------

    def test_empty_content(self):
        """빈 문자열 입력 시 기본값을 반환한다."""
        result = build_persona("")
        self.assertEqual(result["persona"]["expertise_level"], "beginner")
        self.assertEqual(result["persona"]["interests"], [])
        self.assertEqual(result["persona"]["reading_style"], "scanner")
        self.assertEqual(result["persona"]["age_group"], "middle")
        self.assertEqual(result["persona"]["professional_field"], "일반 직장인")
        self.assertEqual(result["confidence"], 0.0)

    def test_none_content(self):
        """None 입력 시 예외 없이 기본값을 반환한다."""
        result = build_persona(None)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["confidence"], 0.0)
        self.assertIn("콘텐츠가 비어 있어 기본값 사용", result["indicators"])

    # ------------------------------------------------------------------
    # 2. 전문성 수준
    # ------------------------------------------------------------------

    def test_beginner_content(self):
        """입문자용 콘텐츠에서 beginner를 감지한다."""
        content = """
        프로그래밍이란 무엇인가? 코딩 기초 입문 가이드입니다.
        처음 배우는 분들을 위한 쉬운 설명으로 시작합니다.
        변수란 값을 저장하는 상자와 같습니다.
        함수의 뜻은 반복되는 작업을 하나로 묶는 것입니다.
        """
        result = build_persona(content)
        self.assertEqual(result["persona"]["expertise_level"], "beginner")

    def test_expert_content(self):
        """전문가용 콘텐츠에서 expert를 감지한다."""
        # 전문용어를 설명 없이 밀도 높게 사용
        content = """
        API 게이트웨이에서 REST와 GraphQL 엔드포인트를 Docker 컨테이너로
        배포하고 Kubernetes 클러스터에서 CI/CD 파이프라인을 구성한다.
        DevOps 관점에서 microservices 아키텍처의 SDK 통합과
        agile 스프린트 기반 MVP 출시 전략을 수립한다.
        SaaS 플랫폼의 API 레이트 리미팅과 SDK 버전 관리를 다룬다.
        B2B 고객을 위한 REST API 문서를 자동화한다.
        ML 파이프라인을 통해 AI 모델을 서빙하는 방법을 살펴본다.
        """
        result = build_persona(content)
        self.assertEqual(result["persona"]["expertise_level"], "expert")

    def test_intermediate_content(self):
        """중급 콘텐츠에서 intermediate를 감지한다."""
        content = """
        웹 개발에서 프론트엔드와 백엔드의 역할을 이해하고,
        데이터베이스 설계 원칙을 적용해 보겠습니다.
        프레임워크를 활용한 실전 프로젝트를 진행합니다.
        성능 최적화와 코드 리팩토링 기법도 살펴봅니다.
        """
        result = build_persona(content)
        self.assertEqual(result["persona"]["expertise_level"], "intermediate")

    # ------------------------------------------------------------------
    # 3. 관심사 추출
    # ------------------------------------------------------------------

    def test_interests_extraction(self):
        """2회 이상 등장하는 토픽을 관심사로 추출한다."""
        content = """
        마케팅 전략에서 콘텐츠 마케팅은 핵심이다.
        콘텐츠를 통한 브랜드 인지도 향상이 목표다.
        소셜 미디어 마케팅과 이메일 마케팅을 결합하면
        브랜드 가치를 극대화할 수 있다.
        캠페인 성과를 분석하고 캠페인 최적화를 진행한다.
        """
        result = build_persona(content)
        interests = result["persona"]["interests"]
        self.assertIsInstance(interests, list)
        self.assertGreater(len(interests), 0)
        self.assertLessEqual(len(interests), 5)
        # '마케팅'이 여러 번 등장하므로 관심사에 포함되어야 함
        self.assertIn("마케팅", interests)

    # ------------------------------------------------------------------
    # 4. 독서 스타일
    # ------------------------------------------------------------------

    def test_scanner_reading_style(self):
        """목록과 헤딩이 많으면 scanner로 감지한다."""
        content = """
# 웹 개발 체크리스트

## 프론트엔드
- HTML 구조 설계
- CSS 스타일링 적용
- JavaScript 로직 구현

## 백엔드
- API 설계
- 데이터베이스 모델링
- 인증 시스템

## 배포
- 서버 설정
- CI/CD 파이프라인
- 모니터링 구축
        """
        result = build_persona(content)
        self.assertEqual(result["persona"]["reading_style"], "scanner")

    def test_deep_reader_style(self):
        """긴 서술 문단이 많으면 deep_reader로 감지한다."""
        content = (
            "현대 소프트웨어 아키텍처에서 모놀리식과 마이크로서비스 접근법의 "
            "차이점을 이해하는 것은 매우 중요합니다. 전통적인 모놀리식 아키텍처는 "
            "모든 기능이 하나의 배포 단위로 묶여 있어 개발 초기에는 간단하지만, "
            "규모가 커지면서 유지보수와 확장에 어려움을 겪게 됩니다.\n\n"
            "마이크로서비스 아키텍처는 각 서비스를 독립적으로 개발, 배포, 확장할 수 "
            "있는 구조를 제공합니다. 이를 통해 팀별로 자율적인 개발이 가능해지고, "
            "장애 격리가 용이해집니다. 하지만 분산 시스템의 복잡성, 서비스 간 통신 "
            "오버헤드, 데이터 일관성 유지 등의 새로운 과제가 발생합니다.\n\n"
            "결국 아키텍처 선택은 조직의 규모, 팀 구성, 비즈니스 요구사항에 따라 "
            "달라져야 합니다. 소규모 팀에서는 모놀리식이 효율적이고, 대규모 조직에서는 "
            "마이크로서비스가 장점을 발휘합니다. 중요한 것은 현재 상황에 맞는 실용적인 "
            "선택을 하는 것입니다.\n\n"
            "기술 부채를 최소화하면서도 비즈니스 속도를 유지하는 균형점을 찾는 것이 "
            "아키텍트의 핵심 역량입니다. 이를 위해 점진적 마이그레이션 전략, 스트랭글러 "
            "패턴, 이벤트 드리븐 아키텍처 등의 전환 기법을 활용할 수 있습니다."
        )
        result = build_persona(content)
        self.assertEqual(result["persona"]["reading_style"], "deep_reader")

    # ------------------------------------------------------------------
    # 5. 연령대
    # ------------------------------------------------------------------

    def test_young_age_group(self):
        """비격식체와 이모티콘이 많으면 young으로 감지한다."""
        content = """
        오늘 새로운 앱 출시됐는데 진짜 대박이에요ㅋㅋㅋ
        이거 ㄹㅇ 미쳤다ㅋㅋ 완전 꿀팁!!!
        근데 버그가 좀 있어서ㅠㅠㅠ 아쉽네요
        다들 한번 써보세요~~~
        """
        result = build_persona(content)
        self.assertEqual(result["persona"]["age_group"], "young")

    # ------------------------------------------------------------------
    # 6. 직업군
    # ------------------------------------------------------------------

    def test_professional_field_dev(self):
        """기술/개발 키워드 우세 시 개발자/엔지니어를 반환한다."""
        content = """
        웹 개발 프로젝트에서 서버 사이드 프로그래밍과 데이터 처리가 핵심이다.
        소프트웨어 아키텍처 설계와 코딩 품질 관리를 위해
        개발 팀이 앱 배포 프로세스를 자동화해야 한다.
        """
        result = build_persona(content)
        self.assertEqual(result["persona"]["professional_field"], "개발자/엔지니어")

    def test_professional_field_marketing(self):
        """마케팅 키워드 우세 시 마케터를 반환한다."""
        content = """
        디지털 마케팅에서 브랜드 광고 캠페인을 기획하고
        타겟 고객층에 맞는 콘텐츠 마케팅 전략을 수립한다.
        광고 예산 최적화와 캠페인 성과 분석이 중요하다.
        브랜드 인지도를 높이는 마케팅 채널 전략을 세운다.
        """
        result = build_persona(content)
        self.assertEqual(result["persona"]["professional_field"], "마케터")

    # ------------------------------------------------------------------
    # 7. 신뢰도
    # ------------------------------------------------------------------

    def test_confidence_score(self):
        """신뢰도 점수가 0-100 범위 내에 있다."""
        content = """
        API 설계와 REST 아키텍처에 대한 전문가를 위한 심층 가이드입니다.
        SDK를 활용한 통합 방법과 DevOps 파이프라인 구축,
        Docker 컨테이너 배포, Kubernetes 오케스트레이션,
        microservices 간 통신 패턴을 다룹니다.
        CI/CD 자동화로 개발 효율을 극대화합니다.
        """ * 3  # 500자 이상 확보
        result = build_persona(content)
        self.assertGreaterEqual(result["confidence"], 0.0)
        self.assertLessEqual(result["confidence"], 100.0)
        # 충분한 콘텐츠 + 전문용어 + 명확한 카테고리 → 높은 신뢰도
        self.assertGreater(result["confidence"], 40.0)

    # ------------------------------------------------------------------
    # 8. 콘텐츠 정합성
    # ------------------------------------------------------------------

    def test_content_alignment(self):
        """콘텐츠 정합성 점수가 올바른 구조와 범위를 가진다."""
        content = """
        프로그래밍이란 무엇인가 알아봅시다. 기초부터 차근차근 배워봅시다.
        변수의 뜻과 함수의 기초를 살펴봅니다. 처음 접하는 분들도 쉽게 이해할 수 있습니다.
        """
        result = build_persona(content)
        alignment = result["content_alignment"]

        self.assertIn("complexity_match", alignment)
        self.assertIn("vocabulary_match", alignment)
        self.assertIn("format_match", alignment)

        for key in ("complexity_match", "vocabulary_match", "format_match"):
            self.assertGreaterEqual(alignment[key], 0.0)
            self.assertLessEqual(alignment[key], 100.0)

    # ------------------------------------------------------------------
    # 9. 추론 근거
    # ------------------------------------------------------------------

    def test_indicators_exist(self):
        """추론 근거 목록이 비어 있지 않고 문자열 리스트다."""
        content = """
        마케팅 전략을 수립하고 브랜드 광고 캠페인을 실행한다.
        콘텐츠 마케팅을 통해 타겟 고객에게 도달하는 방법을 알아본다.
        """
        result = build_persona(content)
        indicators = result["indicators"]

        self.assertIsInstance(indicators, list)
        self.assertGreater(len(indicators), 0)
        for indicator in indicators:
            self.assertIsInstance(indicator, str)


if __name__ == "__main__":
    unittest.main()
