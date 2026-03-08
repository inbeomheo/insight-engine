"""
시크릿 관리 서비스 (F9-21)
우선순위: AWS Secrets Manager → GCP Secret Manager → Vault → 환경변수 폴백
"""
import os
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# 캐시 (TTL 없음 — 프로세스 수명 동안 유지)
_SECRET_CACHE: Dict[str, str] = {}


def _get_from_aws(secret_name: str) -> Optional[str]:
    """AWS Secrets Manager에서 시크릿 조회"""
    try:
        import boto3
        from botocore.exceptions import ClientError

        region = os.getenv('AWS_DEFAULT_REGION', 'ap-northeast-2')
        client = boto3.client('secretsmanager', region_name=region)
        response = client.get_secret_value(SecretId=secret_name)
        return response.get('SecretString') or response.get('SecretBinary', b'').decode()
    except ImportError:
        logger.debug("boto3 미설치 — AWS Secrets Manager 건너뜀")
        return None
    except Exception as e:
        logger.debug("AWS Secrets Manager 조회 실패: %s", e)
        return None


def _get_from_gcp(secret_name: str) -> Optional[str]:
    """GCP Secret Manager에서 시크릿 조회"""
    try:
        from google.cloud import secretmanager

        project_id = os.getenv('GCP_PROJECT_ID', '')
        if not project_id:
            return None

        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode('utf-8')
    except ImportError:
        logger.debug("google-cloud-secret-manager 미설치 — GCP 건너뜀")
        return None
    except Exception as e:
        logger.debug("GCP Secret Manager 조회 실패: %s", e)
        return None


def _get_from_vault(secret_name: str) -> Optional[str]:
    """HashiCorp Vault에서 시크릿 조회"""
    try:
        import hvac

        vault_url = os.getenv('VAULT_ADDR', 'http://localhost:8200')
        vault_token = os.getenv('VAULT_TOKEN', '')
        if not vault_token:
            return None

        client = hvac.Client(url=vault_url, token=vault_token)
        mount = os.getenv('VAULT_MOUNT', 'secret')
        path = os.getenv('VAULT_PATH', 'insight-engine')

        response = client.secrets.kv.v2.read_secret_version(
            mount_point=mount,
            path=f"{path}/{secret_name}"
        )
        return response['data']['data'].get('value')
    except ImportError:
        logger.debug("hvac 미설치 — Vault 건너뜀")
        return None
    except Exception as e:
        logger.debug("Vault 조회 실패: %s", e)
        return None


def get_secret(secret_name: str, env_fallback: str = '') -> str:
    """
    시크릿 조회 (캐시 → AWS → GCP → Vault → 환경변수 폴백 순서)

    Args:
        secret_name: 시크릿 이름
        env_fallback: 모든 백엔드 실패 시 환경변수 이름

    Returns:
        시크릿 값 (없으면 빈 문자열)
    """
    # 1. 캐시 확인
    if secret_name in _SECRET_CACHE:
        return _SECRET_CACHE[secret_name]

    # 2. AWS Secrets Manager
    value = _get_from_aws(secret_name)

    # 3. GCP Secret Manager
    if not value:
        value = _get_from_gcp(secret_name)

    # 4. Vault
    if not value:
        value = _get_from_vault(secret_name)

    # 5. 환경변수 폴백
    if not value and env_fallback:
        value = os.getenv(env_fallback, '')

    if value:
        _SECRET_CACHE[secret_name] = value
        logger.debug("시크릿 '%s' 로드 완료", secret_name)

    return value or ''


def clear_cache() -> None:
    """시크릿 캐시 초기화 (테스트/갱신 시 사용)"""
    _SECRET_CACHE.clear()


# ── 사전 정의 시크릿 헬퍼 ─────────────────────────────────────────────────────

def get_gemini_api_key() -> str:
    """Gemini API 키 조회"""
    return get_secret('GEMINI_API_KEY', 'GEMINI_API_KEY')


def get_deepseek_api_key() -> str:
    """DeepSeek API 키 조회"""
    return get_secret('DEEPSEEK_API_KEY', 'DEEPSEEK_API_KEY')


def get_supabase_url() -> str:
    """Supabase URL 조회"""
    return get_secret('SUPABASE_URL', 'SUPABASE_URL')


def get_supabase_anon_key() -> str:
    """Supabase Anonymous 키 조회"""
    return get_secret('SUPABASE_ANON_KEY', 'SUPABASE_ANON_KEY')


def get_stripe_secret_key() -> str:
    """Stripe Secret 키 조회"""
    return get_secret('STRIPE_SECRET_KEY', 'STRIPE_SECRET_KEY')
