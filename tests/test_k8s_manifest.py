"""Kubernetes production manifest hardening contract."""
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'k8s' / 'deployment.yaml'
VALIDATOR = ROOT / 'scripts' / 'validate_k8s_manifest.py'


def _docs():
    return [doc for doc in yaml.safe_load_all(MANIFEST.read_text(encoding='utf-8')) if doc]


def _by_kind(kind):
    return {doc['metadata']['name']: doc for doc in _docs() if doc.get('kind') == kind}


def _run_validator(manifest):
    env = os.environ.copy()
    env['K8S_MANIFEST'] = str(manifest)
    return subprocess.run(
        [sys.executable, str(VALIDATOR)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_k8s_manifest_validation_passes():
    result = _run_validator(MANIFEST)

    assert result.returncode == 0
    assert 'kubernetes manifest validation passed' in result.stdout


def test_k8s_manifest_hardens_application_deployments():
    deployments = _by_kind('Deployment')

    for name in ('insight-backend', 'insight-frontend'):
        deployment = deployments[name]
        pod_spec = deployment['spec']['template']['spec']
        container = pod_spec['containers'][0]

        assert deployment['spec']['replicas'] >= 2
        assert deployment['spec']['strategy']['rollingUpdate']['maxUnavailable'] == 0
        assert pod_spec['automountServiceAccountToken'] is False
        assert pod_spec['securityContext']['runAsNonRoot'] is True
        assert pod_spec['securityContext']['runAsUser'] == 999
        assert pod_spec['securityContext']['seccompProfile']['type'] == 'RuntimeDefault'
        assert container['securityContext']['allowPrivilegeEscalation'] is False
        assert container['securityContext']['readOnlyRootFilesystem'] is True
        assert container['securityContext']['capabilities']['drop'] == ['ALL']
        assert not container['image'].endswith(':latest')


def test_k8s_backend_uses_runtime_readiness_and_backup_replica_volume():
    backend = _by_kind('Deployment')['insight-backend']
    container = backend['spec']['template']['spec']['containers'][0]
    mount_paths = {mount['mountPath'] for mount in container['volumeMounts']}
    volume_claims = {
        volume['persistentVolumeClaim']['claimName']
        for volume in backend['spec']['template']['spec']['volumes']
        if 'persistentVolumeClaim' in volume
    }

    assert container['command'] == [
        'gunicorn',
        '--workers=2',
        '--threads=4',
        '--timeout=300',
        '--bind=0.0.0.0:5001',
        'app:app',
    ]
    assert container['readinessProbe']['httpGet']['path'] == '/ready'
    assert container['livenessProbe']['httpGet']['path'] == '/health'
    assert '/app/backup-replica' in mount_paths
    assert 'insight-backup-replica-pvc' in volume_claims
    assert 'insight-secrets' in [
        ref['secretRef']['name']
        for ref in container['envFrom']
        if 'secretRef' in ref
    ]


def test_k8s_runs_background_scheduler_as_single_worker_deployment():
    config = _by_kind('ConfigMap')['insight-config']['data']
    worker = _by_kind('Deployment')['insight-worker']
    container = worker['spec']['template']['spec']['containers'][0]
    mount_paths = {mount['mountPath'] for mount in container['volumeMounts']}
    volume_claims = {
        volume['persistentVolumeClaim']['claimName']
        for volume in worker['spec']['template']['spec']['volumes']
        if 'persistentVolumeClaim' in volume
    }
    env = {entry['name']: entry.get('value') for entry in container['env']}

    assert config['SCHEDULER_ENABLED'] == 'false'
    assert config['SCHEDULER_HEARTBEAT_FILE'] == '/tmp/insight-engine-scheduler.heartbeat'
    assert worker['spec']['replicas'] == 1
    assert container['command'] == ['python', 'scripts/run_scheduler_worker.py']
    assert env['SCHEDULER_ENABLED'] == 'true'
    assert 'insight-config' in [
        ref['configMapRef']['name']
        for ref in container['envFrom']
        if 'configMapRef' in ref
    ]
    assert 'insight-secrets' in [
        ref['secretRef']['name']
        for ref in container['envFrom']
        if 'secretRef' in ref
    ]
    assert '/app/data' in mount_paths
    assert '/app/backups' in mount_paths
    assert '/app/backup-replica' in mount_paths
    assert 'insight-data-pvc' in volume_claims
    assert 'insight-backups-pvc' in volume_claims
    assert 'insight-backup-replica-pvc' in volume_claims
    assert 'exec' in container['readinessProbe']
    assert 'exec' in container['livenessProbe']


def test_k8s_config_map_keeps_secrets_out_of_tracked_manifest():
    config = _by_kind('ConfigMap')['insight-config']['data']
    secret_keys = {'SECRET_KEY', 'ENCRYPTION_SECRET', 'METRICS_AUTH_TOKEN', 'SENTRY_DSN', 'ALERT_WEBHOOK_URL'}

    assert config['FLASK_ENV'] == 'production'
    assert config['AUTH_MODE'] == 'edge'
    assert config['INSIGHT_BASE_URL'] == 'https://insight.example.com'
    assert config['APP_BASE_URL'] == 'https://insight.example.com'
    assert config['PUBLISH_QUEUE_BACKEND'] == 'redis'
    assert config['AGENT_DB_PATH'] == '/app/data/agent_state.db'
    assert config['APP_CACHE_DIR'] == '/app/cache'
    assert config['AI_CACHE_DB'] == '/app/cache/ai_cache.db'
    assert config['CHROMA_DB_PATH'] == '/app/data/chroma_db'
    assert config['CONTENT_BACKUP_DIR'] == '/app/backups/content-library'
    assert config['FEEDBACK_DATA_DIR'] == '/app/data/feedback'
    assert config['FEEDBACK_STORE_DIR'] == '/app/data/feedback'
    assert config['FINETUNE_OUTPUT_DIR'] == '/app/data/finetune'
    assert config['GRAPH_STORE_PATH'] == '/app/data/graph_store'
    assert config['JOB_STORE_DIR'] == '/app/data/jobs'
    assert config['PREFERENCE_DATA_PATH'] == '/app/data/preferences.jsonl'
    assert config['SHARE_PAGE_DIR'] == '/app/data/shared_pages'
    assert config['USER_MEMORY_PATH'] == '/app/data/user_memory'
    assert config['ERROR_TRACKING_REQUIRED'] == 'true'
    assert config['ALERT_WEBHOOK_REQUIRED'] == 'true'
    assert secret_keys.isdisjoint(config)
    assert 'insight-secrets' not in _by_kind('Secret')


def test_k8s_shared_app_pvcs_use_read_write_many_storage():
    pvcs = _by_kind('PersistentVolumeClaim')

    for name in (
        'insight-data-pvc',
        'insight-backups-pvc',
        'insight-backup-replica-pvc',
    ):
        spec = pvcs[name]['spec']
        assert spec['accessModes'] == ['ReadWriteMany']
        assert spec['storageClassName'] == 'replace-with-rwx-storage-class'

    assert pvcs['insight-redis-pvc']['spec']['accessModes'] == ['ReadWriteOnce']


def test_k8s_public_ingress_exposes_health_ready_and_share_without_auth():
    ingress = _by_kind('Ingress')['insight-public-ingress']
    annotations = ingress['metadata']['annotations']
    path_entries = {
        path['path']: path
        for path in ingress['spec']['rules'][0]['http']['paths']
    }
    path_map = {
        path: entry['backend']['service']['name']
        for path, entry in path_entries.items()
    }

    assert 'nginx.ingress.kubernetes.io/rewrite-target' not in annotations
    assert annotations['nginx.ingress.kubernetes.io/ssl-redirect'] == 'true'
    assert 'nginx.ingress.kubernetes.io/auth-type' not in annotations
    assert ingress['spec']['tls'][0]['secretName'] == 'insight-tls'
    assert path_map['/health'] == 'insight-backend'
    assert path_entries['/health']['pathType'] == 'Exact'
    assert path_map['/ready'] == 'insight-backend'
    assert path_entries['/ready']['pathType'] == 'Exact'
    assert path_map['/share'] == 'insight-backend'
    assert path_map['/api/shares/'] == 'insight-backend'
    assert path_entries['/api/shares/']['pathType'] == 'Prefix'
    assert '/api/shares' not in path_map
    for webhook_path in (
        '/api/payment/webhook',
        '/api/paddle/webhook',
        '/api/crypto/webhook',
        '/api/webhooks/slack',
        '/api/webhooks/discord',
        '/api/webhooks/telegram',
    ):
        assert path_map[webhook_path] == 'insight-backend'
        assert path_entries[webhook_path]['pathType'] == 'Exact'


def test_k8s_validator_rejects_public_share_create_route(tmp_path):
    broken = tmp_path / 'deployment.yaml'
    broken.write_text(
        MANIFEST.read_text(encoding='utf-8').replace(
            '- path: /api/shares/\n            pathType: Prefix',
            '- path: /api/shares\n            pathType: Prefix',
            1,
        ),
        encoding='utf-8',
    )

    result = _run_validator(broken)

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'must not expose protected /api/shares create route' in output


def test_k8s_validator_rejects_unsafe_public_urls(tmp_path):
    broken = tmp_path / 'deployment.yaml'
    broken.write_text(
        MANIFEST.read_text(encoding='utf-8')
        .replace('CORS_ORIGINS: "https://insight.example.com"', 'CORS_ORIGINS: "https://insight.example.com/app"')
        .replace('INSIGHT_BASE_URL: "https://insight.example.com"', 'INSIGHT_BASE_URL: "http://127.0.0.1:8090"')
        .replace('APP_BASE_URL: "https://insight.example.com"', 'APP_BASE_URL: "https://10.0.0.5"'),
        encoding='utf-8',
    )

    result = _run_validator(broken)

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'CORS_ORIGINS' in output
    assert 'INSIGHT_BASE_URL' in output
    assert 'APP_BASE_URL' in output


def test_k8s_protected_ingress_preserves_paths_and_requires_tls_auth():
    ingress = _by_kind('Ingress')['insight-ingress']
    annotations = ingress['metadata']['annotations']
    path_map = {
        path['path']: path['backend']['service']['name']
        for path in ingress['spec']['rules'][0]['http']['paths']
    }

    assert 'nginx.ingress.kubernetes.io/rewrite-target' not in annotations
    assert annotations['nginx.ingress.kubernetes.io/ssl-redirect'] == 'true'
    assert annotations['nginx.ingress.kubernetes.io/auth-type'] == 'basic'
    assert ingress['spec']['tls'][0]['secretName'] == 'insight-tls'
    for backend_path in (
        '/api',
        '/generate',
        '/generate-stream',
        '/generate-batch',
        '/regenerate',
        '/metrics',
        '/graphql',
    ):
        assert path_map[backend_path] == 'insight-backend'
    for webhook_path in (
        '/api/payment/webhook',
        '/api/paddle/webhook',
        '/api/crypto/webhook',
        '/api/webhooks/slack',
        '/api/webhooks/discord',
        '/api/webhooks/telegram',
    ):
        assert webhook_path not in path_map
    assert path_map['/'] == 'insight-frontend'


def test_k8s_validator_rejects_latest_tags(tmp_path):
    broken = tmp_path / 'deployment.yaml'
    broken.write_text(
        MANIFEST.read_text(encoding='utf-8').replace(
            'ghcr.io/your-org/insight-engine:replace-with-git-sha',
            'ghcr.io/your-org/insight-engine:latest',
        ),
        encoding='utf-8',
    )

    result = _run_validator(broken)

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'must not use :latest image tags' in output


def test_k8s_validator_rejects_rwo_shared_app_pvcs(tmp_path):
    broken = tmp_path / 'deployment.yaml'
    broken.write_text(
        MANIFEST.read_text(encoding='utf-8').replace(
            'name: insight-data-pvc\n  namespace: insight-engine\nspec:\n  accessModes:\n    - ReadWriteMany',
            'name: insight-data-pvc\n  namespace: insight-engine\nspec:\n  accessModes:\n    - ReadWriteOnce',
        ),
        encoding='utf-8',
    )

    result = _run_validator(broken)

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'PersistentVolumeClaim/insight-data-pvc must use ReadWriteMany' in output


def test_release_gate_exposes_k8s_validation():
    package_json = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))
    verify_release = (ROOT / 'scripts' / 'verify_release.sh').read_text(encoding='utf-8')

    assert package_json['scripts']['verify:k8s'] == 'python3 scripts/validate_k8s_manifest.py'
    assert 'npm run verify:k8s' in verify_release


def test_scheduler_worker_script_exists_for_k8s_worker():
    script = ROOT / 'scripts' / 'run_scheduler_worker.py'
    content = script.read_text(encoding='utf-8')

    assert script.exists()
    assert 'SCHEDULER_ENABLED must be true' in content
    assert 'SCHEDULER_HEARTBEAT_FILE' in content
    assert 'stop_scheduler()' in content
