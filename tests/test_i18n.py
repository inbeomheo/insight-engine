"""
i18n 번역 파일 통합 테스트

검증 항목:
- 모든 JSON 파일이 유효한 JSON인지 확인
- ko.json의 모든 키가 en.json과 ja.json에도 존재하는지 확인
- 누락된 번역 없음 확인
"""

import json
import os
import unittest
from pathlib import Path


I18N_DIR = Path(__file__).parent.parent / "frontend" / "lib" / "i18n"
LOCALES = ["ko", "en", "ja"]


def load_json(locale: str) -> dict:
    """번역 파일을 로드합니다."""
    path = I18N_DIR / f"{locale}.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def flatten_keys(obj: dict, prefix: str = "") -> list[str]:
    """중첩 딕셔너리의 모든 키를 dot-notation으로 평탄화합니다."""
    keys = []
    for k, v in obj.items():
        full_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            keys.extend(flatten_keys(v, full_key))
        else:
            keys.append(full_key)
    return keys


class TestI18nFiles(unittest.TestCase):
    """i18n 번역 파일 유효성 테스트"""

    def test_all_locale_files_exist(self):
        """모든 로케일 파일이 존재하는지 확인합니다."""
        for locale in LOCALES:
            path = I18N_DIR / f"{locale}.json"
            self.assertTrue(
                path.exists(),
                f"번역 파일이 없습니다: {path}"
            )

    def test_all_locale_files_are_valid_json(self):
        """모든 번역 파일이 유효한 JSON인지 확인합니다."""
        for locale in LOCALES:
            with self.subTest(locale=locale):
                try:
                    data = load_json(locale)
                    self.assertIsInstance(data, dict, f"{locale}.json은 JSON 객체여야 합니다")
                except json.JSONDecodeError as e:
                    self.fail(f"{locale}.json은 유효하지 않은 JSON입니다: {e}")

    def test_ko_is_base_locale(self):
        """ko.json이 기본 로케일로서 최소한의 키를 포함하는지 확인합니다."""
        ko = load_json("ko")
        required_sections = ["common", "sidebar", "styles", "result", "settings", "errors"]
        for section in required_sections:
            self.assertIn(section, ko, f"ko.json에 '{section}' 섹션이 없습니다")

    def test_en_has_all_ko_keys(self):
        """en.json이 ko.json의 모든 키를 포함하는지 확인합니다."""
        ko_keys = set(flatten_keys(load_json("ko")))
        en_keys = set(flatten_keys(load_json("en")))

        missing = ko_keys - en_keys
        self.assertEqual(
            len(missing), 0,
            f"en.json에 누락된 키: {sorted(missing)}"
        )

    def test_ja_has_all_ko_keys(self):
        """ja.json이 ko.json의 모든 키를 포함하는지 확인합니다."""
        ko_keys = set(flatten_keys(load_json("ko")))
        ja_keys = set(flatten_keys(load_json("ja")))

        missing = ko_keys - ja_keys
        self.assertEqual(
            len(missing), 0,
            f"ja.json에 누락된 키: {sorted(missing)}"
        )

    def test_no_empty_values(self):
        """모든 번역 값이 비어 있지 않은지 확인합니다."""
        for locale in LOCALES:
            with self.subTest(locale=locale):
                data = load_json(locale)
                keys = flatten_keys(data)
                for key in keys:
                    # 중첩 값 접근
                    parts = key.split(".")
                    value = data
                    for part in parts:
                        value = value[part]
                    self.assertIsInstance(value, str, f"{locale}.{key}는 문자열이어야 합니다")
                    self.assertGreater(
                        len(value.strip()), 0,
                        f"{locale}.json의 '{key}' 값이 비어 있습니다"
                    )

    def test_style_keys_match_known_styles(self):
        """styles 섹션에 알려진 스타일 ID가 포함되어 있는지 확인합니다."""
        known_styles = [
            "blog_seo", "summary", "tutorial", "qna", "app_ideas",
            "yozm_it", "brunch_essay", "naver_popular", "sns_post",
            "newsletter", "show_notes", "shorts_script", "geo_seo",
            "comment_summary"
        ]
        for locale in LOCALES:
            with self.subTest(locale=locale):
                data = load_json(locale)
                styles = data.get("styles", {})
                for style_id in known_styles:
                    self.assertIn(
                        style_id, styles,
                        f"{locale}.json styles에 '{style_id}'가 없습니다"
                    )

    def test_language_section_has_all_locale_labels(self):
        """language 섹션에 모든 로케일 레이블이 있는지 확인합니다."""
        for locale in LOCALES:
            with self.subTest(locale=locale):
                data = load_json(locale)
                lang_section = data.get("language", {})
                for loc in LOCALES:
                    self.assertIn(
                        loc, lang_section,
                        f"{locale}.json의 language 섹션에 '{loc}' 레이블이 없습니다"
                    )

    def test_all_locales_have_same_key_count(self):
        """모든 로케일이 동일한 수의 키를 가지고 있는지 확인합니다."""
        key_counts = {}
        for locale in LOCALES:
            keys = flatten_keys(load_json(locale))
            key_counts[locale] = len(keys)

        ko_count = key_counts["ko"]
        for locale, count in key_counts.items():
            self.assertEqual(
                count, ko_count,
                f"{locale}.json의 키 수({count})가 ko.json({ko_count})과 다릅니다"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
