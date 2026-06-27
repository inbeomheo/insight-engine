"""Fail when tracked files contain likely real secrets."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ('openai_api_key', re.compile(r'\bsk-(?:proj-)?[A-Za-z0-9_-]{16,}\b')),
    ('anthropic_api_key', re.compile(r'\bsk-ant-[A-Za-z0-9_-]{16,}\b')),
    ('google_api_key', re.compile(r'\bAIza[0-9A-Za-z_-]{20,}\b')),
    ('github_token', re.compile(r'\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b')),
    ('github_pat', re.compile(r'\bgithub_pat_[A-Za-z0-9_]{20,}\b')),
    ('slack_token', re.compile(r'\bxox[baprs]-[A-Za-z0-9-]{16,}\b')),
    ('stripe_secret_key', re.compile(r'\bsk_live_[A-Za-z0-9]{16,}\b')),
    ('stripe_webhook_secret', re.compile(r'\bwhsec_[A-Za-z0-9]{16,}\b')),
    ('aws_access_key_id', re.compile(r'\b(?:AKIA|ASIA)[0-9A-Z]{16}\b')),
)

PLACEHOLDER_WORDS = (
    'placeholder',
    'example',
    'dummy',
    'fake',
    'sample',
    'test',
    'secret',
    'token',
    'your-',
    'ci-',
    'xxx',
)

SKIP_SUFFIXES = {
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.webp', '.svg',
    '.sqlite3', '.db', '.zip', '.gz', '.tgz', '.mp4', '.mp3',
    '.woff', '.woff2', '.ttf', '.pdf', '.docx',
}

SKIP_PARTS = {
    '.git',
    '.next',
    'node_modules',
    'test-results',
    'playwright-report',
    'html-report',
}


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    kind: str
    preview: str


def _is_placeholder(token: str) -> bool:
    lowered = token.lower()
    if any(word in lowered for word in PLACEHOLDER_WORDS):
        return True
    if '...' in token:
        return True
    if '1234567890abcdef' in lowered or 'abcdefghijklmnop' in lowered:
        return True
    if lowered in {'sk-abcdefghijklmnop', 'xoxb-token'}:
        return True
    return False


def _redact(token: str) -> str:
    if len(token) <= 8:
        return '*' * len(token)
    return f'{token[:4]}...{token[-4:]}'


def _should_skip(path: Path) -> bool:
    if path.suffix.lower() in SKIP_SUFFIXES:
        return True
    return any(part in SKIP_PARTS for part in path.parts)


def tracked_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
    )
    return [
        root / name
        for name in result.stdout.decode('utf-8').split('\0')
        if name
    ]


def scan_file(path: Path, root: Path) -> list[Finding]:
    if not path.exists() or _should_skip(path):
        return []

    try:
        text = path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        text = path.read_text(encoding='utf-8', errors='ignore')
    except OSError:
        return []

    findings: list[Finding] = []
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError:
        relative = str(path)
    for line_number, line in enumerate(text.splitlines(), start=1):
        for kind, pattern in SECRET_PATTERNS:
            for match in pattern.finditer(line):
                token = match.group(0)
                if _is_placeholder(token):
                    continue
                findings.append(Finding(
                    path=relative,
                    line=line_number,
                    kind=kind,
                    preview=_redact(token),
                ))
    return findings


def scan_paths(paths: list[Path], root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in paths:
        findings.extend(scan_file(path if path.is_absolute() else root / path, root))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', nargs='*', help='Optional files to scan. Defaults to git tracked files.')
    parser.add_argument('--json', action='store_true', help='Emit JSON findings.')
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    root = Path(__file__).resolve().parents[1]
    paths = [Path(path) for path in args.paths] if args.paths else tracked_files(root)
    findings = scan_paths(paths, root)

    if args.json:
        print(json.dumps([asdict(finding) for finding in findings], indent=2, sort_keys=True))
    elif findings:
        print('secret scan failed: likely real secrets found in tracked files', file=sys.stderr)
        for finding in findings:
            print(
                f'{finding.path}:{finding.line}: {finding.kind} {finding.preview}',
                file=sys.stderr,
            )
    else:
        print('secret scan passed')

    return 1 if findings else 0


if __name__ == '__main__':
    raise SystemExit(main())
