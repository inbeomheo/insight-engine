"""Run Python commands with the repository virtualenv when it exists."""
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _venv_python() -> Path | None:
    candidates = [
        ROOT / '.venv' / 'Scripts' / 'python.exe',
        ROOT / '.venv' / 'bin' / 'python',
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def main() -> int:
    python = _venv_python()
    current = Path(sys.executable).resolve()
    if python and python.resolve() != current:
        return subprocess.call([str(python), *sys.argv[1:]], cwd=ROOT)
    return subprocess.call([sys.executable, *sys.argv[1:]], cwd=ROOT)


if __name__ == '__main__':
    raise SystemExit(main())
