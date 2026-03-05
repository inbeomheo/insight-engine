-- Insight Engine DB 마이그레이션 001: 초기 스키마 (F9-03)
-- 실행: psql $DATABASE_URL -f migrations/001_initial_schema.sql
-- 또는 Supabase SQL Editor에서 실행

-- 마이그레이션 히스토리 테이블
CREATE TABLE IF NOT EXISTS ie_migrations (
    id SERIAL PRIMARY KEY,
    version VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    applied_at TIMESTAMPTZ DEFAULT NOW()
);

-- 사용량 테이블
CREATE TABLE IF NOT EXISTS ie_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    usage_count INTEGER NOT NULL DEFAULT 0,
    max_usage INTEGER NOT NULL DEFAULT 20,
    reset_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, reset_date)
);

-- 히스토리 테이블
CREATE TABLE IF NOT EXISTS ie_histories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title TEXT,
    style_id VARCHAR(50),
    model VARCHAR(100),
    content_preview TEXT,
    token_count INTEGER DEFAULT 0,
    duration_ms INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_ie_histories_user_id ON ie_histories(user_id);
CREATE INDEX IF NOT EXISTS idx_ie_histories_created_at ON ie_histories(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ie_usage_user_id ON ie_usage(user_id);

-- 안전 사용량 차감 함수
CREATE OR REPLACE FUNCTION decrement_usage_safe(p_user_id UUID)
RETURNS JSON
LANGUAGE plpgsql
AS $$
DECLARE
    v_remaining INTEGER;
    v_new_count INTEGER;
BEGIN
    SELECT (max_usage - usage_count) INTO v_remaining
    FROM ie_usage
    WHERE user_id = p_user_id AND reset_date = CURRENT_DATE;

    IF v_remaining IS NULL OR v_remaining <= 0 THEN
        RETURN '{"success": false, "reason": "no_usage_left"}'::JSON;
    END IF;

    UPDATE ie_usage
    SET usage_count = usage_count + 1, updated_at = NOW()
    WHERE user_id = p_user_id AND reset_date = CURRENT_DATE
    RETURNING (max_usage - usage_count) INTO v_new_count;

    RETURN json_build_object('success', true, 'new_count', v_new_count);
END;
$$;

-- 마이그레이션 기록
INSERT INTO ie_migrations (version, name) VALUES ('001', 'initial_schema')
ON CONFLICT (version) DO NOTHING;
