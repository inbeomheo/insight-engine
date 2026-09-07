const { existsSync } = require('node:fs');
const { resolve } = require('node:path');
const { spawnSync } = require('node:child_process');

const root = resolve(__dirname, '..');

const preferredCandidates = [
  { command: resolve(root, '.venv', 'Scripts', 'python.exe'), args: [] },
  { command: resolve(root, '.venv', 'bin', 'python'), args: [] },
  ...(process.env.PYTHON
    ? [{ command: process.env.PYTHON, args: [] }]
    : []),
];

const systemCandidates = [
  ...(process.platform === 'win32'
    ? [
        { command: 'py', args: ['-3.11'] },
        { command: 'python', args: [] },
      ]
    : [
        { command: 'python3.11', args: [] },
        { command: 'python3', args: [] },
        { command: 'python', args: [] },
      ]),
];

function isPython311(candidate) {
  if (candidate.command.includes('/') || candidate.command.includes('\\')) {
    if (!existsSync(candidate.command)) return false;
  }
  const probe = spawnSync(candidate.command, [
    ...candidate.args,
    '-c',
    'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)',
  ], {
    cwd: root,
    stdio: 'ignore',
  });
  return !probe.error && probe.status === 0;
}

function commandAvailable(command) {
  const probe = spawnSync(command, ['--version'], { cwd: root, stdio: 'ignore' });
  return !probe.error && probe.status === 0;
}

let interpreter = preferredCandidates.find(isPython311);
if (!interpreter && commandAvailable('uv')) {
  interpreter = {
    command: 'uv',
    args: [
      'run',
      '--python',
      '3.11',
      '--with-requirements',
      'requirements.txt',
      '--with-requirements',
      'requirements-dev.txt',
      'python',
    ],
  };
}
interpreter ??= systemCandidates.find(isPython311);

if (!interpreter) {
  console.error('Python 3.11+ 실행 파일을 찾지 못했습니다. .venv를 만들거나 Python을 설치해주세요.');
  process.exit(1);
}

const result = spawnSync(
  interpreter.command,
  [...interpreter.args, ...process.argv.slice(2)],
  {
    cwd: root,
    env: process.env,
    stdio: 'inherit',
  },
);

if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}
process.exit(result.status ?? 1);
