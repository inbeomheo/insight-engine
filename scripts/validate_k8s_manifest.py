"""Validate the checked-in Kubernetes production manifest."""
import os
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from utils.production_readiness import (  # noqa: E402
    parse_cors_origins,
    production_security_errors,
    public_app_url_configuration_errors,
    trusted_host_configuration_errors,
)

DEFAULT_MANIFEST = ROOT / 'k8s' / 'deployment.yaml'
NAMESPACE = 'insight-engine'
APP_DEPLOYMENTS = {'insight-backend', 'insight-frontend'}
REQUIRED_DEPLOYMENTS = APP_DEPLOYMENTS | {'insight-worker', 'insight-redis'}
REQUIRED_SERVICES = {'insight-backend', 'insight-frontend', 'insight-redis'}
REQUIRED_PVCS = {
    'insight-data-pvc',
    'insight-backups-pvc',
    'insight-backup-replica-pvc',
    'insight-redis-pvc',
}
SHARED_APP_PVCS = {
    'insight-data-pvc',
    'insight-backups-pvc',
    'insight-backup-replica-pvc',
}
SECRET_CONFIG_KEYS = {
    'SECRET_KEY',
    'ENCRYPTION_SECRET',
    'METRICS_AUTH_TOKEN',
    'BASIC_AUTH_HASH',
    'SENTRY_DSN',
    'ALERT_WEBHOOK_URL',
    'SUPPORT_HANDOFF_SECRET',
    'SUPPORT_GITHUB_TOKEN',
}
SIGNED_INBOUND_WEBHOOK_PATHS = {
    '/api/payment/webhook',
    '/api/paddle/webhook',
    '/api/crypto/webhook',
    '/api/webhooks/slack',
    '/api/webhooks/discord',
    '/api/webhooks/telegram',
}
VALIDATOR_METRICS_TOKEN = 'validator-metrics-token-1234567890abcdefABCDEF'
VALIDATOR_SECRET_KEY = 'validator-secret-key-1234567890abcdefABCDEF'
VALIDATOR_ENCRYPTION_SECRET = 'validator-encryption-secret-1234567890abcdefABCDEF'


def _documents(path: Path) -> list[dict[str, Any]]:
    with path.open('r', encoding='utf-8') as handle:
        return [doc for doc in yaml.safe_load_all(handle) if doc]


def _metadata_name(resource: dict[str, Any]) -> str:
    return str(resource.get('metadata', {}).get('name', ''))


def _by_kind(resources: list[dict[str, Any]], kind: str) -> dict[str, dict[str, Any]]:
    return {_metadata_name(resource): resource for resource in resources if resource.get('kind') == kind}


def _nested(resource: dict[str, Any], *keys: str, default: Any = None) -> Any:
    value: Any = resource
    for key in keys:
        if not isinstance(value, dict):
            return default
        value = value.get(key)
    return default if value is None else value


def _containers(deployment: dict[str, Any]) -> list[dict[str, Any]]:
    return _nested(deployment, 'spec', 'template', 'spec', 'containers', default=[])


def _container(deployment: dict[str, Any]) -> dict[str, Any]:
    containers = _containers(deployment)
    return containers[0] if containers else {}


def _env_from_names(container: dict[str, Any], ref_name: str) -> set[str]:
    names: set[str] = set()
    for entry in container.get('envFrom', []) or []:
        ref = entry.get(ref_name)
        if ref:
            names.add(ref.get('name', ''))
    return names


def _env_value(container: dict[str, Any], name: str) -> str:
    for entry in container.get('env', []) or []:
        if entry.get('name') == name:
            return str(entry.get('value', ''))
    return ''


def _probe_path(container: dict[str, Any], probe_name: str) -> str:
    return str(_nested(container, probe_name, 'httpGet', 'path', default=''))


def _volume_mount_paths(container: dict[str, Any]) -> set[str]:
    return {mount.get('mountPath', '') for mount in container.get('volumeMounts', []) or []}


def _volume_names(deployment: dict[str, Any]) -> set[str]:
    return {volume.get('name', '') for volume in _nested(deployment, 'spec', 'template', 'spec', 'volumes', default=[])}


def _resource_key(resource: dict[str, Any]) -> str:
    kind = resource.get('kind', '<unknown>')
    name = _metadata_name(resource) or '<unnamed>'
    return f'{kind}/{name}'


def _validate_common_resources(resources: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for resource in resources:
        metadata = resource.get('metadata') or {}
        namespace = metadata.get('namespace')
        if resource.get('kind') != 'Namespace' and namespace != NAMESPACE:
            errors.append(f'{_resource_key(resource)} must be in namespace {NAMESPACE}')

        annotations = metadata.get('annotations') or {}
        if annotations.get('prometheus.io/scrape') == 'true':
            errors.append(f'{_resource_key(resource)} must not scrape protected /metrics with anonymous annotations')

    return errors


def _validate_config_map(config_map: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    data = config_map.get('data') or {}
    required_keys = {
        'FLASK_ENV',
        'AUTH_MODE',
        'CORS_ORIGINS',
        'INSIGHT_BASE_URL',
        'APP_BASE_URL',
        'TRUSTED_HOSTS',
        'REDIS_URL',
        'PUBLISH_QUEUE_BACKEND',
        'PUBLISH_QUEUE_REDIS_URL',
        'AGENT_DB_PATH',
        'APP_DATA_BACKUP_DIR',
        'APP_DATA_BACKUP_REPLICA_DIR',
        'CHROMA_DB_PATH',
        'FEEDBACK_DATA_DIR',
        'FEEDBACK_STORE_DIR',
        'FINETUNE_OUTPUT_DIR',
        'GRAPH_STORE_PATH',
        'JOB_STORE_DIR',
        'PREFERENCE_DATA_PATH',
        'SHARE_PAGE_DIR',
        'USER_MEMORY_PATH',
        'ERROR_TRACKING_REQUIRED',
        'ALERT_WEBHOOK_REQUIRED',
        'SCHEDULER_ENABLED',
        'SCHEDULER_HEARTBEAT_FILE',
    }
    for key in sorted(required_keys):
        if not data.get(key):
            errors.append(f'ConfigMap/insight-config missing {key}')

    for key in data:
        if key in SECRET_CONFIG_KEYS or key.endswith('_API_KEY') or key.endswith('_TOKEN'):
            errors.append(f'ConfigMap/insight-config must not contain secret key {key}')

    if data.get('FLASK_ENV') != 'production':
        errors.append('ConfigMap/insight-config FLASK_ENV must be production')
    if data.get('AUTH_MODE') not in {'edge', 'supabase'}:
        errors.append('ConfigMap/insight-config AUTH_MODE must be edge or supabase')
    if data.get('PUBLISH_QUEUE_BACKEND') != 'redis':
        errors.append('ConfigMap/insight-config PUBLISH_QUEUE_BACKEND must be redis')
    if data.get('ERROR_TRACKING_REQUIRED') != 'true':
        errors.append('ConfigMap/insight-config must require error tracking')
    if data.get('ALERT_WEBHOOK_REQUIRED') != 'true':
        errors.append('ConfigMap/insight-config must require alert webhook checks')
    if data.get('SCHEDULER_ENABLED') != 'false':
        errors.append('ConfigMap/insight-config SCHEDULER_ENABLED must be false for replicated app pods')

    public_env = {
        'FLASK_ENV': 'production',
        'TRUSTED_HOSTS': data.get('TRUSTED_HOSTS', ''),
        'INSIGHT_BASE_URL': data.get('INSIGHT_BASE_URL', ''),
        'APP_BASE_URL': data.get('APP_BASE_URL', ''),
    }
    for error in production_security_errors(
        'production',
        parse_cors_origins(data.get('CORS_ORIGINS', '')),
        VALIDATOR_METRICS_TOKEN,
        VALIDATOR_SECRET_KEY,
        VALIDATOR_ENCRYPTION_SECRET,
    ):
        errors.append(f'ConfigMap/insight-config {error}')
    for error in trusted_host_configuration_errors(public_env):
        errors.append(f'ConfigMap/insight-config {error}')
    for error in public_app_url_configuration_errors(public_env):
        errors.append(f'ConfigMap/insight-config {error}')
    return errors


def _validate_deployment(name: str, deployment: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    spec = deployment.get('spec') or {}
    template_spec = _nested(deployment, 'spec', 'template', 'spec', default={})
    pod_security = template_spec.get('securityContext') or {}
    container = _container(deployment)
    container_security = container.get('securityContext') or {}

    if name in APP_DEPLOYMENTS and int(spec.get('replicas') or 0) < 2:
        errors.append(f'Deployment/{name} must run at least 2 replicas')

    if name in APP_DEPLOYMENTS:
        rolling = _nested(deployment, 'spec', 'strategy', 'rollingUpdate', default={})
        if _nested(deployment, 'spec', 'strategy', 'type') != 'RollingUpdate':
            errors.append(f'Deployment/{name} must use RollingUpdate')
        if rolling.get('maxUnavailable') not in (0, '0'):
            errors.append(f'Deployment/{name} maxUnavailable must be 0')

    if template_spec.get('automountServiceAccountToken') is not False:
        errors.append(f'Deployment/{name} must disable service account token automounting')
    if pod_security.get('runAsNonRoot') is not True:
        errors.append(f'Deployment/{name} must set runAsNonRoot')
    if _nested(pod_security, 'seccompProfile', 'type') != 'RuntimeDefault':
        errors.append(f'Deployment/{name} must use RuntimeDefault seccomp')

    expected_uid = 999
    if pod_security.get('runAsUser') != expected_uid:
        errors.append(f'Deployment/{name} runAsUser must be {expected_uid}')
    if pod_security.get('runAsGroup') != expected_uid:
        errors.append(f'Deployment/{name} runAsGroup must be {expected_uid}')

    image = str(container.get('image', ''))
    if not image:
        errors.append(f'Deployment/{name} must set a container image')
    if image.endswith(':latest') or ':latest@' in image:
        errors.append(f'Deployment/{name} must not use :latest image tags')
    if container.get('imagePullPolicy') == 'Always':
        errors.append(f'Deployment/{name} must use immutable images, not imagePullPolicy Always')

    if not container.get('resources', {}).get('requests'):
        errors.append(f'Deployment/{name} must set resource requests')
    if not container.get('resources', {}).get('limits'):
        errors.append(f'Deployment/{name} must set resource limits')

    if container_security.get('allowPrivilegeEscalation') is not False:
        errors.append(f'Deployment/{name} must disable privilege escalation')
    if container_security.get('readOnlyRootFilesystem') is not True:
        errors.append(f'Deployment/{name} must use a read-only root filesystem')
    if 'ALL' not in _nested(container_security, 'capabilities', 'drop', default=[]):
        errors.append(f'Deployment/{name} must drop all Linux capabilities')

    return errors


def _validate_backend(deployment: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    container = _container(deployment)
    if container.get('command') != [
        'gunicorn',
        '--workers=2',
        '--threads=4',
        '--timeout=300',
        '--bind=0.0.0.0:5001',
        'app:app',
    ]:
        errors.append('Deployment/insight-backend must run gunicorn app:app with the approved worker settings')
    if 'insight-config' not in _env_from_names(container, 'configMapRef'):
        errors.append('Deployment/insight-backend must load insight-config ConfigMap')
    if 'insight-secrets' not in _env_from_names(container, 'secretRef'):
        errors.append('Deployment/insight-backend must load insight-secrets Secret')
    if _probe_path(container, 'readinessProbe') != '/ready':
        errors.append('Deployment/insight-backend readinessProbe must use /ready')
    if _probe_path(container, 'livenessProbe') != '/health':
        errors.append('Deployment/insight-backend livenessProbe must use /health')
    if _probe_path(container, 'startupProbe') != '/health':
        errors.append('Deployment/insight-backend startupProbe must use /health')

    required_mounts = {
        '/app/data',
        '/app/backups',
        '/app/backup-replica',
        '/app/cache',
        '/app/logs',
        '/tmp',
        '/app/.gunicorn',
    }
    missing_mounts = required_mounts - _volume_mount_paths(container)
    for mount in sorted(missing_mounts):
        errors.append(f'Deployment/insight-backend missing writable mount {mount}')

    required_volumes = {'app-data', 'app-backups', 'app-backup-replica', 'app-cache', 'app-logs', 'tmp', 'gunicorn-tmp'}
    missing_volumes = required_volumes - _volume_names(deployment)
    for volume in sorted(missing_volumes):
        errors.append(f'Deployment/insight-backend missing volume {volume}')
    return errors


def _validate_worker(deployment: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    spec = deployment.get('spec') or {}
    container = _container(deployment)
    if int(spec.get('replicas') or 0) != 1:
        errors.append('Deployment/insight-worker must run exactly 1 replica')
    if 'insight-config' not in _env_from_names(container, 'configMapRef'):
        errors.append('Deployment/insight-worker must load insight-config ConfigMap')
    if 'insight-secrets' not in _env_from_names(container, 'secretRef'):
        errors.append('Deployment/insight-worker must load insight-secrets Secret')
    if _env_value(container, 'SCHEDULER_ENABLED') != 'true':
        errors.append('Deployment/insight-worker must set SCHEDULER_ENABLED=true')
    if container.get('command') != ['python', 'scripts/run_scheduler_worker.py']:
        errors.append('Deployment/insight-worker must run scripts/run_scheduler_worker.py')
    if not container.get('readinessProbe', {}).get('exec'):
        errors.append('Deployment/insight-worker must use an exec readinessProbe')
    if not container.get('livenessProbe', {}).get('exec'):
        errors.append('Deployment/insight-worker must use an exec livenessProbe')

    required_mounts = {
        '/app/data',
        '/app/backups',
        '/app/backup-replica',
        '/app/cache',
        '/app/logs',
        '/tmp',
    }
    missing_mounts = required_mounts - _volume_mount_paths(container)
    for mount in sorted(missing_mounts):
        errors.append(f'Deployment/insight-worker missing writable mount {mount}')

    required_volumes = {'app-data', 'app-backups', 'app-backup-replica', 'app-cache', 'app-logs', 'tmp'}
    missing_volumes = required_volumes - _volume_names(deployment)
    for volume in sorted(missing_volumes):
        errors.append(f'Deployment/insight-worker missing volume {volume}')
    return errors


def _validate_frontend(deployment: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    container = _container(deployment)
    if 'insight-config' not in _env_from_names(container, 'configMapRef'):
        errors.append('Deployment/insight-frontend must load insight-config ConfigMap')
    if _probe_path(container, 'readinessProbe') != '/':
        errors.append('Deployment/insight-frontend readinessProbe must use /')
    required_mounts = {'/tmp', '/app/frontend/.next/cache', '/app/frontend/.next/diagnostics'}
    missing_mounts = required_mounts - _volume_mount_paths(container)
    for mount in sorted(missing_mounts):
        errors.append(f'Deployment/insight-frontend missing writable mount {mount}')
    return errors


def _validate_redis(deployment: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    container = _container(deployment)
    command = [str(part) for part in container.get('command', [])]
    if '--appendonly' not in command or 'yes' not in command:
        errors.append('Deployment/insight-redis must enable Redis AOF persistence')
    if '/data' not in _volume_mount_paths(container):
        errors.append('Deployment/insight-redis must mount persistent /data')
    if '/tmp' not in _volume_mount_paths(container):
        errors.append('Deployment/insight-redis must mount writable /tmp')
    if not container.get('readinessProbe', {}).get('exec'):
        errors.append('Deployment/insight-redis must use an exec readinessProbe')
    return errors


def _validate_pvc(name: str, pvc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    spec = pvc.get('spec') or {}
    access_modes = set(spec.get('accessModes') or [])
    storage_class = str(spec.get('storageClassName') or '')
    storage_request = _nested(spec, 'resources', 'requests', 'storage', default='')

    if name in SHARED_APP_PVCS:
        if 'ReadWriteMany' not in access_modes:
            errors.append(f'PersistentVolumeClaim/{name} must use ReadWriteMany for replicated app pods')
        if not storage_class:
            errors.append(f'PersistentVolumeClaim/{name} must set a ReadWriteMany-capable storageClassName')
    elif name == 'insight-redis-pvc':
        if access_modes != {'ReadWriteOnce'}:
            errors.append('PersistentVolumeClaim/insight-redis-pvc must use ReadWriteOnce')

    if not storage_request:
        errors.append(f'PersistentVolumeClaim/{name} must request storage')
    return errors


def _ingress_path_map(ingress: dict[str, Any]) -> dict[str, str]:
    path_map: dict[str, str] = {}
    for rule in _nested(ingress, 'spec', 'rules', default=[]):
        for path in _nested(rule, 'http', 'paths', default=[]):
            path_map[path.get('path', '')] = _nested(path, 'backend', 'service', 'name', default='')
    return path_map


def _ingress_paths(ingress: dict[str, Any]) -> dict[str, dict[str, Any]]:
    paths: dict[str, dict[str, Any]] = {}
    for rule in _nested(ingress, 'spec', 'rules', default=[]):
        for path in _nested(rule, 'http', 'paths', default=[]):
            paths[path.get('path', '')] = path
    return paths


def _validate_public_ingress(ingress: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    annotations = ingress.get('metadata', {}).get('annotations') or {}
    if 'nginx.ingress.kubernetes.io/rewrite-target' in annotations:
        errors.append('Ingress/insight-public-ingress must not rewrite paths')
    if annotations.get('nginx.ingress.kubernetes.io/ssl-redirect') != 'true':
        errors.append('Ingress/insight-public-ingress must force SSL redirect')
    if 'nginx.ingress.kubernetes.io/auth-type' in annotations:
        errors.append('Ingress/insight-public-ingress must leave health and share routes unauthenticated')
    if not _nested(ingress, 'spec', 'tls', default=[]):
        errors.append('Ingress/insight-public-ingress must configure TLS')

    path_map = _ingress_path_map(ingress)
    paths = _ingress_paths(ingress)
    for backend_path in ('/health', '/ready', '/share', '/api/shares/', *sorted(SIGNED_INBOUND_WEBHOOK_PATHS)):
        if path_map.get(backend_path) != 'insight-backend':
            errors.append(f'Ingress/insight-public-ingress must route {backend_path} to insight-backend')
    if path_map.get('/api/shares'):
        errors.append('Ingress/insight-public-ingress must not expose protected /api/shares create route')
    for backend_path in ('/health', '/ready'):
        if paths.get(backend_path, {}).get('pathType') != 'Exact':
            errors.append(f'Ingress/insight-public-ingress must expose {backend_path} as Exact')
    for backend_path in sorted(SIGNED_INBOUND_WEBHOOK_PATHS):
        if paths.get(backend_path, {}).get('pathType') != 'Exact':
            errors.append(f'Ingress/insight-public-ingress must expose signed webhook {backend_path} as Exact')
    if paths.get('/api/shares/', {}).get('pathType') != 'Prefix':
        errors.append('Ingress/insight-public-ingress must expose /api/shares/ public reads as Prefix')
    return errors


def _validate_protected_ingress(ingress: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    annotations = ingress.get('metadata', {}).get('annotations') or {}
    if 'nginx.ingress.kubernetes.io/rewrite-target' in annotations:
        errors.append('Ingress/insight-ingress must not rewrite API paths')
    if annotations.get('nginx.ingress.kubernetes.io/ssl-redirect') != 'true':
        errors.append('Ingress/insight-ingress must force SSL redirect')
    if annotations.get('nginx.ingress.kubernetes.io/auth-type') != 'basic':
        errors.append('Ingress/insight-ingress must enforce edge basic auth')
    if not _nested(ingress, 'spec', 'tls', default=[]):
        errors.append('Ingress/insight-ingress must configure TLS')

    path_map = _ingress_path_map(ingress)
    for backend_path in SIGNED_INBOUND_WEBHOOK_PATHS:
        if path_map.get(backend_path):
            errors.append(f'Ingress/insight-ingress must not protect signed webhook {backend_path} with basic auth')

    for backend_path in (
        '/api',
        '/generate',
        '/generate-stream',
        '/generate-batch',
        '/regenerate',
        '/feed.xml',
        '/version',
        '/metrics',
        '/openapi.json',
        '/oauth',
        '/graphql',
    ):
        if path_map.get(backend_path) != 'insight-backend':
            errors.append(f'Ingress/insight-ingress must route {backend_path} to insight-backend')
    if path_map.get('/') != 'insight-frontend':
        errors.append('Ingress/insight-ingress must route / to insight-frontend')
    return errors


def validate_manifest(path: Path) -> list[str]:
    resources = _documents(path)
    errors = _validate_common_resources(resources)
    deployments = _by_kind(resources, 'Deployment')
    services = _by_kind(resources, 'Service')
    pvcs = _by_kind(resources, 'PersistentVolumeClaim')
    config_maps = _by_kind(resources, 'ConfigMap')
    ingresses = _by_kind(resources, 'Ingress')

    for deployment_name in sorted(REQUIRED_DEPLOYMENTS):
        deployment = deployments.get(deployment_name)
        if not deployment:
            errors.append(f'Deployment/{deployment_name} is required')
            continue
        errors.extend(_validate_deployment(deployment_name, deployment))

    if 'insight-backend' in deployments:
        errors.extend(_validate_backend(deployments['insight-backend']))
    if 'insight-worker' in deployments:
        errors.extend(_validate_worker(deployments['insight-worker']))
    if 'insight-frontend' in deployments:
        errors.extend(_validate_frontend(deployments['insight-frontend']))
    if 'insight-redis' in deployments:
        errors.extend(_validate_redis(deployments['insight-redis']))

    for service_name in sorted(REQUIRED_SERVICES):
        if service_name not in services:
            errors.append(f'Service/{service_name} is required')
    for pvc_name in sorted(REQUIRED_PVCS):
        pvc = pvcs.get(pvc_name)
        if not pvc:
            errors.append(f'PersistentVolumeClaim/{pvc_name} is required')
            continue
        errors.extend(_validate_pvc(pvc_name, pvc))

    config_map = config_maps.get('insight-config')
    if not config_map:
        errors.append('ConfigMap/insight-config is required')
    else:
        errors.extend(_validate_config_map(config_map))

    public_ingress = ingresses.get('insight-public-ingress')
    if not public_ingress:
        errors.append('Ingress/insight-public-ingress is required')
    else:
        errors.extend(_validate_public_ingress(public_ingress))

    protected_ingress = ingresses.get('insight-ingress')
    if not protected_ingress:
        errors.append('Ingress/insight-ingress is required')
    else:
        errors.extend(_validate_protected_ingress(protected_ingress))

    secret_resources = _by_kind(resources, 'Secret')
    if 'insight-secrets' in secret_resources:
        errors.append('Secret/insight-secrets must be created out of band, not committed to the manifest')

    return errors


def main() -> int:
    manifest = Path(os.getenv('K8S_MANIFEST') or DEFAULT_MANIFEST)
    errors = validate_manifest(manifest)
    if errors:
        print('kubernetes manifest validation failed', file=sys.stderr)
        for error in errors:
            print(f'- {error}', file=sys.stderr)
        return 1

    print('kubernetes manifest validation passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
