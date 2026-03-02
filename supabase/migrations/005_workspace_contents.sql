-- 워크스페이스 콘텐츠 승인 흐름 테이블
CREATE TABLE IF NOT EXISTS ie_workspace_contents (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    workspace_id UUID NOT NULL REFERENCES ie_workspaces(id) ON DELETE CASCADE,
    content_id TEXT NOT NULL,  -- 생성 결과 ID (ie_histories.report_id 참조)
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'review', 'approved', 'published', 'rejected')),
    author_id UUID NOT NULL,
    reviewer_id UUID,
    review_note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS 활성화
ALTER TABLE ie_workspace_contents ENABLE ROW LEVEL SECURITY;

-- 워크스페이스 멤버만 조회 가능
CREATE POLICY "workspace_contents_select" ON ie_workspace_contents
    FOR SELECT USING (
        workspace_id IN (
            SELECT workspace_id FROM ie_workspace_members WHERE user_id = auth.uid()
        )
    );

-- 본인만 삽입 가능
CREATE POLICY "workspace_contents_insert" ON ie_workspace_contents
    FOR INSERT WITH CHECK (author_id = auth.uid());

-- owner/editor만 수정 가능
CREATE POLICY "workspace_contents_update" ON ie_workspace_contents
    FOR UPDATE USING (
        workspace_id IN (
            SELECT workspace_id FROM ie_workspace_members
            WHERE user_id = auth.uid() AND role IN ('owner', 'editor')
        )
    );
