"""
산출물 워크스페이스 서비스 테스트
"""

import unittest
import time

from services.artifact_workspace_service import (
    ArtifactWorkspaceService,
    Workspace,
    Artifact,
    VALID_ARTIFACT_TYPES,
)


class TestCreateWorkspace(unittest.TestCase):
    """create_workspace 테스트"""

    def setUp(self):
        self.svc = ArtifactWorkspaceService()

    def test_기본_워크스페이스_생성(self):
        """워크스페이스가 올바르게 생성되어야 한다"""
        ws = self.svc.create_workspace("sess_1", "내 워크스페이스")
        self.assertIsInstance(ws, Workspace)
        self.assertTrue(ws.workspace_id.startswith("ws_"))
        self.assertEqual(ws.session_id, "sess_1")
        self.assertEqual(ws.name, "내 워크스페이스")
        self.assertEqual(ws.artifacts, [])

    def test_이름_미지정시_자동생성(self):
        """name이 비어있으면 자동 생성"""
        ws = self.svc.create_workspace("sess_1")
        self.assertTrue(ws.name.startswith("Workspace-"))

    def test_빈_session_id_거부(self):
        """빈 session_id는 ValueError"""
        with self.assertRaises(ValueError):
            self.svc.create_workspace("")

    def test_공백_session_id_거부(self):
        """공백만 있는 session_id는 ValueError"""
        with self.assertRaises(ValueError):
            self.svc.create_workspace("   ")

    def test_고유_workspace_id(self):
        """각 워크스페이스는 고유 ID를 가져야 한다"""
        w1 = self.svc.create_workspace("sess_1")
        w2 = self.svc.create_workspace("sess_1")
        self.assertNotEqual(w1.workspace_id, w2.workspace_id)

    def test_created_at_자동설정(self):
        """created_at이 현재 시간 근처여야 한다"""
        before = time.time()
        ws = self.svc.create_workspace("sess_1")
        after = time.time()
        self.assertGreaterEqual(ws.created_at, before)
        self.assertLessEqual(ws.created_at, after)


class TestAddArtifact(unittest.TestCase):
    """add_artifact 테스트"""

    def setUp(self):
        self.svc = ArtifactWorkspaceService()
        self.ws = self.svc.create_workspace("sess_1", "테스트")

    def test_텍스트_산출물_추가(self):
        """text 타입 산출물 추가"""
        art = self.svc.add_artifact(self.ws.workspace_id, "text", "안녕하세요")
        self.assertIsInstance(art, Artifact)
        self.assertTrue(art.artifact_id.startswith("art_"))
        self.assertEqual(art.artifact_type, "text")
        self.assertEqual(art.content, "안녕하세요")
        self.assertEqual(art.metadata, {})

    def test_모든_허용_타입(self):
        """5가지 허용 타입 모두 성공"""
        for atype in VALID_ARTIFACT_TYPES:
            art = self.svc.add_artifact(self.ws.workspace_id, atype, "content")
            self.assertEqual(art.artifact_type, atype)

    def test_잘못된_타입_거부(self):
        """허용되지 않은 타입은 ValueError"""
        with self.assertRaises(ValueError) as ctx:
            self.svc.add_artifact(self.ws.workspace_id, "video", "content")
        self.assertIn("잘못된 산출물 타입", str(ctx.exception))

    def test_존재하지_않는_워크스페이스(self):
        """없는 workspace_id는 KeyError"""
        with self.assertRaises(KeyError):
            self.svc.add_artifact("nonexistent", "text", "content")

    def test_metadata_전달(self):
        """metadata가 올바르게 저장"""
        meta = {"author": "테스트", "version": 1}
        art = self.svc.add_artifact(
            self.ws.workspace_id, "json", '{"key": "val"}', metadata=meta
        )
        self.assertEqual(art.metadata, meta)

    def test_워크스페이스에_산출물_누적(self):
        """같은 워크스페이스에 여러 산출물 추가"""
        self.svc.add_artifact(self.ws.workspace_id, "text", "첫 번째")
        self.svc.add_artifact(self.ws.workspace_id, "html", "<p>두 번째</p>")
        ws = self.svc.get_workspace(self.ws.workspace_id)
        self.assertEqual(len(ws.artifacts), 2)


class TestGetWorkspace(unittest.TestCase):
    """get_workspace 테스트"""

    def setUp(self):
        self.svc = ArtifactWorkspaceService()

    def test_정상_조회(self):
        """생성한 워크스페이스를 ID로 조회"""
        ws = self.svc.create_workspace("sess_1", "테스트")
        fetched = self.svc.get_workspace(ws.workspace_id)
        self.assertEqual(fetched.workspace_id, ws.workspace_id)
        self.assertEqual(fetched.name, "테스트")

    def test_존재하지_않는_워크스페이스(self):
        """없는 ID는 KeyError"""
        with self.assertRaises(KeyError):
            self.svc.get_workspace("nonexistent")


class TestListWorkspaces(unittest.TestCase):
    """list_workspaces 테스트"""

    def setUp(self):
        self.svc = ArtifactWorkspaceService()

    def test_빈_목록(self):
        """워크스페이스가 없으면 빈 리스트"""
        self.assertEqual(self.svc.list_workspaces(), [])

    def test_session_id_필터(self):
        """특정 session_id만 필터링"""
        self.svc.create_workspace("sess_1", "A")
        self.svc.create_workspace("sess_2", "B")
        self.svc.create_workspace("sess_1", "C")
        result = self.svc.list_workspaces(session_id="sess_1")
        self.assertEqual(len(result), 2)
        for ws in result:
            self.assertEqual(ws.session_id, "sess_1")

    def test_session_id_None이면_전체(self):
        """session_id=None이면 모든 워크스페이스"""
        self.svc.create_workspace("sess_1")
        self.svc.create_workspace("sess_2")
        result = self.svc.list_workspaces(session_id=None)
        self.assertEqual(len(result), 2)

    def test_생성_시간순_정렬(self):
        """created_at 오름차순 정렬"""
        w1 = self.svc.create_workspace("sess_1", "First")
        w2 = self.svc.create_workspace("sess_1", "Second")
        result = self.svc.list_workspaces()
        self.assertEqual(result[0].name, "First")
        self.assertEqual(result[1].name, "Second")


if __name__ == "__main__":
    unittest.main()
