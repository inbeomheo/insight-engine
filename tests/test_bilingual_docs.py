"""사용자 문서의 언어 연결과 주요 설정 누락을 검사한다."""
from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('directory', ['', 'patches'])
def test_language_links_and_local_document_targets(directory):
    folder = ROOT / directory
    for filename, counterpart in [('README.md', 'README.en.md'), ('README.en.md', 'README.md')]:
        text = (folder / filename).read_text()
        assert f']({counterpart})' in text
        for target in re.findall(r'\]\(([^)]+)\)', text):
            if target.startswith(('https://', 'http://', '#')):
                continue
            assert (folder / target.split('#')[0]).exists(), target


def test_readme_environment_names_match_between_languages():
    def variables(filename):
        return set(re.findall(r'\b[A-Z][A-Z0-9]*_[A-Z0-9_]+\b', (ROOT / filename).read_text()))

    assert variables('README.md') == variables('README.en.md')
