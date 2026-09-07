"""R137: datetime.utcnow() deprecated 수정 검증 — 전체 코드베이스에서 완전 제거 확인"""
import ast
import os
import sys
import unittest


class TestNoUtcnowUsage(unittest.TestCase):
    """프로젝트 전체에서 deprecated datetime.utcnow() 사용이 없는지 확인"""

    def _active_venv_prefixes(self):
        """프로젝트 루트 내부에 있는 활성 가상환경의 정규화된 전체 경로 목록.

        가상환경 '이름'으로 제외 목록을 만들면 venv와 동일한 이름의 프로덕션
        디렉터리(예: 활성 venv tools/env ↔ 프로덕션 services/env)까지 prune해서
        실제 utcnow 위반을 놓친다. 여기서는 경로 전체로만 비교해 해당 하위트리만
        제외하며, 루트 밖 venv는 애초에 루트 하위가 아니라 대상이 아니다.
        """
        root = os.path.realpath(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        prefixes = set()
        for prefix in {sys.prefix, getattr(sys, 'base_prefix', sys.prefix)}:
            if not prefix:
                continue
            prefix_real = os.path.realpath(prefix)
            if (prefix_real != root
                    and prefix_real.startswith(root + os.sep)):
                prefixes.add(prefix_real)
        return prefixes

    def _collect_python_files(self):
        """프로젝트 루트의 .py 파일 수집 (tests/, 가상환경, node_modules 등 제외)

        가상환경 디렉토리 이름(.venv 등)에 의존하면 다른 이름(예: .venv-pipeline)의
        가상환경에서 site-packages의 서드파티 utcnow() 사용이 오탐으로 잡힌다.
        활성 가상환경은 실행 중 인터프리터의 전체 경로로 해당 하위트리만 제외한다.
        """
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        py_files = []
        exclude = {'.venv', 'node_modules', '.git', '__pycache__', 'tests'}
        venv_prefixes = self._active_venv_prefixes()
        for dirpath, dirnames, filenames in os.walk(root):
            dirpath_real = os.path.realpath(dirpath)
            dirnames[:] = [
                d for d in dirnames
                if d not in exclude
                and not any(
                    os.path.join(dirpath_real, d) == p
                    or os.path.join(dirpath_real, d).startswith(p + os.sep)
                    for p in venv_prefixes
                )
            ]
            for f in filenames:
                if f.endswith('.py'):
                    py_files.append(os.path.join(dirpath, f))
        return py_files

    def test_no_utcnow_in_codebase(self):
        """datetime.utcnow() 호출이 프로덕션 코드에 없어야 한다"""
        violations = []
        for filepath in self._collect_python_files():
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    source = f.read()
                tree = ast.parse(source, filename=filepath)
                for node in ast.walk(tree):
                    if (isinstance(node, ast.Call)
                            and isinstance(node.func, ast.Attribute)
                            and node.func.attr == 'utcnow'):
                        rel = os.path.relpath(filepath)
                        violations.append(f"{rel}:{node.lineno}")
            except SyntaxError:
                continue
        self.assertEqual(violations, [], f"datetime.utcnow() 사용 발견: {violations}")

    def test_integration_routes_uses_timezone_utc(self):
        """통합 라우트가 timezone.utc를 사용하는지 확인

        integration_routes.py는 shim으로 축소되고 실제 라우트는
        routes/integrations/ 서브패키지로 분리됨 → 서브패키지 전체를 검사.
        """
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pkg_dir = os.path.join(root, 'routes', 'integrations')
        combined = ''
        for fname in sorted(os.listdir(pkg_dir)):
            if not fname.endswith('.py'):
                continue
            with open(os.path.join(pkg_dir, fname), 'r', encoding='utf-8') as f:
                content = f.read()
            combined += content
            # deprecated utcnow()는 어느 파일에도 없어야 함
            self.assertNotIn(
                'datetime.utcnow()', content,
                f"routes/integrations/{fname}에 deprecated datetime.utcnow() 발견",
            )
        # timezone-aware 시각 생성이 실제로 사용되는지 확인
        self.assertIn('timezone.utc', combined)
        self.assertIn('datetime.now(timezone.utc)', combined)


class TestActiveVenvExclusion(unittest.TestCase):
    """활성 가상환경은 '정규화된 전체 경로'로 해당 하위트리만 제외하는지 검증.

    가상환경 basename을 전역 이름 제외로 쓰면 venv와 동일한 이름의
    프로덕션 디렉터리(예: 활성 venv tools/env ↔ 프로덕션 services/env)까지
    prune해 실제 utcnow 위반을 놓치는 회귀를 방어한다.
    """

    VIOLATION = 'from datetime import datetime\nnow = datetime.utcnow()\n'

    def setUp(self):
        import shutil
        import tempfile
        self._shutil = shutil
        self._tempfile = tempfile
        self.root = tempfile.mkdtemp(prefix='utcnow_scan_')
        os.makedirs(os.path.join(self.root, 'tests'), exist_ok=True)
        # 실제 검사 로직을 임시 트리로 복사해 진짜 구현을 대상으로 검증
        shutil.copyfile(
            os.path.abspath(__file__),
            os.path.join(self.root, 'tests', 'test_r137_utcnow_fix.py'),
        )
        # venv 밖 동명 프로덕션 디렉터리 fixture (항상 스캔되어야 함)
        os.makedirs(os.path.join(self.root, 'services', 'env'), exist_ok=True)
        with open(os.path.join(self.root, 'services', 'env', 'probe.py'), 'w') as f:
            f.write(self.VIOLATION)

    def tearDown(self):
        self._shutil.rmtree(self.root, ignore_errors=True)

    @staticmethod
    def _venv_python(venv_dir):
        subdir = 'Scripts' if os.name == 'nt' else 'bin'
        exe = 'python.exe' if os.name == 'nt' else 'python'
        return os.path.join(venv_dir, subdir, exe)

    def _make_venv(self, venv_dir):
        """sys.executable로 --without-pip venv를 만들고 인터프리터 경로 반환."""
        import subprocess
        subprocess.run(
            [sys.executable, '-m', 'venv', '--without-pip', venv_dir],
            check=True, capture_output=True, timeout=120,
        )
        return self._venv_python(venv_dir)

    def _collect_with(self, interpreter):
        """임시 트리에서 복사된 실제 구현의 _collect_python_files()를 실행.

        반환값: 수집된 파일의 root 기준 상대경로 목록.
        """
        import json
        import subprocess
        probe = os.path.join(self.root, 'tests', '_probe_collect.py')
        with open(probe, 'w') as f:
            f.write(
                'import importlib.util\n'
                'import json\n'
                'import os\n'
                'import sys\n'
                "spec = importlib.util.spec_from_file_location('target', sys.argv[1])\n"
                'mod = importlib.util.module_from_spec(spec)\n'
                'spec.loader.exec_module(mod)\n'
                'files = mod.TestNoUtcnowUsage()._collect_python_files()\n'
                'print(json.dumps(sorted(os.path.relpath(p, sys.argv[2]) for p in files)))\n'
            )
        run = subprocess.run(
            [interpreter, probe,
             os.path.join(self.root, 'tests', 'test_r137_utcnow_fix.py'),
             self.root],
            capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(
            run.returncode, 0,
            f"프로브 실행 실패: {run.stderr[-500:]}",
        )
        return json.loads(run.stdout.strip().splitlines()[-1])

    def test_system_python_scans_production_dirs(self):
        """venv 없는 실행(CI 조건)에서는 루트 내부 프로덕션 파일이 모두 수집된다."""
        files = self._collect_with(sys.executable)
        self.assertIn('services/env/probe.py', files)

    def test_active_venv_prunes_only_own_subtree(self):
        """활성 venv tools/env는 자기 하위트리만 제외하고 동명 프로덕션
        services/env는 계속 스캔한다 (basename 전역 제외 회귀 방어)."""
        venv_py = self._make_venv(os.path.join(self.root, 'tools', 'env'))
        vendor = os.path.join(self.root, 'tools', 'env', 'lib', 'vendor_probe.py')
        os.makedirs(os.path.dirname(vendor), exist_ok=True)
        with open(vendor, 'w') as f:
            f.write(self.VIOLATION)
        files = self._collect_with(venv_py)
        self.assertNotIn('tools/env/lib/vendor_probe.py', files)
        self.assertIn('services/env/probe.py', files)

    def test_external_venv_excludes_nothing_inside_root(self):
        """루트 밖 venv에서 실행하면 루트 내부 어떤 경로도 제외되지 않는다."""
        external = self._tempfile.mkdtemp(prefix='utcnow_ext_')
        try:
            venv_py = self._make_venv(os.path.join(external, 'venv'))
            files = self._collect_with(venv_py)
            self.assertIn('services/env/probe.py', files)
        finally:
            self._shutil.rmtree(external, ignore_errors=True)

    def test_nested_venv_prunes_only_innermost(self):
        """중첩 venv 실행 시 활성(안쪽) venv만 제외하고 바깥 venv의
        비활성 site-packages는 정적 이름 제외 규칙과 무관하게 그대로 둔다."""
        outer_py = self._make_venv(os.path.join(self.root, 'tools', 'env'))
        inner_py = self._make_venv(os.path.join(self.root, 'tools', 'env', 'inner'))
        vendor = os.path.join(self.root, 'tools', 'env', 'lib', 'vendor_probe.py')
        os.makedirs(os.path.dirname(vendor), exist_ok=True)
        with open(vendor, 'w') as f:
            f.write(self.VIOLATION)
        inner_fixture = os.path.join(
            self.root, 'tools', 'env', 'inner', 'lib', 'inner_probe.py')
        os.makedirs(os.path.dirname(inner_fixture), exist_ok=True)
        with open(inner_fixture, 'w') as f:
            f.write(self.VIOLATION)
        self.assertNotEqual(outer_py, inner_py)
        files = self._collect_with(inner_py)
        self.assertNotIn('tools/env/inner/lib/inner_probe.py', files)
        self.assertIn('services/env/probe.py', files)


if __name__ == '__main__':
    unittest.main()
