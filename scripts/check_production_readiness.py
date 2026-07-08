"""Fail CI/deploys when production-critical environment variables are unsafe."""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.production_readiness import production_readiness_errors


def _parse_env_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith('#') or '=' not in stripped:
        return None

    key, value = stripped.split('=', 1)
    key = key.strip()
    if not key:
        return None

    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    return key, value


def load_env_file(path: Path) -> dict[str, str]:
    """Load simple KEY=VALUE lines from an env file."""
    values: dict[str, str] = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        parsed = _parse_env_line(line)
        if parsed:
            key, value = parsed
            values[key] = value
    return values


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--env-file',
        type=Path,
        help='Optional production env file to validate, e.g. .env.production.local',
    )
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args(sys.argv[1:])

    if args.env_file:
        env_path = args.env_file if args.env_file.is_absolute() else ROOT / args.env_file
        if not env_path.exists():
            print(f'env file not found: {env_path}', file=sys.stderr)
            return 1
        env = load_env_file(env_path)
    else:
        env = dict(os.environ)

    errors = production_readiness_errors(env)
    if errors:
        print('production readiness checks failed', file=sys.stderr)
        for error in errors:
            print(f'- {error}', file=sys.stderr)
        return 1

    print('production readiness checks passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
