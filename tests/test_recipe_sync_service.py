"""요리 동영상 동기화 레시피 서비스 테스트"""
import unittest

from services.recipe_sync_service import (
    SyncedRecipe, Ingredient, RecipeStep,
    sync_recipe, extract_ingredients,
    _extract_title, _extract_servings,
    _find_tools_in_text, _estimate_duration, _split_into_steps,
)


class TestSyncRecipe(unittest.TestCase):
    """sync_recipe 함수 통합 테스트"""

    def test_basic_recipe_sync(self):
        """기본 요리 자막으로 SyncedRecipe가 정상 생성되는지 확인"""
        transcript = (
            "오늘은 김치볶음밥을 만들어 볼게요.\n"
            "재료는 200g 밥, 100g 김치, 2큰술 고추장이 필요합니다.\n"
            "먼저 팬에 기름을 넣고 김치를 볶아주세요.\n"
            "3분 정도 볶은 후 밥을 넣어 잘 섞어줍니다.\n"
            "마지막으로 고추장을 넣고 2분 더 볶아주세요.\n"
        )
        recipe = sync_recipe(transcript)

        self.assertIsInstance(recipe, SyncedRecipe)
        self.assertIn("김치볶음밥", recipe.title)
        self.assertGreater(len(recipe.ingredients), 0)
        self.assertGreater(len(recipe.steps), 0)
        self.assertGreater(recipe.total_time_minutes, 0)

    def test_empty_transcript(self):
        """빈 자막으로도 에러 없이 기본 레시피 반환"""
        recipe = sync_recipe("")

        self.assertIsInstance(recipe, SyncedRecipe)
        self.assertEqual(recipe.title, "레시피")
        self.assertEqual(recipe.ingredients, [])
        self.assertEqual(recipe.steps, [])
        self.assertEqual(recipe.total_time_minutes, 0)

    def test_servings_extraction_in_sync(self):
        """인분 정보가 SyncedRecipe에 포함되는지 확인"""
        transcript = "4인분 기준으로 재료를 준비합니다. 팬에 넣고 볶아주세요."
        recipe = sync_recipe(transcript)

        self.assertEqual(recipe.servings, "4인분")

    def test_total_time_is_sum_of_steps(self):
        """총 시간이 각 단계 시간의 합인지 확인"""
        transcript = (
            "팬에 버터를 넣고 녹여주세요.\n"
            "5분 동안 볶아줍니다.\n"
            "이어서 소스를 넣고 3분 끓여줍니다.\n"
        )
        recipe = sync_recipe(transcript)

        expected = sum(s.duration_minutes for s in recipe.steps)
        self.assertEqual(recipe.total_time_minutes, expected)


class TestExtractIngredients(unittest.TestCase):
    """재료 추출 테스트"""

    def test_extract_gram_ingredients(self):
        """그램 단위 재료 추출"""
        transcript = "재료는 200g 닭가슴살과 150g 양파가 필요합니다."
        ingredients = extract_ingredients(transcript)

        self.assertGreaterEqual(len(ingredients), 2)
        names = [i.name for i in ingredients]
        self.assertTrue(any("닭가슴살" in n for n in names))

    def test_extract_spoon_ingredients(self):
        """큰술/작은술 단위 재료 추출"""
        transcript = "간장 2큰술 넣고 설탕 1작은술 추가합니다."
        ingredients = extract_ingredients(transcript)

        self.assertGreaterEqual(len(ingredients), 2)
        units = [i.unit for i in ingredients]
        self.assertIn("큰술", units)
        self.assertIn("작은술", units)

    def test_extract_count_ingredients(self):
        """개 단위 재료 추출"""
        transcript = "달걀 3개 준비하세요."
        ingredients = extract_ingredients(transcript)

        self.assertGreaterEqual(len(ingredients), 1)
        egg = next((i for i in ingredients if "달걀" in i.name), None)
        self.assertIsNotNone(egg)
        self.assertEqual(egg.amount, "3")
        self.assertEqual(egg.unit, "개")

    def test_extract_cup_ingredients(self):
        """컵 단위 재료 추출"""
        transcript = "물 2컵 넣어주세요."
        ingredients = extract_ingredients(transcript)

        self.assertGreaterEqual(len(ingredients), 1)
        self.assertTrue(any(i.unit == "컵" for i in ingredients))

    def test_no_duplicates(self):
        """동일 재료명 중복 제거"""
        transcript = "소금 1큰술 넣고, 다시 소금 2큰술 추가합니다."
        ingredients = extract_ingredients(transcript)

        salt_count = sum(1 for i in ingredients if "소금" in i.name)
        self.assertEqual(salt_count, 1)

    def test_no_ingredients_in_text(self):
        """재료 패턴 없는 텍스트에서 빈 리스트 반환"""
        transcript = "오늘 날씨가 좋습니다."
        ingredients = extract_ingredients(transcript)

        self.assertEqual(len(ingredients), 0)

    def test_ml_unit(self):
        """밀리리터 단위 추출"""
        transcript = "우유 500ml 준비합니다."
        ingredients = extract_ingredients(transcript)

        self.assertGreaterEqual(len(ingredients), 1)
        self.assertTrue(any(i.unit == "ml" for i in ingredients))


class TestExtractTitle(unittest.TestCase):
    """레시피 제목 추출 테스트"""

    def test_extract_from_pattern(self):
        """'오늘은 X를 만들' 패턴에서 제목 추출"""
        transcript = "오늘은 된장찌개를 만들어 보겠습니다.\n재료부터 준비할게요."
        title = _extract_title(transcript)

        self.assertIn("된장찌개", title)

    def test_extract_short_first_line(self):
        """첫 줄이 짧으면 제목으로 사용"""
        transcript = "불고기 레시피\n고기를 준비합니다."
        title = _extract_title(transcript)

        self.assertEqual(title, "불고기 레시피")

    def test_default_title(self):
        """빈 자막에서 기본 제목 반환"""
        title = _extract_title("")
        self.assertEqual(title, "레시피")


class TestExtractServings(unittest.TestCase):
    """인분 추출 테스트"""

    def test_extract_servings(self):
        """N인분 패턴 추출"""
        self.assertEqual(_extract_servings("4인분 기준입니다."), "4인분")
        self.assertEqual(_extract_servings("2인분 재료"), "2인분")

    def test_default_servings(self):
        """인분 정보 없으면 기본 2인분"""
        self.assertEqual(_extract_servings("재료를 준비합니다."), "2인분")


class TestFindTools(unittest.TestCase):
    """도구 키워드 매칭 테스트"""

    def test_find_pan(self):
        """팬 키워드 매칭"""
        tools = _find_tools_in_text("팬에 기름을 두르세요.")
        self.assertIn("팬", tools)

    def test_find_multiple_tools(self):
        """여러 도구 동시 매칭"""
        tools = _find_tools_in_text("팬에 볶다가 냄비에 옮겨 담습니다.")
        self.assertIn("팬", tools)
        self.assertIn("냄비", tools)

    def test_no_tools(self):
        """도구 키워드 없는 텍스트"""
        tools = _find_tools_in_text("양념을 준비합니다.")
        self.assertEqual(len(tools), 0)


class TestEstimateDuration(unittest.TestCase):
    """소요 시간 추정 테스트"""

    def test_extract_minutes(self):
        """'N분' 패턴에서 시간 추출"""
        self.assertEqual(_estimate_duration("5분 동안 볶아줍니다."), 5)
        self.assertEqual(_estimate_duration("10분간 끓여주세요."), 10)

    def test_default_duration(self):
        """시간 언급 없으면 기본 2분"""
        self.assertEqual(_estimate_duration("잘 섞어줍니다."), 2)


class TestSplitIntoSteps(unittest.TestCase):
    """조리 단계 분리 테스트"""

    def test_split_by_action_keywords(self):
        """동작 키워드로 단계 분리"""
        transcript = (
            "먼저 야채를 자르세요.\n"
            "팬에 기름을 넣고 볶아줍니다.\n"
            "소스를 넣고 잘 섞어주세요.\n"
        )
        steps = _split_into_steps(transcript)

        self.assertGreaterEqual(len(steps), 2)
        self.assertEqual(steps[0].step_number, 1)

    def test_empty_transcript_no_steps(self):
        """빈 자막에서 빈 리스트 반환"""
        steps = _split_into_steps("")
        self.assertEqual(len(steps), 0)

    def test_step_numbers_sequential(self):
        """단계 번호가 순차적인지 확인"""
        transcript = (
            "고기를 자르세요.\n"
            "양념을 넣어주세요.\n"
            "잘 볶아주세요.\n"
        )
        steps = _split_into_steps(transcript)

        for i, step in enumerate(steps):
            self.assertEqual(step.step_number, i + 1)

    def test_tools_extracted_in_step(self):
        """단계에서 도구가 추출되는지 확인"""
        transcript = "팬에 기름을 넣고 볶아주세요.\n"
        steps = _split_into_steps(transcript)

        self.assertGreater(len(steps), 0)
        self.assertIn("팬", steps[0].tools)

    def test_timestamp_extracted_in_step(self):
        """타임스탬프가 있는 단계에서 시점 추출"""
        transcript = "[2:30] 팬에 기름을 넣고 볶아주세요.\n"
        steps = _split_into_steps(transcript)

        self.assertGreater(len(steps), 0)
        self.assertEqual(steps[0].timestamp, "2:30")


if __name__ == '__main__':
    unittest.main()
