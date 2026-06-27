import ast
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _environment_names(environment) -> set[str]:
    if isinstance(environment, dict):
        return set(environment)
    return {item.split('=', 1)[0] for item in environment or []}


def _config_exports_and_assignments() -> tuple[set[str], set[str]]:
    tree = ast.parse((ROOT / 'config.py').read_text(encoding='utf-8'))
    exports: set[str] = set()
    assignments: set[str] = set()

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assignments.add(target.id)
                    if target.id == '__all__' and isinstance(node.value, ast.List):
                        exports = {
                            item.value for item in node.value.elts
                            if isinstance(item, ast.Constant) and isinstance(item.value, str)
                        }
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            assignments.add(node.target.id)

    return exports, assignments


def test_default_compose_forwards_canonical_encryption_secret():
    compose = yaml.safe_load((ROOT / 'docker-compose.yml').read_text(encoding='utf-8'))
    backend_env = _environment_names(compose['services']['backend']['environment'])

    assert 'ENCRYPTION_SECRET' in backend_env
    assert 'ENCRYPTION_KEY' not in backend_env


def test_config_exports_canonical_encryption_secret_not_legacy_key():
    exports, assignments = _config_exports_and_assignments()

    assert 'ENCRYPTION_SECRET' in exports
    assert 'ENCRYPTION_SECRET' in assignments
    assert 'ENCRYPTION_KEY' not in exports
    assert 'ENCRYPTION_KEY' not in assignments
