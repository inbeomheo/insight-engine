"""백업/복원 + 데이터 가져오기/내보내기 라우트 (F8-22 / F8-23).

content_mgmt_routes.py에서 분리됨.
"""
from flask import Response, current_app, request

from routes.content_mgmt._shared import _err, _get_json, _json
from routes.content_mgmt_routes import content_mgmt_bp
from services.data import backup_service, data_migration_service
from src.contexts.identity.interface.auth_decorators import require_auth


# ══════════════════════════════════════════════════════════════════
# F8-22 백업/복원
# ══════════════════════════════════════════════════════════════════

@content_mgmt_bp.route('/backup', methods=['POST'])
@require_auth
def create_backup():
    """수동 백업을 생성합니다."""
    data = _get_json()
    try:
        result = backup_service.create_backup(
            workspace_id=data.get('workspace_id', ''),
            user_id=data.get('user_id', ''),
            triggered_by='manual',
        )
    except Exception as e:
        current_app.logger.error('Backup creation failed: %s', e, exc_info=True)
        return _err('[서버 오류] 백업 생성 중 문제가 발생했습니다.', 500)
    return _json(result, 201)


@content_mgmt_bp.route('/backup', methods=['GET'])
@require_auth
def list_backups():
    """백업 목록 조회."""
    try:
        backups = backup_service.list_backups()
    except Exception as e:
        current_app.logger.error('Backup list failed: %s', e, exc_info=True)
        return _err('[서버 오류] 백업 목록 조회 중 문제가 발생했습니다.', 500)
    return _json({'backups': backups})


@content_mgmt_bp.route('/backup/<filename>/restore', methods=['POST'])
@require_auth
def restore_backup(filename):
    """백업을 복원합니다."""
    try:
        result = backup_service.restore_backup(filename)
        return _json(result)
    except ValueError as e:
        current_app.logger.warning('Invalid backup filename: %s', e)
        return _err('잘못된 백업 파일명입니다.', 400)
    except FileNotFoundError as e:
        current_app.logger.warning('Backup file not found: %s', e)
        return _err('백업 파일을 찾을 수 없습니다.', 404)
    except Exception as e:
        current_app.logger.error('Backup restore failed: %s', e, exc_info=True)
        return _err('[서버 오류] 백업 복원 중 문제가 발생했습니다.', 500)


# ══════════════════════════════════════════════════════════════════
# F8-23 데이터 가져오기/내보내기
# ══════════════════════════════════════════════════════════════════

@content_mgmt_bp.route('/export/<fmt>', methods=['GET'])
@require_auth
def export_content(fmt):
    """콘텐츠를 JSON/CSV/Markdown으로 내보냅니다."""
    args = request.args
    workspace_id = args.get('workspace_id', '')
    user_id = args.get('user_id', '')

    try:
        if fmt == 'json':
            data = data_migration_service.export_json(workspace_id, user_id)
            return Response(data, content_type='application/json; charset=utf-8',
                            headers={'Content-Disposition': 'attachment; filename="export.json"'})
        elif fmt == 'csv':
            data = data_migration_service.export_csv(workspace_id, user_id)
            return Response(data, content_type='text/csv; charset=utf-8',
                            headers={'Content-Disposition': 'attachment; filename="export.csv"'})
        elif fmt == 'markdown':
            data = data_migration_service.export_markdown(workspace_id, user_id)
            return Response(data, content_type='text/markdown; charset=utf-8',
                            headers={'Content-Disposition': 'attachment; filename="export.md"'})
        else:
            return _err(f'지원하지 않는 형식: {fmt}. json/csv/markdown 중 선택하세요.')
    except Exception as e:
        current_app.logger.error('Content export failed: format=%s error=%s', fmt, e, exc_info=True)
        return _err('[서버 오류] 콘텐츠 내보내기 중 문제가 발생했습니다.', 500)


@content_mgmt_bp.route('/import/<fmt>', methods=['POST'])
@require_auth
def import_content(fmt):
    """JSON/CSV 형식으로 콘텐츠를 가져옵니다."""
    data = _get_json()
    workspace_id = data.get('workspace_id', '')
    user_id = data.get('user_id', '')
    content_str = data.get('content', '')

    try:
        if fmt == 'json':
            result = data_migration_service.import_json(
                content_str, workspace_id, user_id, overwrite=bool(data.get('overwrite', False))
            )
        elif fmt == 'csv':
            result = data_migration_service.import_csv(content_str, workspace_id, user_id)
        else:
            return _err(f'지원하지 않는 형식: {fmt}')
    except Exception as e:
        current_app.logger.error('Content import failed: format=%s error=%s', fmt, e, exc_info=True)
        return _err('[서버 오류] 콘텐츠 가져오기 중 문제가 발생했습니다.', 500)

    return _json(result)
