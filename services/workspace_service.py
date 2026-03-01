"""
워크스페이스 서비스
팀 협업을 위한 워크스페이스 CRUD 및 멤버 관리
"""
from services.supabase_service import get_supabase, is_supabase_enabled
from services.logging_config import ServiceLogger

logger = ServiceLogger('WorkspaceService')


def _db_operation(operation_name: str, default_return, operation_func):
    """DB 작업 공통 래퍼 (에러 핸들링 통합)"""
    try:
        return operation_func()
    except Exception as e:
        logger.error(f"{operation_name} 오류: {e}")
        return default_return


class WorkspaceService:
    """워크스페이스 CRUD 및 멤버 관리"""

    def create_workspace(self, name: str, owner_id: str) -> dict:
        """워크스페이스 생성 + owner를 멤버로 자동 추가"""
        if not is_supabase_enabled():
            return {'error': 'Supabase 연결이 필요합니다.'}

        supabase = get_supabase()
        if not supabase:
            return {'error': 'Supabase 클라이언트 초기화 실패'}

        def operation():
            # 워크스페이스 생성
            result = supabase.table('ie_workspaces').insert({
                'name': name,
                'owner_id': owner_id,
            }).execute()

            if not result.data:
                return {'error': '워크스페이스 생성 실패'}

            workspace = result.data[0]

            # owner를 멤버로 자동 추가
            supabase.table('ie_workspace_members').insert({
                'workspace_id': workspace['id'],
                'user_id': owner_id,
                'role': 'owner',
            }).execute()

            return workspace

        return _db_operation('Workspace create', {'error': '워크스페이스 생성 중 오류'}, operation)

    def list_workspaces(self, user_id: str) -> list:
        """사용자가 속한 워크스페이스 목록"""
        if not is_supabase_enabled():
            return []

        supabase = get_supabase()
        if not supabase:
            return []

        def operation():
            # 멤버 테이블에서 워크스페이스 ID 조회 후 워크스페이스 정보 가져오기
            members = supabase.table('ie_workspace_members') \
                .select('workspace_id, role') \
                .eq('user_id', user_id) \
                .execute()

            if not members.data:
                return []

            workspace_ids = [m['workspace_id'] for m in members.data]
            role_map = {m['workspace_id']: m['role'] for m in members.data}

            workspaces = supabase.table('ie_workspaces') \
                .select('*') \
                .in_('id', workspace_ids) \
                .order('created_at', desc=True) \
                .execute()

            # 역할 정보 추가
            result = []
            for ws in (workspaces.data or []):
                ws['my_role'] = role_map.get(ws['id'], 'viewer')
                result.append(ws)

            return result

        return _db_operation('Workspace list', [], operation)

    def get_workspace(self, workspace_id: str) -> dict | None:
        """워크스페이스 상세 조회"""
        if not is_supabase_enabled():
            return None

        supabase = get_supabase()
        if not supabase:
            return None

        def operation():
            result = supabase.table('ie_workspaces') \
                .select('*') \
                .eq('id', workspace_id) \
                .limit(1) \
                .execute()
            return result.data[0] if result.data else None

        return _db_operation('Workspace get', None, operation)

    def get_members(self, workspace_id: str) -> list:
        """워크스페이스 멤버 목록 (이메일 포함)"""
        if not is_supabase_enabled():
            return []

        supabase = get_supabase()
        if not supabase:
            return []

        def operation():
            result = supabase.table('ie_workspace_members') \
                .select('user_id, role, joined_at') \
                .eq('workspace_id', workspace_id) \
                .order('joined_at') \
                .execute()
            return result.data or []

        return _db_operation('Workspace members', [], operation)

    def invite_member(self, workspace_id: str, user_id: str, role: str = 'editor') -> dict:
        """멤버 초대"""
        if not is_supabase_enabled():
            return {'error': 'Supabase 연결이 필요합니다.'}

        if role not in ('editor', 'viewer'):
            return {'error': '유효하지 않은 역할입니다. (editor, viewer)'}

        supabase = get_supabase()
        if not supabase:
            return {'error': 'Supabase 클라이언트 초기화 실패'}

        def operation():
            # 이미 멤버인지 확인
            existing = supabase.table('ie_workspace_members') \
                .select('user_id') \
                .eq('workspace_id', workspace_id) \
                .eq('user_id', user_id) \
                .limit(1) \
                .execute()

            if existing.data:
                return {'error': '이미 워크스페이스 멤버입니다.'}

            result = supabase.table('ie_workspace_members').insert({
                'workspace_id': workspace_id,
                'user_id': user_id,
                'role': role,
            }).execute()

            return result.data[0] if result.data else {'error': '초대 실패'}

        return _db_operation('Member invite', {'error': '멤버 초대 중 오류'}, operation)

    def remove_member(self, workspace_id: str, user_id: str) -> bool:
        """멤버 제거 (owner는 제거 불가)"""
        if not is_supabase_enabled():
            return False

        supabase = get_supabase()
        if not supabase:
            return False

        def operation():
            # owner 제거 방지
            member = supabase.table('ie_workspace_members') \
                .select('role') \
                .eq('workspace_id', workspace_id) \
                .eq('user_id', user_id) \
                .limit(1) \
                .execute()

            if member.data and member.data[0].get('role') == 'owner':
                return False

            supabase.table('ie_workspace_members') \
                .delete() \
                .eq('workspace_id', workspace_id) \
                .eq('user_id', user_id) \
                .execute()
            return True

        return _db_operation('Member remove', False, operation)

    def update_role(self, workspace_id: str, user_id: str, new_role: str) -> bool:
        """멤버 역할 변경 (owner 역할로 변경 불가)"""
        if not is_supabase_enabled():
            return False

        if new_role not in ('editor', 'viewer'):
            return False

        supabase = get_supabase()
        if not supabase:
            return False

        def operation():
            # owner의 역할은 변경 불가
            member = supabase.table('ie_workspace_members') \
                .select('role') \
                .eq('workspace_id', workspace_id) \
                .eq('user_id', user_id) \
                .limit(1) \
                .execute()

            if member.data and member.data[0].get('role') == 'owner':
                return False

            supabase.table('ie_workspace_members') \
                .update({'role': new_role}) \
                .eq('workspace_id', workspace_id) \
                .eq('user_id', user_id) \
                .execute()
            return True

        return _db_operation('Role update', False, operation)

    def delete_workspace(self, workspace_id: str, owner_id: str) -> bool:
        """워크스페이스 삭제 (owner만 가능)"""
        if not is_supabase_enabled():
            return False

        supabase = get_supabase()
        if not supabase:
            return False

        def operation():
            # owner 확인
            ws = supabase.table('ie_workspaces') \
                .select('owner_id') \
                .eq('id', workspace_id) \
                .limit(1) \
                .execute()

            if not ws.data or ws.data[0].get('owner_id') != owner_id:
                return False

            # CASCADE로 멤버도 자동 삭제
            supabase.table('ie_workspaces') \
                .delete() \
                .eq('id', workspace_id) \
                .execute()
            return True

        return _db_operation('Workspace delete', False, operation)

    def find_user_by_email(self, email: str) -> str | None:
        """이메일로 사용자 ID 조회 (admin 클라이언트 필요)"""
        from services.supabase_service import _get_admin_client

        admin = _get_admin_client()
        if not admin:
            return None

        try:
            # admin API로 이메일 검색
            users = admin.auth.admin.list_users()
            for user in users:
                if user.email == email:
                    return user.id
            return None
        except Exception as e:
            logger.error(f"사용자 이메일 조회 실패: {e}")
            return None


# 싱글톤 인스턴스
workspace_service = WorkspaceService()
