#!/usr/bin/env python3
"""Outer Loop Frozen Metric — 절대 수정 금지 (Level 0)
Inner Loop의 수렴 속도 + 최종 점수로 Outer Score를 산출합니다."""

import csv
import json
import sys
from pathlib import Path
from typing import List, Tuple


def load_inner_results(tsv_path: str) -> List[Tuple[int, float, str]]:
    """inner_results.tsv에서 (실험번호, 점수, 판정)을 로드합니다."""
    results = []
    path = Path(tsv_path)
    if not path.exists():
        return results
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            try:
                results.append((
                    int(row.get('experiment', 0)),
                    float(row.get('score', 0)),
                    row.get('verdict', 'revert')
                ))
            except (ValueError, KeyError):
                continue
    return results


def calculate_outer_score(results: List[Tuple[int, float, str]]) -> dict:
    """Outer Score를 산출합니다."""
    if not results:
        return {'outer_score': 0, 'final_score': 0, 'convergence_speed': 0, 'improvement_per_exp': 0}

    scores = [r[1] for r in results]
    final_score = scores[-1]
    initial_score = scores[0]

    # 수렴 속도: 최고점에 도달한 회차 (빠를수록 좋음)
    best_score = max(scores)
    best_idx = scores.index(best_score)
    convergence_speed = max(0, 100 - best_idx * 3)  # 0회차=100, 33회차=0

    # 실험당 평균 개선폭
    kept = [r for r in results if r[2] == 'keep']
    if kept and len(results) > 1:
        improvement_per_exp = (final_score - initial_score) / len(results) * 10
    else:
        improvement_per_exp = 0
    improvement_per_exp = max(0, min(100, improvement_per_exp))

    outer_score = round(
        final_score * 0.5 +
        convergence_speed * 0.3 +
        improvement_per_exp * 0.2,
        2
    )

    return {
        'outer_score': outer_score,
        'final_score': final_score,
        'best_score': best_score,
        'convergence_speed': convergence_speed,
        'improvement_per_exp': round(improvement_per_exp, 2),
        'total_experiments': len(results),
        'kept_experiments': len(kept),
        'keep_rate': round(len(kept) / len(results) * 100, 1)
    }


if __name__ == '__main__':
    tsv_path = sys.argv[1] if len(sys.argv) > 1 else 'autoresearch/inner_results.tsv'
    results = load_inner_results(tsv_path)
    outer = calculate_outer_score(results)
    print(json.dumps(outer, indent=2, ensure_ascii=False))
