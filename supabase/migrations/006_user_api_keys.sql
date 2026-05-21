-- =============================================
-- Migration 006: ie_user_api_keys 통합 테이블
-- =============================================
-- 배경: services/data/api_key_service.py(IE 자체 발급 토큰)와
--      src/contexts/identity/.../supabase_api_key_vault.py(외부 LLM BYO 키)
--      두 시스템이 'ie_user_api_keys' 테이블명을 다른 컬럼 구조로 사용 중이었지만
--      DDL이 한 번도 정의된 적이 없어 운영에서 사용 불가 상태였다.
--
-- 본 마이그레이션: 두 도메인을 한 테이블에 공존시키는 통합 스키마를 생성한다.
--   - 한 행은 (key_hash) 또는 (encrypted_key) 중 하나에만 속한다 (CHECK 제약)
--   - BYO 키의 upsert는 (user_id, provider, label) partial unique 인덱스로 보장
--   - IE 토큰의 검증은 (key_hash) WHERE is_active partial 인덱스로 가속
--
-- 운영 적용:
--   - 운영 DB에는 현재 ie_user_api_keys 테이블이 없으므로 CREATE만 수행
--   - 데이터 마이그레이션 불필요
--
-- 관련: Issue #16, PR #15 (Phase 2-f)

CREATE TABLE IF NOT EXISTS ie_user_api_keys (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- (a) IE 자체 발급 토큰 — services/data/api_key_service.py
    name TEXT,
    key_hash TEXT,
    key_prefix TEXT,
    usage_count INT NOT NULL DEFAULT 0,
    last_used_at TIMESTAMPTZ,

    -- (b) 외부 LLM BYO 키 — src/contexts/identity/.../supabase_api_key_vault.py
    provider TEXT,
    label TEXT,
    encrypted_key TEXT,

    -- 공통
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT ie_user_api_keys_row_kind CHECK (
        key_hash IS NOT NULL OR encrypted_key IS NOT NULL
    )
);

-- RLS
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

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_ie_user_api_keys_hash
    ON ie_user_api_keys(key_hash)
    WHERE key_hash IS NOT NULL AND is_active = true;

CREATE INDEX IF NOT EXISTS idx_ie_user_api_keys_user
    ON ie_user_api_keys(user_id, is_active);

CREATE UNIQUE INDEX IF NOT EXISTS uq_ie_user_api_keys_provider
    ON ie_user_api_keys(user_id, provider, label)
    WHERE provider IS NOT NULL;

-- updated_at 트리거 (schema.sql의 update_updated_at 함수에 의존)
-- 운영에 schema.sql이 먼저 적용되어야 함 (update_updated_at 함수 존재).
DROP TRIGGER IF EXISTS ie_user_api_keys_updated_at ON ie_user_api_keys;
CREATE TRIGGER ie_user_api_keys_updated_at
    BEFORE UPDATE ON ie_user_api_keys
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
