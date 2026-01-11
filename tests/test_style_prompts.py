import unittest


class TestStylePrompts(unittest.TestCase):
    def test_style_options_and_prompts_include_new_styles(self):
        import config

        style_keys = [k for k, _ in config.STYLE_OPTIONS]

        self.assertIn('blog', style_keys)
        self.assertIn('news', style_keys)
        self.assertIn('summary', style_keys)

        # New styles
        self.assertIn('seo', style_keys)
        self.assertIn('script', style_keys)

        self.assertIn('seo', config.STYLE_PROMPTS)
        self.assertIn('script', config.STYLE_PROMPTS)


if __name__ == "__main__":
    unittest.main()
