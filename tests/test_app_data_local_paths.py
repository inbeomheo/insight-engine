import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_file_backed_local_fallbacks_default_to_app_data_dir(tmp_path):
    app_data_dir = tmp_path / 'app_data'
    script = """
import json
import importlib
import config
import services.data.api_key_service as api_keys
import services.payment.subscription_service as subscriptions
import services.payment.trial_service as trials
import services.platform.referral_service as referrals
import services.platform.rss_subscription_service as rss
import services.core.content_service as content
import services.data.backup_service as backups
import services.data.memory_service as user_memory
import services.data.prompt_optimizer_service as prompt_feedback
import services.rag.chroma_client_factory as chroma_factory
import services.content.share_page_service as share_pages
import services.support.feedback_store as support_feedback
import agent.memory as agent_memory
from services.finetune.data_collector import AutoDataCollector
from services.finetune.reward_model import PreferenceCollector

credits = importlib.import_module('services.usage.credit_service')
graph_store = importlib.import_module('services.rag.graph_store')
feedback_store = support_feedback.FeedbackStore()
finetune_collector = AutoDataCollector()
preference_collector = PreferenceCollector()

print(json.dumps({
    'api_keys': api_keys._LOCAL_API_KEYS_FILE,
    'agent_db': agent_memory.DEFAULT_DB_PATH,
    'chroma_db': chroma_factory._resolve_path(None),
    'credits': credits._LOCAL_CREDITS_FILE,
    'feedback_data_dir': str(prompt_feedback._FEEDBACK_DIR),
    'feedback_store_dir': str(feedback_store.base_dir),
    'finetune_output_dir': finetune_collector.output_dir,
    'graph_store': graph_store._DEFAULT_STORE_PATH,
    'trials': trials._LOCAL_TRIALS_FILE,
    'preferences': preference_collector.storage_path,
    'subscriptions': subscriptions._LOCAL_SUBS_FILE,
    'referrals': referrals._LOCAL_REFERRALS_FILE,
    'rss': rss._SUBS_FILE,
    'share_page_dir': str(share_pages._DEFAULT_SHARE_DIR),
    'content_cache': content.CACHE_DIR,
    'ai_cache_db': config.AI_CACHE_DB,
    'content_backup_dir': str(backups.BACKUP_DIR),
    'user_memory': user_memory._DEFAULT_MEMORY_PATH,
}, sort_keys=True))
"""
    env = {
        **os.environ,
        'APP_DATA_DIR': str(app_data_dir),
        'APP_CACHE_DIR': str(tmp_path / 'app_cache'),
        'AI_CACHE_DB': '',
        'APP_DATA_BACKUP_DIR': str(tmp_path / 'app_backups'),
        'CONTENT_BACKUP_DIR': '',
        'AGENT_DB_PATH': '',
        'CHROMA_DB_PATH': '',
        'FEEDBACK_DATA_DIR': '',
        'FEEDBACK_STORE_DIR': '',
        'FINETUNE_OUTPUT_DIR': '',
        'GRAPH_STORE_PATH': '',
        'PREFERENCE_DATA_PATH': '',
        'SHARE_PAGE_DIR': '',
        'USER_MEMORY_PATH': '',
        'PYTHONPATH': str(ROOT),
    }
    result = subprocess.run(
        [sys.executable, '-c', script],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    paths = json.loads(result.stdout)
    for file_path in paths.values():
        path = Path(file_path)
        assert ROOT / 'services' not in path.parents

    for name, file_path in paths.items():
        path = Path(file_path)
        if name == 'content_cache':
            assert path == tmp_path / 'app_cache'
        elif name == 'ai_cache_db':
            assert path == tmp_path / 'app_cache' / 'ai_cache.db'
        elif name == 'content_backup_dir':
            assert path == tmp_path / 'app_backups' / 'content-library'
        elif name == 'agent_db':
            assert path == app_data_dir / 'agent_state.db'
        elif name == 'chroma_db':
            assert path == app_data_dir / 'chroma_db'
        elif name == 'feedback_data_dir':
            assert path == app_data_dir / 'feedback'
        elif name == 'feedback_store_dir':
            assert path == app_data_dir / 'feedback'
        elif name == 'finetune_output_dir':
            assert path == app_data_dir / 'finetune'
        elif name == 'graph_store':
            assert path == app_data_dir / 'graph_store'
        elif name == 'preferences':
            assert path == app_data_dir / 'preferences.jsonl'
        elif name == 'share_page_dir':
            assert path == app_data_dir / 'shared_pages'
        elif name == 'user_memory':
            assert path == app_data_dir / 'user_memory'
        else:
            assert path.parent == app_data_dir
