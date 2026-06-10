"""R137: datetime.utcnow() deprecated 수정 검증 — 전체 코드베이스에서 완전 제거 확인"""
import ast
import os
import unittest


class TestNoUtcnowUsage(unittest.TestCase):
    """프로젝트 전체에서 deprecated datetime.utcnow() 사용이 없는지 확인"""

    def _collect_python_files(self):
        """프로젝트 루트의 .py 파일 수집 (tests/, .venv/ 제외)"""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        py_files = []
        exclude = {'.venv', 'node_modules', '.git', '__pycache__', 'tests'}
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in exclude]
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


if __name__ == '__main__':
    unittest.main()
