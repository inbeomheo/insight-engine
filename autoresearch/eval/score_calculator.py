#!/usr/bin/env python3
"""Inner Loop 복합 점수를 산출합니다. (Frozen — 수정 금지)
가중치는 outer/metric_weights.json에서 읽음 (Outer Loop가 조정 가능)."""

import json
import os
import sys
from pathlib import Path


def load_weights() -> dict:
    """outer/metric_weights.json에서 가중치를 로드합니다."""
    weights_path = Path(__file__).parent.parent / 'outer' / 'metric_weights.json'
    if weights_path.exists():
        with open(weights_path, encoding='utf-8') as f:
            data = json.load(f)
            return {k: v for k, v in data.items() if not k.startswith('_')}
    return {'error': 0.35, 'dom': 0.25, 'form': 0.25, 'visual': 0.15}


def calculate_score(metrics: dict) -> float:
    """메트릭에서 복합 점수를 산출합니다 (0-100)."""
    weights = load_weights()

    error_score = metrics.get('error_score', 100)
    dom_score = metrics.get('dom_score', 50)
    form_score = metrics.get('form_score', 50)
    visual_score = metrics.get('visual_score', 50)

    score = (
        error_score * weights.get('error', 0.35) +
        dom_score * weights.get('dom', 0.25) +
        form_score * weights.get('form', 0.25) +
        visual_score * weights.get('visual', 0.15)
    )

    return round(score, 2)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            metrics = json.load(f)
    else:
        metrics = {'error_score': 100, 'dom_score': 80, 'form_score': 90, 'visual_score': 70}

    score = calculate_score(metrics)
    print(f"복합 점수: {score}/100")
    print(json.dumps({'score': score, 'weights': load_weights()}, indent=2))
