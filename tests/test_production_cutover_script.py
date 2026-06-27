"""Production cutover gate script contract."""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'production_cutover_check.sh'


def test_cutover_script_enforces_strict_external_gates():
    script = SCRIPT.read_text(encoding='utf-8')

    assert 'ERROR_TRACKING_REQUIRED="${ERROR_TRACKING_REQUIRED:-true}"' in script
    assert 'ALERT_WEBHOOK_REQUIRED="${ALERT_WEBHOOK_REQUIRED:-true}"' in script
    assert 'INSIGHT_BASE_URL or APP_BASE_URL is required' in script
    assert 'check_release_source_state.py --require-clean' in script
    assert 'npm run verify:release' in script
    assert 'check_production_readiness.py' in script
    assert 'verify_docker_image_hygiene.sh "$image_ref"' in script
    assert 'EXPECTED_GIT_SHA="$GIT_SHA"' in script
    assert 'check_host_prereqs.py \\' in script
    assert '--require-overcommit' in script
    assert '--require-persistent-overcommit' in script
    assert '--require-external-backups' in script
    assert '--require-backup-mounts' in script
    assert 'backup_app_data.py drill-latest --summary' in script
    assert '--require-public-host' in script
    assert '--require-https' in script
    assert '--tls-min-days "$tls_min_days"' in script
    assert '--require-webhook' in script
    assert '--require-webhook-https' in script
    assert '--require-webhook-public-host' in script
    assert '--send-test-alert' in script


def test_package_json_exposes_cutover_check_script():
    package_json = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))

    assert package_json['scripts']['ops:cutover-check'] == 'bash scripts/production_cutover_check.sh'
