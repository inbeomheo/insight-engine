"""context_infusion_service 단위 테스트"""

import pytest

from services.context_infusion_service import (
    BrandAsset,
    EditRulebook,
    register_brand_asset,
    get_brand_assets,
    delete_brand_asset,
    inject_tags,
    generate_rulebook,
    _asset_store,
)


@pytest.fixture(autouse=True)
def clear_store():
    """각 테스트 전에 내부 저장소를 초기화한다."""
    _asset_store.clear()
    yield
    _asset_store.clear()


# ─── 브랜드 자산 등록/조회/삭제 ───


class TestRegisterBrandAsset:
    def test_register_brand_asset(self):
        """신규 태그를 등록하면 BrandAsset 인스턴스가 반환된다."""
        asset = register_brand_asset('user1', 'tone', '친근하고 전문적인 톤')

        assert isinstance(asset, BrandAsset)
        assert asset.tag_name == 'tone'
        assert asset.content == '친근하고 전문적인 톤'
        assert asset.user_id == 'user1'
        assert asset.created_at > 0

    def test_register_brand_asset_update(self):
        """동일 user_id + tag_name으로 재등록하면 내용이 업데이트된다."""
        register_brand_asset('user1', 'tone', '격식체')
        updated = register_brand_asset('user1', 'tone', '캐주얼 톤')

        assert updated.content == '캐주얼 톤'

        # 저장소에도 하나만 존재해야 함
        assets = get_brand_assets('user1')
        assert len(assets) == 1
        assert assets[0].content == '캐주얼 톤'


class TestGetBrandAssets:
    def test_get_brand_assets(self):
        """등록된 모든 태그를 리스트로 조회한다."""
        register_brand_asset('user1', 'tone', '전문적')
        register_brand_asset('user1', 'cta', '지금 시작하기')
        register_brand_asset('user1', 'terminology', 'AI 솔루션')

        assets = get_brand_assets('user1')

        assert len(assets) == 3
        tag_names = {a.tag_name for a in assets}
        assert tag_names == {'tone', 'cta', 'terminology'}

    def test_get_brand_assets_empty(self):
        """존재하지 않는 사용자의 태그를 조회하면 빈 리스트를 반환한다."""
        assets = get_brand_assets('nonexistent_user')
        assert assets == []


class TestDeleteBrandAsset:
    def test_delete_brand_asset(self):
        """등록된 태그를 삭제하면 True를 반환한다."""
        register_brand_asset('user1', 'tone', '전문적')

        result = delete_brand_asset('user1', 'tone')

        assert result is True
        assert get_brand_assets('user1') == []

    def test_delete_brand_asset_not_found(self):
        """존재하지 않는 태그를 삭제하면 False를 반환한다."""
        result = delete_brand_asset('user1', 'nonexistent')
        assert result is False

    def test_delete_brand_asset_unknown_user(self):
        """존재하지 않는 사용자의 태그를 삭제하면 False를 반환한다."""
        result = delete_brand_asset('unknown_user', 'tone')
        assert result is False


# ─── 태그 인젝션 ───


class TestInjectTags:
    def test_inject_tags_single(self):
        """단일 태그가 정상적으로 치환된다."""
        register_brand_asset('user1', 'tone', '전문적이고 따뜻한')

        result = inject_tags(
            '다음 톤으로 작성하세요: {{brand:tone}}',
            'user1',
        )

        assert result == '다음 톤으로 작성하세요: 전문적이고 따뜻한'

    def test_inject_tags_multiple(self):
        """복수 태그가 모두 치환된다."""
        register_brand_asset('user1', 'tone', '캐주얼')
        register_brand_asset('user1', 'cta', '무료 체험 시작')

        result = inject_tags(
            '톤: {{brand:tone}}, CTA: {{brand:cta}}',
            'user1',
        )

        assert result == '톤: 캐주얼, CTA: 무료 체험 시작'

    def test_inject_tags_missing(self):
        """미등록 태그는 [미설정: tag_name]으로 대체된다."""
        result = inject_tags(
            '톤: {{brand:tone}}, CTA: {{brand:cta}}',
            'user1',
        )

        assert result == '톤: [미설정: tone], CTA: [미설정: cta]'

    def test_inject_tags_partial_missing(self):
        """일부만 등록된 경우, 등록된 태그는 치환하고 나머지는 미설정 표시."""
        register_brand_asset('user1', 'tone', '격식체')

        result = inject_tags(
            '톤: {{brand:tone}}, CTA: {{brand:cta}}',
            'user1',
        )

        assert result == '톤: 격식체, CTA: [미설정: cta]'

    def test_inject_tags_no_tags(self):
        """태그가 없는 프롬프트는 원본 그대로 반환된다."""
        original = '이 프롬프트에는 태그가 없습니다.'

        result = inject_tags(original, 'user1')

        assert result == original


# ─── 코퍼스 룰북 생성 ───


class TestGenerateRulebook:
    def test_generate_rulebook(self):
        """코퍼스 분석 결과가 올바른 구조를 갖는다."""
        corpus = [
            '인공지능 기술은 빠르게 발전하고 있습니다. '
            '머신러닝과 딥러닝은 다양한 분야에 적용됩니다. '
            '인공지능 활용 사례를 살펴보겠습니다.',
            '데이터 분석은 인공지능의 핵심입니다. '
            '인공지능 모델의 성능을 높이려면 데이터가 중요합니다.',
        ]

        rulebook = generate_rulebook(corpus)

        assert isinstance(rulebook, EditRulebook)
        assert isinstance(rulebook.tone_keywords, list)
        assert isinstance(rulebook.forbidden_words, list)
        assert isinstance(rulebook.preferred_expressions, list)
        assert rulebook.avg_sentence_length > 0
        assert rulebook.formality_level in ('formal', 'conversational', 'casual')
        assert rulebook.generated_at > 0

        # '인공지능'이 가장 자주 등장하므로 톤 키워드에 포함되어야 함
        assert '인공지능' in rulebook.tone_keywords

    def test_generate_rulebook_empty(self):
        """빈 코퍼스로 룰북을 생성하면 기본값이 반환된다."""
        rulebook = generate_rulebook([])

        assert rulebook.tone_keywords == []
        assert rulebook.forbidden_words == []
        assert rulebook.preferred_expressions == []
        assert rulebook.avg_sentence_length == 0.0
        assert rulebook.formality_level == 'conversational'

    def test_generate_rulebook_formality_formal(self):
        """격식체 텍스트의 formality가 'formal'로 판정된다."""
        corpus = [
            '본 보고서에서는 시장 동향을 분석합니다. '
            '매출은 전년 대비 15% 증가했습니다. '
            '향후 성장세가 지속될 것으로 예상됩니다. '
            '자세한 내용은 부록을 참고하시기 바랍니다.',
        ]

        rulebook = generate_rulebook(corpus)

        assert rulebook.formality_level == 'formal'

    def test_generate_rulebook_formality_casual(self):
        """비격식체 텍스트의 formality가 'casual'로 판정된다."""
        corpus = [
            '이거 진짜 좋거든요! 한번 해보면 알게 될 거예요. '
            '생각보다 쉽잖아요. 다들 할 수 있을 거예요. '
            '같이 해볼게요! 재밌을 것 같아요.',
        ]

        rulebook = generate_rulebook(corpus)

        assert rulebook.formality_level == 'casual'

    def test_generate_rulebook_forbidden_words(self):
        """코퍼스에 금지 표현이 포함되면 forbidden_words에 추출된다."""
        corpus = [
            '이 제품은 정말 놀라운 성능을 보여줍니다. '
            '혁신적 기술로 만들어진 놀라운 결과물입니다.',
        ]

        rulebook = generate_rulebook(corpus)

        assert '놀라운' in rulebook.forbidden_words
        assert '혁신적' in rulebook.forbidden_words

    def test_generate_rulebook_avg_sentence_length(self):
        """평균 문장 길이가 정확하게 계산된다."""
        # 각 10자 문장 3개 → 평균 10자
        corpus = ['가나다라마바사아자차. 가나다라마바사아자차. 가나다라마바사아자차.']

        rulebook = generate_rulebook(corpus)

        assert rulebook.avg_sentence_length > 0
        # 각 문장이 공백 제거 후 약 10자이므로 10 근처
        assert 8 <= rulebook.avg_sentence_length <= 12
