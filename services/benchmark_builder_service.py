"""
벤치마크 빌더 서비스.

모델/서비스 벤치마크를 구성하고 결과를 평가한다.
"""

from dataclasses import dataclass, field
import uuid


@dataclass
class BenchmarkCase:
    """벤치마크 케이스"""
    case_id: str = ""
    name: str = ""
    input_data: str = ""
    expected_output: str = ""
    category: str = "general"


@dataclass
class BenchmarkResult:
    """벤치마크 결과"""
    case_id: str = ""
    actual_output: str = ""
    passed: bool = False
    latency_ms: float = 0.0
    score: float = 0.0


@dataclass
class BenchmarkSuite:
    """벤치마크 스위트"""
    suite_id: str = ""
    cases: list = field(default_factory=list)
    results: list = field(default_factory=list)


def create_suite(name: str, cases_config: list) -> BenchmarkSuite:
    """벤치마크 스위트 생성"""
    cases = []
    for cfg in cases_config:
        case = BenchmarkCase(
            case_id=cfg.get("case_id", str(uuid.uuid4())),
            name=cfg.get("name", ""),
            input_data=cfg.get("input_data", ""),
            expected_output=cfg.get("expected_output", ""),
            category=cfg.get("category", "general"),
        )
        cases.append(case)

    return BenchmarkSuite(
        suite_id=str(uuid.uuid4()),
        cases=cases,
        results=[],
    )


def evaluate_result(
    case: BenchmarkCase,
    actual_output: str,
    latency: float
) -> BenchmarkResult:
    """
    결과 평가.

    exact match이면 score=1.0, 부분 일치이면 단어 겹침 비율로 점수 산정.
    """
    # 정확 일치
    if actual_output.strip() == case.expected_output.strip():
        passed = True
        score = 1.0
    else:
        # 부분 일치: 단어 겹침 비율
        expected_words = set(case.expected_output.lower().split())
        actual_words = set(actual_output.lower().split())

        if expected_words:
            overlap = len(expected_words & actual_words)
            score = round(overlap / len(expected_words), 4)
        else:
            score = 0.0

        passed = score >= 0.8  # 80% 이상 일치 시 통과

    return BenchmarkResult(
        case_id=case.case_id,
        actual_output=actual_output,
        passed=passed,
        latency_ms=round(latency, 2),
        score=score,
    )


def generate_report(suite: BenchmarkSuite) -> dict:
    """
    벤치마크 보고서 생성.

    합격률, 평균 지연, 카테고리별 점수를 포함한다.
    """
    total = len(suite.results)
    if total == 0:
        return {
            "suite_id": suite.suite_id,
            "total_cases": len(suite.cases),
            "evaluated": 0,
            "pass_rate": 0.0,
            "avg_latency_ms": 0.0,
            "avg_score": 0.0,
            "category_scores": {},
        }

    passed = sum(1 for r in suite.results if r.passed)
    avg_latency = sum(r.latency_ms for r in suite.results) / total
    avg_score = sum(r.score for r in suite.results) / total

    # 카테고리별 점수
    category_scores = {}
    case_map = {c.case_id: c for c in suite.cases}

    for result in suite.results:
        case = case_map.get(result.case_id)
        category = case.category if case else "unknown"

        if category not in category_scores:
            category_scores[category] = {"total": 0, "passed": 0, "score_sum": 0.0}

        category_scores[category]["total"] += 1
        if result.passed:
            category_scores[category]["passed"] += 1
        category_scores[category]["score_sum"] += result.score

    for cat, data in category_scores.items():
        data["avg_score"] = round(data["score_sum"] / data["total"], 4) if data["total"] > 0 else 0.0
        data["pass_rate"] = round(data["passed"] / data["total"], 4) if data["total"] > 0 else 0.0
        del data["score_sum"]

    return {
        "suite_id": suite.suite_id,
        "total_cases": len(suite.cases),
        "evaluated": total,
        "pass_rate": round(passed / total, 4),
        "avg_latency_ms": round(avg_latency, 2),
        "avg_score": round(avg_score, 4),
        "category_scores": category_scores,
    }


def compare_runs(suite_a: BenchmarkSuite, suite_b: BenchmarkSuite) -> dict:
    """두 실행 비교"""
    report_a = generate_report(suite_a)
    report_b = generate_report(suite_b)

    pass_rate_diff = report_b["pass_rate"] - report_a["pass_rate"]
    latency_diff = report_b["avg_latency_ms"] - report_a["avg_latency_ms"]
    score_diff = report_b["avg_score"] - report_a["avg_score"]

    return {
        "suite_a_id": suite_a.suite_id,
        "suite_b_id": suite_b.suite_id,
        "pass_rate_diff": round(pass_rate_diff, 4),
        "latency_diff_ms": round(latency_diff, 2),
        "score_diff": round(score_diff, 4),
        "improved": score_diff > 0,
        "summary": (
            f"점수 {'향상' if score_diff > 0 else '하락'}: "
            f"{report_a['avg_score']:.4f} → {report_b['avg_score']:.4f} "
            f"({'+' if score_diff > 0 else ''}{score_diff:.4f})"
        ),
    }
