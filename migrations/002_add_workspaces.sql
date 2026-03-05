-- Insight Engine DB 마이그레이션 002: 워크스페이스 스키마 (F9-03)
-- 실행: psql $DATABASE_URL -f migrations/002_add_workspaces.sql

-- 워크스페이스 테이블
CREATE TABLE IF NOT EXISTS ie_workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    owner_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    plan VARCHAR(20) DEFAULT 'free',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 워크스페이스 멤버 테이블
CREATE TABLE IF NOT EXISTS ie_workspace_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES ie_workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL DEFAULT 'viewer', -- owner/editor/viewer
    invited_by UUID REFERENCES auth.users(id),
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(workspace_id, user_id)
);

-- API 키 테이블
CREATE TABLE IF NOT EXISTS ie_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    key_hash VARCHAR(64) NOT NULL UNIQUE,
    label VARCHAR(100),
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

-- 커스텀 스타일 테이블
CREATE TABLE IF NOT EXISTS ie_custom_styles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    style_id VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    prompt TEXT NOT NULL,
    is_public BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, style_id)
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_ie_workspace_members_workspace ON ie_workspace_members(workspace_id);
CREATE INDEX IF NOT EXISTS idx_ie_workspace_members_user ON ie_workspace_members(user_id);
CREATE INDEX IF NOT EXISTS idx_ie_api_keys_user ON ie_api_keys(user_id);

INSERT INTO ie_migrations (version, name) VALUES ('002', 'add_workspaces')
ON CONFLICT (version) DO NOTHING;
