-- =============================================
-- Insight Engine - Supabase Schema
-- =============================================
-- Supabase Dashboard > SQL Editor에서 실행하세요

-- 1. 분석 히스토리 테이블
CREATE TABLE IF NOT EXISTS histories (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    report_id TEXT NOT NULL,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    style TEXT NOT NULL,
    content TEXT,
    html TEXT,
    mindmap_markdown TEXT,
    usage JSONB,
    elapsed_time FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. API 키 저장 테이블 (암호화됨)
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
    -- 암호화된 API 키들 (pgcrypto 사용)
    openai_key TEXT,
    anthropic_key TEXT,
    google_key TEXT,
    zhipu_key TEXT,
    deepseek_key TEXT,
    supadata_key TEXT,
    -- 선택된 프로바이더
    selected_provider TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. 커스텀 스타일 테이블
CREATE TABLE IF NOT EXISTS custom_styles (
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

-- 4. 사용자 설정 테이블
CREATE TABLE IF NOT EXISTS user_settings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
    default_style TEXT DEFAULT 'summary',
    default_length TEXT DEFAULT 'medium',
    default_tone TEXT DEFAULT 'professional',
    default_language TEXT DEFAULT 'ko',
    use_emoji BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================
-- Row Level Security (RLS) 정책
-- =============================================

-- histories 테이블 RLS
ALTER TABLE histories ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own histories"
    ON histories FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own histories"
    ON histories FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own histories"
    ON histories FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own histories"
    ON histories FOR DELETE
    USING (auth.uid() = user_id);

-- api_keys 테이블 RLS
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own api_keys"
    ON api_keys FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own api_keys"
    ON api_keys FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own api_keys"
    ON api_keys FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own api_keys"
    ON api_keys FOR DELETE
    USING (auth.uid() = user_id);

-- custom_styles 테이블 RLS
ALTER TABLE custom_styles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own custom_styles"
    ON custom_styles FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own custom_styles"
    ON custom_styles FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own custom_styles"
    ON custom_styles FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own custom_styles"
    ON custom_styles FOR DELETE
    USING (auth.uid() = user_id);

-- user_settings 테이블 RLS
ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own settings"
    ON user_settings FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own settings"
    ON user_settings FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own settings"
    ON user_settings FOR UPDATE
    USING (auth.uid() = user_id);

-- =============================================
-- 인덱스
-- =============================================

CREATE INDEX IF NOT EXISTS idx_histories_user_id ON histories(user_id);
CREATE INDEX IF NOT EXISTS idx_histories_created_at ON histories(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_custom_styles_user_id ON custom_styles(user_id);

-- =============================================
-- 트리거: updated_at 자동 업데이트
-- =============================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER histories_updated_at
    BEFORE UPDATE ON histories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER api_keys_updated_at
    BEFORE UPDATE ON api_keys
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER custom_styles_updated_at
    BEFORE UPDATE ON custom_styles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER user_settings_updated_at
    BEFORE UPDATE ON user_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
