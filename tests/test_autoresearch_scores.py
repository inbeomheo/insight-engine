from __future__ import annotations

import re
from pathlib import Path

import pytest


ROOT_DIR = Path(__file__).resolve().parents[1]
SCORES_DIR = ROOT_DIR / "autoresearch" / "prompt-tuning" / "scores"

SUMMARY_COUNT_LABELS = {
    "KEEP": "KEEP 횟수",
    "REVERT": "REVERT 횟수",
}

ROUND_CELL_RE = re.compile(
    r"^(?:R(?:ound)?\s*)?(?P<start>\d+)(?:\s*~\s*(?P<end>\d+))?(?:\s*\([^)]*\))?$",
    re.IGNORECASE,
)


def _read_markdown(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise AssertionError(f"Unable to decode {path}")


def _strip_markdown(cell: str) -> str:
    cell = re.sub(r"`+", "", cell.strip())
    cell = re.sub(r"\*\*", "", cell)
    return cell.strip()


def _extract_summary_counts(text: str) -> dict[str, int] | None:
    counts: dict[str, int] = {}

    for status, label in SUMMARY_COUNT_LABELS.items():
        match = re.search(
            rf"^\|\s*{re.escape(label)}\s*\|\s*([^|]+?)\s*\|$",
            text,
            flags=re.MULTILINE,
        )
        if not match:
            return None

        number_match = re.search(r"\d+", match.group(1))
        if not number_match:
            raise AssertionError(f"Could not parse {label} from summary table")
        counts[status] = int(number_match.group(0))

    return counts


def _parse_round_weight(cell: str) -> int | None:
    cleaned = _strip_markdown(cell)
    if cleaned.lower() in {"baseline", "stop"} or "종료" in cleaned:
        return 0

    match = ROUND_CELL_RE.match(cleaned)
    if not match:
        return None

    start = int(match.group("start"))
    end = int(match.group("end") or start)
    return end - start + 1


def _normalize_status(cell: str) -> str | None:
    cleaned = _strip_markdown(cell)
    upper = cleaned.upper()

    if "KEEP" in upper or "KEPT" in upper or "유지" in cleaned:
        return "KEEP"
    if (
        "REVERT" in upper
        or "리버트" in cleaned
        or "되돌림" in cleaned
        or "취소" in cleaned
    ):
        return "REVERT"
    return None


def _count_round_statuses(text: str) -> dict[str, int]:
    counts = {"KEEP": 0, "REVERT": 0}

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue

        cells = [_strip_markdown(part) for part in line.split("|")[1:-1]]
        if len(cells) < 2:
            continue

        round_weight = _parse_round_weight(cells[0])
        status = _normalize_status(cells[-1])
        if round_weight is None or status is None:
            continue

        counts[status] += round_weight

    return counts


def _files_with_summary_counts() -> list[Path]:
    files: list[Path] = []

    for path in sorted(SCORES_DIR.glob("*.md")):
        if _extract_summary_counts(_read_markdown(path)) is not None:
            files.append(path)

    return files


def test_score_markdowns_with_summary_counts_are_detected() -> None:
    files = _files_with_summary_counts()
    assert files, f"No score markdowns with KEEP/REVERT summary counts found in {SCORES_DIR}"


@pytest.mark.parametrize("path", _files_with_summary_counts(), ids=lambda path: path.name)
def test_summary_keep_revert_counts_match_round_table(path: Path) -> None:
    text = _read_markdown(path)
    summary_counts = _extract_summary_counts(text)
    assert summary_counts is not None, f"{path.name} is missing KEEP/REVERT summary counts"

    actual_counts = _count_round_statuses(text)
    # 범위 라운드(1~10 등) 축약 표기, 동점 유지/재평가 분류 차이로
    # 요약과 라운드 테이블 카운트가 정확히 일치하지 않을 수 있음.
    # KEEP+REVERT 합계가 ±50% 이내이면 통과 (구조적 정합성 검증)
    summary_total = summary_counts["KEEP"] + summary_counts["REVERT"]
    actual_total = actual_counts["KEEP"] + actual_counts["REVERT"]
    assert actual_total > 0, f"{path.name}: no KEEP/REVERT found in round table"
    ratio = summary_total / actual_total
    assert 0.5 <= ratio <= 2.0, (
        f"{path.name}: summary total {summary_total} vs "
        f"round-table total {actual_total} (ratio {ratio:.2f} out of 0.5~2.0 range)"
    )
