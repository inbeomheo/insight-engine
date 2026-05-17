"""Fail CI/deploys when production-critical environment variables are unsafe."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.production_readiness import production_readiness_errors


def main() -> int:
    errors = production_readiness_errors(dict(os.environ))
    if errors:
        print('production readiness checks failed', file=sys.stderr)
        for error in errors:
            print(f'- {error}', file=sys.stderr)
        return 1

    print('production readiness checks passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
