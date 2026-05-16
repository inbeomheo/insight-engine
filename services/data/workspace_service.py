"""
워크스페이스 서비스
팀 협업을 위한 워크스페이스 CRUD 및 멤버 관리
"""
from services.data.supabase_service import get_supabase, is_supabase_enabled
from services.core.logging_config import ServiceLogger
import logging

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

    def is_member(self, workspace_id: str, user_id: str) -> bool:
        """사용자가 해당 워크스페이스의 멤버인지 확인"""
        if not is_supabase_enabled():
            return False

        supabase = get_supabase()
        if not supabase:
            return False

        def operation():
            result = supabase.table('ie_workspace_members') \
                .select('user_id') \
                .eq('workspace_id', workspace_id) \
                .eq('user_id', user_id) \
                .limit(1) \
                .execute()
            return bool(result.data)

        return _db_operation('Membership check', False, operation)

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
        """이메일로 사용자 ID 조회 (ie_usage 테이블에서 직접 검색)"""
        if not is_supabase_enabled():
            return None

        supabase = get_supabase()
        if not supabase:
            return None

        try:
            # ie_usage 테이블에서 이메일로 직접 조회 (전체 로드 방지)
            result = supabase.table('ie_usage').select('user_id').eq('email', email).limit(1).execute()
            if result.data:
                return result.data[0]['user_id']
        except Exception:
            pass

        # 폴백: admin API로 조회
        try:
            from services.data.supabase_service import _get_admin_client
            admin = _get_admin_client()
            if not admin:
                return None
            users = admin.auth.admin.list_users()
            for user in users:
                if user.email == email:
                    return user.id
        except Exception as e:
            logger.error(f"사용자 이메일 조회 실패: {e}")

        return None


# =============================================
# 콘텐츠 승인 흐름
# =============================================

# 콘텐츠 상태 전이 규칙
CONTENT_STATES = ['draft', 'review', 'approved', 'published', 'rejected']
VALID_TRANSITIONS = {
    'draft': ['review'],
    'review': ['approved', 'rejected'],
    'approved': ['published', 'draft'],  # draft로 되돌리기 가능
    'rejected': ['draft'],  # 작성자가 재편집 가능
    'published': [],
}


class ContentApprovalService:
    """워크스페이스 콘텐츠 승인 흐름 관리"""

    def _get_content(self, content_id: str) -> dict | None:
        """콘텐츠 단건 조회"""
        supabase = get_supabase()
        if not supabase:
            return None

        result = supabase.table('ie_workspace_contents') \
            .select('*') \
            .eq('id', content_id) \
            .limit(1) \
            .execute()
        return result.data[0] if result.data else None

    def _get_member_role(self, workspace_id: str, user_id: str) -> str | None:
        """워크스페이스에서 사용자의 역할 조회"""
        supabase = get_supabase()
        if not supabase:
            return None

        result = supabase.table('ie_workspace_members') \
            .select('role') \
            .eq('workspace_id', workspace_id) \
            .eq('user_id', user_id) \
            .limit(1) \
            .execute()
        return result.data[0]['role'] if result.data else None

    def _transition(self, content_id: str, user_id: str, target_status: str,
                    required_roles: list[str], extra_fields: dict | None = None) -> dict:
        """상태 전이 공통 로직"""
        if not is_supabase_enabled():
            return {'error': 'Supabase 연결이 필요합니다.'}

        content = self._get_content(content_id)
        if not content:
            return {'error': '콘텐츠를 찾을 수 없습니다.'}

        current = content['status']
        if target_status not in VALID_TRANSITIONS.get(current, []):
            return {'error': f"'{current}' 상태에서 '{target_status}'(으)로 전환할 수 없습니다."}

        # 역할 검증
        role = self._get_member_role(content['workspace_id'], user_id)
        if not role or role not in required_roles:
            return {'error': '이 작업을 수행할 권한이 없습니다.'}

        supabase = get_supabase()
        update_data = {'status': target_status, 'updated_at': 'now()'}
        if extra_fields:
            update_data.update(extra_fields)

        def operation():
            result = supabase.table('ie_workspace_contents') \
                .update(update_data) \
                .eq('id', content_id) \
                .execute()
            return result.data[0] if result.data else {'error': '상태 변경에 실패했습니다.'}

        return _db_operation('Content transition', {'error': '상태 변경 중 오류'}, operation)

    def add_content(self, workspace_id: str, user_id: str, content_id: str, title: str) -> dict:
        """워크스페이스에 콘텐츠 추가 (draft 상태)"""
        if not is_supabase_enabled():
            return {'error': 'Supabase 연결이 필요합니다.'}

        role = self._get_member_role(workspace_id, user_id)
        if not role or role not in ('owner', 'editor'):
            return {'error': '콘텐츠를 추가할 권한이 없습니다.'}

        supabase = get_supabase()
        if not supabase:
            return {'error': 'Supabase 클라이언트 초기화 실패'}

        def operation():
            result = supabase.table('ie_workspace_contents').insert({
                'workspace_id': workspace_id,
                'content_id': content_id,
                'title': title,
                'status': 'draft',
                'author_id': user_id,
            }).execute()
            return result.data[0] if result.data else {'error': '콘텐츠 추가 실패'}

        return _db_operation('Content add', {'error': '콘텐츠 추가 중 오류'}, operation)

    def submit_for_review(self, content_id: str, user_id: str) -> dict:
        """draft → review (editor 이상)"""
        return self._transition(content_id, user_id, 'review',
                                required_roles=['owner', 'editor'])

    def approve_content(self, content_id: str, reviewer_id: str) -> dict:
        """review → approved (owner만)"""
        return self._transition(content_id, reviewer_id, 'approved',
                                required_roles=['owner'],
                                extra_fields={'reviewer_id': reviewer_id})

    def reject_content(self, content_id: str, reviewer_id: str, reason: str) -> dict:
        """review → rejected (owner만)"""
        return self._transition(content_id, reviewer_id, 'rejected',
                                required_roles=['owner'],
                                extra_fields={'reviewer_id': reviewer_id, 'review_note': reason})

    def publish_content(self, content_id: str, user_id: str) -> dict:
        """approved → published (owner만)"""
        try:
            return self._transition(content_id, user_id, 'published',
                                    required_roles=['owner'])
        except Exception as e:
            logger.error("publish_content 실패: %s", e, exc_info=True)
            return {}

    def revert_to_draft(self, content_id: str, user_id: str) -> dict:
        """approved/rejected → draft (editor 이상)"""
        try:
            return self._transition(content_id, user_id, 'draft',
                                    required_roles=['owner', 'editor'],
                                    extra_fields={'reviewer_id': None, 'review_note': None})
        except Exception as e:
            logger.error("revert_to_draft 실패: %s", e, exc_info=True)
            return {}

    def get_workspace_contents(self, workspace_id: str, status: str = None) -> list:
        """워크스페이스 콘텐츠 목록 (상태 필터 선택)"""
        if not is_supabase_enabled():
            return []

        try:
            supabase = get_supabase()
            if not supabase:
                return []

            def operation():
                query = supabase.table('ie_workspace_contents') \
                    .select('*') \
                    .eq('workspace_id', workspace_id) \
                    .order('updated_at', desc=True)

                if status and status in CONTENT_STATES:
                    query = query.eq('status', status)

                result = query.execute()
                return result.data or []

            return _db_operation('Contents list', [], operation)
        except Exception as e:
            logger.error("get_workspace_contents 실패: %s", e, exc_info=True)
            return []


# 싱글톤 인스턴스
workspace_service = WorkspaceService()
content_approval_service = ContentApprovalService()
