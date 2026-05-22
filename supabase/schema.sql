-- =============================================
-- Insight Engine - Supabase Schema (v2)
-- =============================================
-- Supabase Dashboard > SQL Editor에서 실행하세요
-- 테이블명: ie_ 접두사 (Insight Engine)

-- =============================================
-- 1. 테이블 생성
-- =============================================

-- 1-1. 사용량 테이블 (일일 제한)
CREATE TABLE IF NOT EXISTS ie_usage (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
    usage_count INT DEFAULT 20,  -- 남은 사용 횟수 (기본 20회)
    last_reset_date DATE DEFAULT CURRENT_DATE,  -- 마지막 리셋 날짜
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 1-2. 분석 히스토리 테이블
CREATE TABLE IF NOT EXISTS ie_histories (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    report_id TEXT NOT NULL,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    style TEXT NOT NULL,
    content TEXT,
    html TEXT,
    mindmap_markdown TEXT,
    transcript_preview TEXT,  -- 자막 미리보기 (500자)
    usage JSONB,
    elapsed_time FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 1-3. API 키 저장 테이블 (사용자 설정 패널 — provider별 컬럼, 사용자당 1행)
CREATE TABLE IF NOT EXISTS ie_api_keys (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
    openai_key TEXT,
    anthropic_key TEXT,
    google_key TEXT,
    zhipu_key TEXT,
    deepseek_key TEXT,
    supadata_key TEXT,
    selected_provider TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 1-3b. 사용자 API 키 (다중 행 — 통합 스키마 v3)
-- 두 도메인을 한 테이블에 공존:
--   (a) IE 자체 발급 토큰 (services/data/api_key_service.py)
--       — Authorization Bearer로 외부에서 IE API 호출용. (name, key_hash, key_prefix)
--   (b) 외부 LLM BYO 키 (src/contexts/identity/.../supabase_api_key_vault.py)
--       — 콘텐츠 생성 시 사용자 자기 키로 호출. (provider, label, encrypted_key)
-- 한 행은 둘 중 하나만 채움 (CHECK 제약).
CREATE TABLE IF NOT EXISTS ie_user_api_keys (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- (a) IE 자체 발급 토큰 컬럼
    name TEXT,
    key_hash TEXT,
    key_prefix TEXT,
    usage_count INT NOT NULL DEFAULT 0,
    last_used_at TIMESTAMPTZ,

    -- (b) 외부 LLM BYO 키 컬럼
    provider TEXT,
    label TEXT,
    encrypted_key TEXT,

    -- 공통
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- 한 행은 두 도메인 중 하나에 속해야 한다
    CONSTRAINT ie_user_api_keys_row_kind CHECK (
        key_hash IS NOT NULL OR encrypted_key IS NOT NULL
    )
);

-- 1-4. 커스텀 스타일 테이블
CREATE TABLE IF NOT EXISTS ie_custom_styles (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    style_id TEXT NOT NULL,
    name TEXT NOT NULL,
    icon TEXT DEFAULT 'edit_note',
    prompt TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, style_id)
);

-- 1-5. 관리자 테이블
CREATE TABLE IF NOT EXISTS ie_admins (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================
-- 2. 뷰 생성 (이메일 조인)
-- =============================================

-- 2-1. 사용량 + 이메일 뷰 (관리자용)
CREATE OR REPLACE VIEW ie_usage_with_email AS
SELECT
    u.id,
    u.user_id,
    u.usage_count,
    u.last_reset_date,
    u.created_at,
    u.updated_at,
    au.email
FROM ie_usage u
LEFT JOIN auth.users au ON u.user_id = au.id;

-- 2-2. 히스토리 + 이메일 뷰 (관리자용)
CREATE OR REPLACE VIEW ie_histories_with_email AS
SELECT
    h.id,
    h.user_id,
    h.report_id,
    h.url,
    h.title,
    h.style,
    h.content,
    h.html,
    h.mindmap_markdown,
    h.transcript_preview,
    h.usage,
    h.elapsed_time,
    h.created_at,
    h.updated_at,
    au.email
FROM ie_histories h
LEFT JOIN auth.users au ON h.user_id = au.id;

-- =============================================
-- 3. Row Level Security (RLS) 정책
-- =============================================

-- ie_usage 테이블 RLS
ALTER TABLE ie_usage ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own usage"
    ON ie_usage FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own usage"
    ON ie_usage FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own usage"
    ON ie_usage FOR UPDATE
    USING (auth.uid() = user_id);

-- ie_histories 테이블 RLS
ALTER TABLE ie_histories ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own histories"
    ON ie_histories FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own histories"
    ON ie_histories FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own histories"
    ON ie_histories FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own histories"
    ON ie_histories FOR DELETE
    USING (auth.uid() = user_id);

-- ie_api_keys 테이블 RLS
ALTER TABLE ie_api_keys ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own api_keys"
    ON ie_api_keys FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own api_keys"
    ON ie_api_keys FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own api_keys"
    ON ie_api_keys FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own api_keys"
    ON ie_api_keys FOR DELETE
    USING (auth.uid() = user_id);

-- ie_user_api_keys 테이블 RLS (다중 행 통합 테이블)
ALTER TABLE ie_user_api_keys ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own user_api_keys"
    ON ie_user_api_keys FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own user_api_keys"
    ON ie_user_api_keys FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own user_api_keys"
    ON ie_user_api_keys FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own user_api_keys"
    ON ie_user_api_keys FOR DELETE
    USING (auth.uid() = user_id);

-- ie_custom_styles 테이블 RLS
ALTER TABLE ie_custom_styles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own custom_styles"
    ON ie_custom_styles FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own custom_styles"
    ON ie_custom_styles FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own custom_styles"
    ON ie_custom_styles FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own custom_styles"
    ON ie_custom_styles FOR DELETE
    USING (auth.uid() = user_id);

-- ie_admins 테이블 RLS
ALTER TABLE ie_admins ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Only service role can manage admins"
    ON ie_admins FOR ALL
    USING (false);  -- 일반 사용자 접근 불가, service_role만 가능

-- =============================================
-- 4. 인덱스
-- =============================================

CREATE INDEX IF NOT EXISTS idx_ie_usage_user_id ON ie_usage(user_id);
CREATE INDEX IF NOT EXISTS idx_ie_histories_user_id ON ie_histories(user_id);
CREATE INDEX IF NOT EXISTS idx_ie_histories_created_at ON ie_histories(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ie_custom_styles_user_id ON ie_custom_styles(user_id);

-- ie_user_api_keys 인덱스
-- IE 토큰 검증(key_hash 역조회) 가속 — 활성 토큰만 인덱싱
CREATE INDEX IF NOT EXISTS idx_ie_user_api_keys_hash
    ON ie_user_api_keys(key_hash)
    WHERE key_hash IS NOT NULL AND is_active = true;
-- 사용자별 목록 조회
CREATE INDEX IF NOT EXISTS idx_ie_user_api_keys_user
    ON ie_user_api_keys(user_id, is_active);
-- BYO 키 upsert용 partial unique — 같은 (user, provider, label) 조합은 한 행만
CREATE UNIQUE INDEX IF NOT EXISTS uq_ie_user_api_keys_provider
    ON ie_user_api_keys(user_id, provider, label)
    WHERE provider IS NOT NULL;

-- =============================================
-- 5. 트리거: updated_at 자동 업데이트
-- =============================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 기존 트리거가 있으면 삭제
DROP TRIGGER IF EXISTS ie_usage_updated_at ON ie_usage;
DROP TRIGGER IF EXISTS ie_histories_updated_at ON ie_histories;
DROP TRIGGER IF EXISTS ie_api_keys_updated_at ON ie_api_keys;
DROP TRIGGER IF EXISTS ie_user_api_keys_updated_at ON ie_user_api_keys;
DROP TRIGGER IF EXISTS ie_custom_styles_updated_at ON ie_custom_styles;

-- 트리거 생성
CREATE TRIGGER ie_usage_updated_at
    BEFORE UPDATE ON ie_usage
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER ie_histories_updated_at
    BEFORE UPDATE ON ie_histories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER ie_api_keys_updated_at
    BEFORE UPDATE ON ie_api_keys
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER ie_user_api_keys_updated_at
    BEFORE UPDATE ON ie_user_api_keys
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER ie_custom_styles_updated_at
    BEFORE UPDATE ON ie_custom_styles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- =============================================
-- 6. RPC 함수: 원자적 사용량 차감
-- =============================================

DROP FUNCTION IF EXISTS decrement_usage_safe(UUID);

CREATE OR REPLACE FUNCTION decrement_usage_safe(p_user_id UUID)
RETURNS JSON
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_new_count INT;
BEGIN
    -- 원자적 UPDATE: usage_count > 0인 경우에만 차감
    UPDATE ie_usage
    SET usage_count = usage_count - 1,
        updated_at = NOW()
    WHERE user_id = p_user_id
      AND usage_count > 0
    RETURNING usage_count INTO v_new_count;

    IF FOUND THEN
        RETURN json_build_object(
            'success', true,
            'new_count', v_new_count
        );
    ELSE
        RETURN json_build_object(
            'success', false,
            'reason', 'no_usage_left'
        );
    END IF;
END;
$$ LANGUAGE plpgsql;

GRANT EXECUTE ON FUNCTION decrement_usage_safe(UUID) TO authenticated;

-- =============================================
-- 7. RPC 함수: 일일 사용량 리셋 (선택)
-- =============================================

CREATE OR REPLACE FUNCTION reset_daily_usage()
RETURNS INT
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_count INT;
BEGIN
    UPDATE ie_usage
    SET usage_count = 20,
        last_reset_date = CURRENT_DATE,
        updated_at = NOW()
    WHERE last_reset_date < CURRENT_DATE;

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

-- =============================================
-- 8. RPC 함수: 만료 히스토리 자동 삭제 (7일 보존)
-- =============================================

CREATE OR REPLACE FUNCTION cleanup_expired_histories()
RETURNS INT
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_count INT;
BEGIN
    DELETE FROM ie_histories
    WHERE created_at < NOW() - INTERVAL '7 days';

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

-- pg_cron 스케줄 등록 (Supabase Dashboard > Database > Extensions에서 pg_cron 활성화 필요)
-- 매일 새벽 3시(UTC)에 실행:
-- SELECT cron.schedule('cleanup-expired-histories', '0 3 * * *', $$SELECT cleanup_expired_histories()$$);

-- =============================================
-- 9. 마이그레이션: 즐겨찾기 컬럼 추가
-- =============================================

ALTER TABLE ie_histories ADD COLUMN IF NOT EXISTS is_favorite BOOLEAN DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS idx_ie_histories_favorite ON ie_histories(user_id, is_favorite) WHERE is_favorite = TRUE;

-- =============================================
-- 10. 마이그레이션: 키워드 컬럼 추가
-- =============================================

ALTER TABLE ie_histories ADD COLUMN IF NOT EXISTS keywords JSONB DEFAULT '[]'::jsonb;

-- =============================================
-- 11. 예약 발행 테이블
-- =============================================

CREATE TABLE IF NOT EXISTS ie_scheduled_posts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    html TEXT,
    target_plugin TEXT NOT NULL,
    scheduled_at TIMESTAMPTZ NOT NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'published', 'failed', 'cancelled')),
    error_message TEXT,
    published_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scheduled_posts_user ON ie_scheduled_posts(user_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_status ON ie_scheduled_posts(status, scheduled_at);

-- RLS
ALTER TABLE ie_scheduled_posts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own scheduled_posts"
    ON ie_scheduled_posts FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own scheduled_posts"
    ON ie_scheduled_posts FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own scheduled_posts"
    ON ie_scheduled_posts FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own scheduled_posts"
    ON ie_scheduled_posts FOR DELETE
    USING (auth.uid() = user_id);

-- =============================================
-- 12. 워크스페이스 테이블
-- =============================================

CREATE TABLE IF NOT EXISTS ie_workspaces (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL,
    owner_id UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 워크스페이스 멤버
CREATE TABLE IF NOT EXISTS ie_workspace_members (
    workspace_id UUID REFERENCES ie_workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('owner', 'editor', 'viewer')),
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (workspace_id, user_id)
);

-- ie_histories에 workspace_id 추가 (기존 데이터 호환)
ALTER TABLE ie_histories ADD COLUMN IF NOT EXISTS workspace_id UUID REFERENCES ie_workspaces(id);
CREATE INDEX IF NOT EXISTS idx_histories_workspace ON ie_histories(workspace_id);

-- =============================================
-- 13. 워크스페이스 RLS
-- =============================================

ALTER TABLE ie_workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE ie_workspace_members ENABLE ROW LEVEL SECURITY;

-- 워크스페이스: 멤버만 읽기 가능
CREATE POLICY workspace_member_read ON ie_workspaces FOR SELECT
    USING (id IN (SELECT workspace_id FROM ie_workspace_members WHERE user_id = auth.uid()));

-- 워크스페이스: owner만 쓰기 가능
CREATE POLICY workspace_owner_write ON ie_workspaces FOR ALL
    USING (owner_id = auth.uid());

-- 멤버: 같은 워크스페이스 멤버만 읽기 가능
CREATE POLICY member_read ON ie_workspace_members FOR SELECT
    USING (workspace_id IN (SELECT workspace_id FROM ie_workspace_members WHERE user_id = auth.uid()));

-- 멤버: owner만 관리 가능
CREATE POLICY member_manage ON ie_workspace_members FOR ALL
    USING (workspace_id IN (SELECT id FROM ie_workspaces WHERE owner_id = auth.uid()));

-- =============================================
-- 14. 프롬프트 템플릿 갤러리 테이블
-- =============================================

CREATE TABLE IF NOT EXISTS ie_prompt_templates (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    prompt_text TEXT NOT NULL,
    style_base TEXT DEFAULT 'blog_seo',  -- 기반 스타일
    is_public BOOLEAN DEFAULT false,     -- 공개 여부 (true면 전체 사용자에게 노출)
    usage_count INTEGER DEFAULT 0,       -- 사용 횟수
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_prompt_templates_user_id ON ie_prompt_templates(user_id);
CREATE INDEX IF NOT EXISTS idx_prompt_templates_public ON ie_prompt_templates(is_public) WHERE is_public = TRUE;
CREATE INDEX IF NOT EXISTS idx_prompt_templates_created_at ON ie_prompt_templates(created_at DESC);

-- RLS
ALTER TABLE ie_prompt_templates ENABLE ROW LEVEL SECURITY;

-- 공개 템플릿은 모든 사용자가 읽기 가능, 본인 템플릿도 읽기 가능
CREATE POLICY "Users can view public or own templates"
    ON ie_prompt_templates FOR SELECT
    USING (is_public = TRUE OR auth.uid() = user_id);

CREATE POLICY "Users can insert own templates"
    ON ie_prompt_templates FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own templates"
    ON ie_prompt_templates FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own templates"
    ON ie_prompt_templates FOR DELETE
    USING (auth.uid() = user_id);

-- updated_at 트리거
DROP TRIGGER IF EXISTS ie_prompt_templates_updated_at ON ie_prompt_templates;
CREATE TRIGGER ie_prompt_templates_updated_at
    BEFORE UPDATE ON ie_prompt_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- 사용 횟수 증가 RPC 함수
CREATE OR REPLACE FUNCTION increment_template_usage(p_template_id UUID)
RETURNS VOID
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    UPDATE ie_prompt_templates
    SET usage_count = usage_count + 1,
        updated_at = NOW()
    WHERE id = p_template_id;
END;
$$ LANGUAGE plpgsql;

GRANT EXECUTE ON FUNCTION increment_template_usage(UUID) TO authenticated;

-- =============================================
-- 15. 개인 스타일 메모리 테이블
-- =============================================

CREATE TABLE IF NOT EXISTS ie_style_profiles (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    preferred_styles JSONB DEFAULT '[]',                      -- 자주 사용하는 스타일 목록 [{style_id, count}]
    preferred_length TEXT DEFAULT 'medium',                    -- 선호 길이 (short/medium/long)
    preferred_writing_style TEXT DEFAULT 'conversational',     -- 선호 문체
    tone_keywords JSONB DEFAULT '[]',                          -- 선호 톤 키워드 (자동 추출)
    avoid_keywords JSONB DEFAULT '[]',                         -- 피하고 싶은 표현 (사용자 지정)
    custom_instructions TEXT DEFAULT '',                        -- 사용자 커스텀 지시사항
    style_memory_enabled BOOLEAN DEFAULT TRUE,                 -- 스타일 메모리 활성화 여부
    generation_count INT DEFAULT 0,                            -- 총 생성 횟수
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_style_profiles_user_id ON ie_style_profiles(user_id);

-- RLS
ALTER TABLE ie_style_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own style profiles"
    ON ie_style_profiles FOR ALL
    USING (auth.uid() = user_id);

-- updated_at 트리거
DROP TRIGGER IF EXISTS ie_style_profiles_updated_at ON ie_style_profiles;
CREATE TRIGGER ie_style_profiles_updated_at
    BEFORE UPDATE ON ie_style_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- =============================================
-- 완료!
-- =============================================
-- 이제 .env 파일에 Supabase 설정을 추가하세요:
-- SUPABASE_URL=https://your-project.supabase.co
-- SUPABASE_ANON_KEY=your-anon-key
