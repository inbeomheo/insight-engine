#!/usr/bin/env python3
"""수렴 분석기 — 절대 수정 금지 (Level 0)
Inner Loop 결과에서 수렴 패턴을 분석합니다."""

import csv
import json
import sys
from pathlib import Path
from typing import List


def analyze_convergence(tsv_path: str) -> dict:
    """수렴 패턴을 분석합니다."""
    path = Path(tsv_path)
    if not path.exists():
        return {'status': 'no_data'}

    scores = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            try:
                scores.append(float(row.get('score', 0)))
            except ValueError:
                continue

    if len(scores) < 3:
        return {'status': 'insufficient_data', 'count': len(scores)}

    # 이동 평균 (window=3)
    moving_avg = []
    for i in range(2, len(scores)):
        moving_avg.append(sum(scores[i-2:i+1]) / 3)

    # 수렴 판단: 마지막 5개 이동평균의 변동폭
    if len(moving_avg) >= 5:
        recent = moving_avg[-5:]
        variance = max(recent) - min(recent)
        converged = variance < 2.0  # 2점 미만 변동이면 수렴
    else:
        variance = 0
        converged = False

    # 트렌드: 상승/하락/정체
    if len(scores) >= 5:
        first_half = sum(scores[:len(scores)//2]) / (len(scores)//2)
        second_half = sum(scores[len(scores)//2:]) / (len(scores) - len(scores)//2)
        if second_half - first_half > 2:
            trend = 'improving'
        elif first_half - second_half > 2:
            trend = 'degrading'
        else:
            trend = 'plateau'
    else:
        trend = 'unknown'

    return {
        'status': 'analyzed',
        'total_experiments': len(scores),
        'initial_score': scores[0],
        'final_score': scores[-1],
        'best_score': max(scores),
        'worst_score': min(scores),
        'converged': converged,
        'variance': round(variance, 2),
        'trend': trend
    }


if __name__ == '__main__':
    tsv_path = sys.argv[1] if len(sys.argv) > 1 else 'autoresearch/inner_results.tsv'
    result = analyze_convergence(tsv_path)
    print(json.dumps(result, indent=2, ensure_ascii=False))
