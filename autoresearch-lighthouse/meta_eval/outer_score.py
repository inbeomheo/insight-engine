#!/usr/bin/env python3
"""
Outer Loop Frozen Metric — 절대 수정 불가.
Inner Loop의 수렴 속도 + 최종 점수를 복합 산출한다.
"""
import csv


def calculate_outer_score(inner_results_path):
    rows = []
    with open(inner_results_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            rows.append(row)

    if not rows:
        return {"outer_score": 0.0, "error": "결과 없음"}

    metric_values = [float(r["metric_value"]) for r in rows if r.get("metric_value")]
    final_inner_score = metric_values[-1] if metric_values else 0.0

    kept = [r for r in rows if r.get("status") == "keep"]
    total = len(rows)
    kept_count = len(kept)

    if metric_values:
        best_value = max(metric_values)
        best_idx = metric_values.index(best_value)
        convergence_speed = 1.0 - (best_idx / max(len(metric_values) - 1, 1))
    else:
        convergence_speed = 0.0

    if len(metric_values) >= 2:
        total_improvement = metric_values[-1] - metric_values[0]
        improvement_per_experiment = total_improvement / len(metric_values)
    else:
        improvement_per_experiment = 0.0

    outer_score = (
        final_inner_score * 0.50
        + convergence_speed * 100 * 0.30
        + max(improvement_per_experiment, 0) * 100 * 0.20
    )

    return {
        "outer_score": round(outer_score, 2),
        "final_inner_score": round(final_inner_score, 2),
        "convergence_speed": round(convergence_speed, 4),
        "improvement_per_experiment": round(improvement_per_experiment, 4),
        "total_experiments": total,
        "kept_experiments": kept_count,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("사용법: python outer_score.py <inner_results.tsv 경로>")
        sys.exit(1)
    result = calculate_outer_score(sys.argv[1])
    for k, v in result.items():
        print(f"{k}: {v}")
