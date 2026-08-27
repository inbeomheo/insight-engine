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
    max_usage INT NOT NULL DEFAULT 20,  -- 일일 최대 사용 횟수
    last_reset_date DATE DEFAULT CURRENT_DATE,  -- 마지막 리셋 날짜
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE ie_usage
    ADD COLUMN IF NOT EXISTS max_usage INT NOT NULL DEFAULT 20;

-- 1-1b. 사용량 예약 원장 (비용 작업 선예약 + 멱등 환불)
CREATE TABLE IF NOT EXISTS ie_usage_reservations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    idempotency_key TEXT NOT NULL,
    request_fingerprint TEXT NOT NULL,
    owner_token_hash TEXT NOT NULL,
    amount INT NOT NULL CHECK (amount > 0),
    state TEXT NOT NULL DEFAULT 'reserved'
        CHECK (state IN ('reserved', 'refunded')),
    remaining_after_reserve INT NOT NULL CHECK (remaining_after_reserve >= 0),
    max_usage INT NOT NULL CHECK (max_usage > 0),
    remaining_after_refund INT,
    refunded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ie_usage_reservations_user_key_unique
        UNIQUE (user_id, idempotency_key)
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

    -- 한 행은 두 도메인 중 정확히 하나에만 속해야 한다 (XOR)
    CONSTRAINT ie_user_api_keys_row_kind CHECK (
        (key_hash IS NOT NULL AND encrypted_key IS NULL)
        OR (key_hash IS NULL AND encrypted_key IS NOT NULL)
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
-- PostgreSQL view-owner 권한으로 기반 테이블 RLS를 우회하지 않게 하고,
-- Data API 기본 역할에는 조회 권한 자체를 부여하지 않는다.
CREATE OR REPLACE VIEW public.ie_usage_with_email
WITH (security_invoker = true, security_barrier = true) AS
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
CREATE OR REPLACE VIEW public.ie_histories_with_email
WITH (security_invoker = true, security_barrier = true) AS
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

REVOKE ALL ON TABLE public.ie_usage_with_email
    FROM PUBLIC, anon, authenticated;
REVOKE ALL ON TABLE public.ie_histories_with_email
    FROM PUBLIC, anon, authenticated;
REVOKE ALL ON TABLE public.ie_usage_with_email
    FROM service_role;
REVOKE ALL ON TABLE public.ie_histories_with_email
    FROM service_role;
GRANT SELECT ON TABLE public.ie_usage_with_email
    TO service_role;
GRANT SELECT ON TABLE public.ie_histories_with_email
    TO service_role;

-- =============================================
-- 3. Row Level Security (RLS) 정책
-- =============================================

-- ie_usage 테이블 RLS
ALTER TABLE ie_usage ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own usage"
    ON ie_usage FOR SELECT
    USING (auth.uid() = user_id);

-- 예약 원장은 RPC만 접근한다. public 스키마 노출에 대비해 RLS와 권한을 모두 차단.
ALTER TABLE ie_usage_reservations ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE ie_usage_reservations FROM PUBLIC, anon, authenticated;

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
CREATE INDEX IF NOT EXISTS idx_ie_usage_reservations_user_created
    ON ie_usage_reservations(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ie_usage_reservations_refunded_at
    ON ie_usage_reservations(refunded_at)
    WHERE state = 'refunded';

CREATE OR REPLACE FUNCTION public.cleanup_expired_usage_reservations_on_insert()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_role TEXT := COALESCE((SELECT auth.jwt() ->> 'role'), '');
BEGIN
    IF v_role <> 'service_role' THEN
        RAISE EXCEPTION 'usage reservation cleanup requires service_role'
            USING ERRCODE = '42501';
    END IF;

    WITH expired AS (
        SELECT id
        FROM public.ie_usage_reservations
        WHERE state = 'refunded'
          AND refunded_at < pg_catalog.now() - INTERVAL '7 days'
        ORDER BY refunded_at
        LIMIT 100
        FOR UPDATE SKIP LOCKED
    )
    DELETE FROM public.ie_usage_reservations AS reservation
    USING expired
    WHERE reservation.id = expired.id;

    RETURN NEW;
END;
$$;

REVOKE ALL ON FUNCTION public.cleanup_expired_usage_reservations_on_insert()
    FROM PUBLIC, anon, authenticated;

DROP TRIGGER IF EXISTS cleanup_expired_usage_reservations_before_insert
    ON public.ie_usage_reservations;
CREATE TRIGGER cleanup_expired_usage_reservations_before_insert
    BEFORE INSERT ON public.ie_usage_reservations
    FOR EACH ROW
    EXECUTE FUNCTION public.cleanup_expired_usage_reservations_on_insert();

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
-- BYO 키 upsert의 on_conflict 추론을 지원하는 비부분 unique index.
-- IE 토큰 행은 provider/label이 NULL이므로 여러 행을 유지할 수 있다.
CREATE UNIQUE INDEX IF NOT EXISTS uq_ie_user_api_keys_provider
    ON ie_user_api_keys(user_id, provider, label);

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

DROP FUNCTION IF EXISTS public.decrement_usage_safe(UUID);
DROP FUNCTION IF EXISTS public.decrement_usage_safe(UUID, INT);

CREATE OR REPLACE FUNCTION public.decrement_usage_safe(
    p_user_id UUID,
    p_amount INT DEFAULT 1
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_new_count INT;
    v_role TEXT := COALESCE((SELECT auth.jwt() ->> 'role'), '');
BEGIN
    IF (SELECT auth.uid()) IS DISTINCT FROM p_user_id
       AND v_role <> 'service_role' THEN
        RAISE EXCEPTION 'usage decrement user mismatch'
            USING ERRCODE = '42501';
    END IF;

    IF p_user_id IS NULL OR p_amount IS NULL OR p_amount <= 0 THEN
        RAISE EXCEPTION 'invalid usage decrement parameters'
            USING ERRCODE = '22023';
    END IF;

    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(p_user_id::TEXT, 0)
    );

    INSERT INTO public.ie_usage (
        user_id, usage_count, max_usage, last_reset_date
    ) VALUES (
        p_user_id, 20, 20, CURRENT_DATE
    )
    ON CONFLICT (user_id) DO UPDATE
    SET usage_count = CASE
            WHEN public.ie_usage.last_reset_date IS DISTINCT FROM CURRENT_DATE
                THEN public.ie_usage.max_usage
            ELSE COALESCE(
                public.ie_usage.usage_count,
                public.ie_usage.max_usage
            )
        END,
        last_reset_date = CURRENT_DATE,
        updated_at = CASE
            WHEN public.ie_usage.last_reset_date IS DISTINCT FROM CURRENT_DATE
                THEN pg_catalog.now()
            ELSE public.ie_usage.updated_at
        END;

    UPDATE public.ie_usage
    SET usage_count = usage_count - p_amount,
        updated_at = pg_catalog.now()
    WHERE user_id = p_user_id
      AND usage_count >= p_amount
    RETURNING usage_count INTO v_new_count;

    IF FOUND THEN
        RETURN pg_catalog.jsonb_build_object(
            'success', true,
            'new_count', v_new_count
        );
    ELSE
        RETURN pg_catalog.jsonb_build_object(
            'success', false,
            'reason', 'no_usage_left'
        );
    END IF;
END;
$$;

REVOKE ALL ON FUNCTION public.decrement_usage_safe(UUID, INT)
    FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.decrement_usage_safe(UUID, INT)
    TO authenticated, service_role;

-- 사용량 조회·신규 행 생성·일자 변경 리셋을 하나의 권한 검증 RPC로 묶는다.
-- 일반 사용자는 자기 행만 조회할 수 있고, ie_usage 테이블을 직접 INSERT/UPDATE
-- 할 권한은 갖지 않는다.
CREATE OR REPLACE FUNCTION public.get_usage_safe(p_user_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_usage_count INT;
    v_max_usage INT;
    v_role TEXT := COALESCE((SELECT auth.jwt() ->> 'role'), '');
BEGIN
    IF (SELECT auth.uid()) IS DISTINCT FROM p_user_id
       AND v_role <> 'service_role' THEN
        RAISE EXCEPTION 'usage lookup user mismatch'
            USING ERRCODE = '42501';
    END IF;

    IF p_user_id IS NULL THEN
        RAISE EXCEPTION 'invalid usage lookup parameters'
            USING ERRCODE = '22023';
    END IF;

    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(p_user_id::TEXT, 0)
    );

    INSERT INTO public.ie_usage (
        user_id, usage_count, max_usage, last_reset_date
    ) VALUES (
        p_user_id, 20, 20, CURRENT_DATE
    )
    ON CONFLICT (user_id) DO UPDATE
    SET usage_count = CASE
            WHEN public.ie_usage.last_reset_date IS DISTINCT FROM CURRENT_DATE
                THEN public.ie_usage.max_usage
            ELSE COALESCE(
                public.ie_usage.usage_count,
                public.ie_usage.max_usage
            )
        END,
        last_reset_date = CURRENT_DATE,
        updated_at = CASE
            WHEN public.ie_usage.last_reset_date IS DISTINCT FROM CURRENT_DATE
                THEN pg_catalog.now()
            ELSE public.ie_usage.updated_at
        END
    RETURNING usage_count, max_usage
    INTO v_usage_count, v_max_usage;

    RETURN pg_catalog.jsonb_build_object(
        'usage_count', v_usage_count,
        'max_usage', v_max_usage,
        'can_use', v_usage_count > 0
    );
END;
$$;

REVOKE ALL ON FUNCTION public.get_usage_safe(UUID)
    FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.get_usage_safe(UUID)
    TO authenticated, service_role;

-- Aggregate 저장 포트의 관리자용 quota 갱신. 사용자 JWT로는 실행할 수 없고,
-- 값 범위도 DB에서 검증한다. 일반 소비/환불은 전용 RPC만 사용한다.
CREATE OR REPLACE FUNCTION public.set_usage_quota_admin(
    p_user_id UUID,
    p_usage_count INT,
    p_max_usage INT
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_usage_count INT;
    v_max_usage INT;
    v_role TEXT := COALESCE((SELECT auth.jwt() ->> 'role'), '');
BEGIN
    IF v_role <> 'service_role' THEN
        RAISE EXCEPTION 'service role required for quota update'
            USING ERRCODE = '42501';
    END IF;

    IF p_user_id IS NULL
       OR p_usage_count IS NULL
       OR p_max_usage IS NULL
       OR p_max_usage <= 0
       OR p_usage_count < 0
       OR p_usage_count > p_max_usage THEN
        RAISE EXCEPTION 'invalid quota update parameters'
            USING ERRCODE = '22023';
    END IF;

    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(p_user_id::TEXT, 0)
    );

    INSERT INTO public.ie_usage (
        user_id, usage_count, max_usage, last_reset_date
    ) VALUES (
        p_user_id, p_usage_count, p_max_usage, CURRENT_DATE
    )
    ON CONFLICT (user_id) DO UPDATE
    SET usage_count = EXCLUDED.usage_count,
        max_usage = EXCLUDED.max_usage,
        last_reset_date = CURRENT_DATE,
        updated_at = pg_catalog.now()
    RETURNING usage_count, max_usage
    INTO v_usage_count, v_max_usage;

    RETURN pg_catalog.jsonb_build_object(
        'success', true,
        'usage_count', v_usage_count,
        'max_usage', v_max_usage
    );
END;
$$;

REVOKE ALL ON FUNCTION public.set_usage_quota_admin(UUID, INT, INT)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.set_usage_quota_admin(UUID, INT, INT)
    TO service_role;

-- 비용 작업 전 원자적·멱등 사용량 예약. 사용자별 transaction advisory lock
-- (트랜잭션 범위 애플리케이션 잠금)과 UNIQUE(user_id, idempotency_key)를 함께
-- 사용해 동시 요청과 커밋 후 응답 유실 재시도를 모두 단일 차감으로 수렴시킨다.
CREATE OR REPLACE FUNCTION public.reserve_usage_safe(
    p_user_id UUID,
    p_idempotency_key TEXT,
    p_request_fingerprint TEXT,
    p_owner_token_hash TEXT,
    p_amount INT DEFAULT 1
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_reservation public.ie_usage_reservations%ROWTYPE;
    v_new_count INT;
    v_max_usage INT;
    v_role TEXT := COALESCE((SELECT auth.jwt() ->> 'role'), '');
BEGIN
    IF (SELECT auth.uid()) IS DISTINCT FROM p_user_id
       AND v_role <> 'service_role' THEN
        RAISE EXCEPTION 'usage reservation user mismatch'
            USING ERRCODE = '42501';
    END IF;

    IF p_user_id IS NULL
       OR p_amount IS NULL
       OR p_amount <= 0
       OR p_idempotency_key IS NULL
       OR pg_catalog.length(p_idempotency_key) = 0
       OR pg_catalog.length(p_idempotency_key) > 80
       OR p_request_fingerprint IS NULL
       OR p_request_fingerprint !~ '^[0-9a-f]{64}$'
       OR p_owner_token_hash IS NULL
       OR p_owner_token_hash !~ '^[0-9a-f]{64}$' THEN
        RAISE EXCEPTION 'invalid usage reservation parameters'
            USING ERRCODE = '22023';
    END IF;

    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(p_user_id::TEXT, 0)
    );

    -- 새 사용자 행 생성과 일자 변경 리셋을 예약과 같은
    -- 트랜잭션/사용자 잠 안에서 수행한다.
    INSERT INTO public.ie_usage (
        user_id, usage_count, max_usage, last_reset_date
    ) VALUES (
        p_user_id, 20, 20, CURRENT_DATE
    )
    ON CONFLICT (user_id) DO UPDATE
    SET usage_count = CASE
            WHEN public.ie_usage.last_reset_date IS DISTINCT FROM CURRENT_DATE
                THEN public.ie_usage.max_usage
            ELSE COALESCE(
                public.ie_usage.usage_count,
                public.ie_usage.max_usage
            )
        END,
        last_reset_date = CURRENT_DATE,
        updated_at = CASE
            WHEN public.ie_usage.last_reset_date IS DISTINCT FROM CURRENT_DATE
                THEN pg_catalog.now()
            ELSE public.ie_usage.updated_at
        END;

    SELECT *
    INTO v_reservation
    FROM public.ie_usage_reservations
    WHERE user_id = p_user_id
      AND idempotency_key = p_idempotency_key
    FOR UPDATE;

    IF FOUND THEN
        IF v_reservation.request_fingerprint IS DISTINCT FROM p_request_fingerprint
           OR v_reservation.amount IS DISTINCT FROM p_amount THEN
            RETURN pg_catalog.jsonb_build_object(
                'success', false,
                'reason', 'idempotency_conflict'
            );
        END IF;

        IF v_reservation.state = 'reserved' THEN
            IF v_reservation.owner_token_hash IS DISTINCT FROM p_owner_token_hash THEN
                RETURN pg_catalog.jsonb_build_object(
                    'success', false,
                    'reason', 'idempotency_replay',
                    'reservation_id', v_reservation.id::TEXT,
                    'new_count', v_reservation.remaining_after_reserve,
                    'max_usage', v_reservation.max_usage
                );
            END IF;
            RETURN pg_catalog.jsonb_build_object(
                'success', true,
                'reservation_id', v_reservation.id::TEXT,
                'new_count', v_reservation.remaining_after_reserve,
                'max_usage', v_reservation.max_usage,
                'owned', true,
                'replayed', true
            );
        END IF;

        -- 이전 시도가 환불된 같은 논리 요청은 새 소유 토큰으로 다시 예약 가능.
        UPDATE public.ie_usage
        SET usage_count = usage_count - p_amount,
            updated_at = pg_catalog.now()
        WHERE user_id = p_user_id
          AND usage_count >= p_amount
        RETURNING usage_count, max_usage INTO v_new_count, v_max_usage;

        IF NOT FOUND THEN
            RETURN pg_catalog.jsonb_build_object(
                'success', false,
                'reason', 'no_usage_left'
            );
        END IF;

        UPDATE public.ie_usage_reservations
        SET owner_token_hash = p_owner_token_hash,
            state = 'reserved',
            remaining_after_reserve = v_new_count,
            max_usage = v_max_usage,
            remaining_after_refund = NULL,
            refunded_at = NULL,
            updated_at = pg_catalog.now()
        WHERE id = v_reservation.id;

        RETURN pg_catalog.jsonb_build_object(
            'success', true,
            'reservation_id', v_reservation.id::TEXT,
            'new_count', v_new_count,
            'max_usage', v_max_usage,
            'owned', true,
            'replayed', false
        );
    END IF;

    UPDATE public.ie_usage
    SET usage_count = usage_count - p_amount,
        updated_at = pg_catalog.now()
    WHERE user_id = p_user_id
      AND usage_count >= p_amount
    RETURNING usage_count, max_usage INTO v_new_count, v_max_usage;

    IF NOT FOUND THEN
        RETURN pg_catalog.jsonb_build_object(
            'success', false,
            'reason', 'no_usage_left'
        );
    END IF;

    INSERT INTO public.ie_usage_reservations (
        user_id,
        idempotency_key,
        request_fingerprint,
        owner_token_hash,
        amount,
        state,
        remaining_after_reserve,
        max_usage
    ) VALUES (
        p_user_id,
        p_idempotency_key,
        p_request_fingerprint,
        p_owner_token_hash,
        p_amount,
        'reserved',
        v_new_count,
        v_max_usage
    )
    RETURNING * INTO v_reservation;

    RETURN pg_catalog.jsonb_build_object(
        'success', true,
        'reservation_id', v_reservation.id::TEXT,
        'new_count', v_new_count,
        'max_usage', v_max_usage,
        'owned', true,
        'replayed', false
    );
END;
$$;

-- 예약 소유 토큰이 일치하는 경우에만 1회 환불한다. 같은 RPC를 재시도하면
-- refunded 상태의 저장값을 반환하므로 중복 증가하지 않는다.
CREATE OR REPLACE FUNCTION public.refund_usage_reservation_safe(
    p_user_id UUID,
    p_idempotency_key TEXT,
    p_request_fingerprint TEXT,
    p_owner_token_hash TEXT
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_reservation public.ie_usage_reservations%ROWTYPE;
    v_new_count INT;
    v_role TEXT := COALESCE((SELECT auth.jwt() ->> 'role'), '');
BEGIN
    IF (SELECT auth.uid()) IS DISTINCT FROM p_user_id
       AND v_role <> 'service_role' THEN
        RAISE EXCEPTION 'usage refund user mismatch'
            USING ERRCODE = '42501';
    END IF;

    IF p_user_id IS NULL
       OR p_idempotency_key IS NULL
       OR pg_catalog.length(p_idempotency_key) = 0
       OR pg_catalog.length(p_idempotency_key) > 80
       OR p_request_fingerprint IS NULL
       OR p_request_fingerprint !~ '^[0-9a-f]{64}$'
       OR p_owner_token_hash IS NULL
       OR p_owner_token_hash !~ '^[0-9a-f]{64}$' THEN
        RAISE EXCEPTION 'invalid usage refund parameters'
            USING ERRCODE = '22023';
    END IF;

    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(p_user_id::TEXT, 0)
    );

    SELECT *
    INTO v_reservation
    FROM public.ie_usage_reservations
    WHERE user_id = p_user_id
      AND idempotency_key = p_idempotency_key
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN pg_catalog.jsonb_build_object(
            'success', false,
            'reason', 'reservation_not_found'
        );
    END IF;

    IF v_reservation.request_fingerprint IS DISTINCT FROM p_request_fingerprint THEN
        RETURN pg_catalog.jsonb_build_object(
            'success', false,
            'reason', 'idempotency_conflict'
        );
    END IF;

    IF v_reservation.owner_token_hash IS DISTINCT FROM p_owner_token_hash THEN
        RETURN pg_catalog.jsonb_build_object(
            'success', false,
            'reason', 'reservation_not_owned'
        );
    END IF;

    IF v_reservation.state = 'refunded' THEN
        RETURN pg_catalog.jsonb_build_object(
            'success', true,
            'new_count', v_reservation.remaining_after_refund,
            'refunded', false,
            'replayed', true
        );
    END IF;

    UPDATE public.ie_usage
    SET usage_count = LEAST(
            max_usage,
            usage_count + v_reservation.amount
        ),
        updated_at = pg_catalog.now()
    WHERE user_id = p_user_id
    RETURNING usage_count INTO v_new_count;

    IF NOT FOUND THEN
        RETURN pg_catalog.jsonb_build_object(
            'success', false,
            'reason', 'usage_row_missing'
        );
    END IF;

    UPDATE public.ie_usage_reservations
    SET state = 'refunded',
        remaining_after_refund = v_new_count,
        refunded_at = pg_catalog.now(),
        updated_at = pg_catalog.now()
    WHERE id = v_reservation.id;

    RETURN pg_catalog.jsonb_build_object(
        'success', true,
        'new_count', v_new_count,
        'refunded', true,
        'replayed', false
    );
END;
$$;

REVOKE ALL ON FUNCTION public.reserve_usage_safe(UUID, TEXT, TEXT, TEXT, INT)
    FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.refund_usage_reservation_safe(UUID, TEXT, TEXT, TEXT)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.reserve_usage_safe(UUID, TEXT, TEXT, TEXT, INT)
    TO service_role;
GRANT EXECUTE ON FUNCTION public.refund_usage_reservation_safe(UUID, TEXT, TEXT, TEXT)
    TO service_role;

-- 예약 원장에서 최근 일별 순사용량을 집계한다. 일반 사용자는 자신의 계정만,
-- service_role은 관리자 대시보드용 전체 집계만 조회할 수 있다.
CREATE OR REPLACE FUNCTION public.get_daily_usage_history(
    p_user_id UUID DEFAULT NULL,
    p_days INT DEFAULT 7
)
RETURNS TABLE("date" DATE, used_count BIGINT)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_role TEXT := COALESCE((SELECT auth.jwt() ->> 'role'), '');
    v_user_id UUID := (SELECT auth.uid());
BEGIN
    IF p_days IS NULL OR p_days < 1 OR p_days > 90 THEN
        RAISE EXCEPTION 'p_days must be between 1 and 90'
            USING ERRCODE = '22023';
    END IF;

    IF v_role <> 'service_role'
       AND (p_user_id IS NULL OR v_user_id IS DISTINCT FROM p_user_id) THEN
        RAISE EXCEPTION 'usage history user mismatch'
            USING ERRCODE = '42501';
    END IF;

    RETURN QUERY
    SELECT
        days.usage_date::DATE AS "date",
        COALESCE(
            pg_catalog.sum(reservation.amount)
                FILTER (WHERE reservation.state = 'reserved'),
            0
        )::BIGINT AS used_count
    FROM pg_catalog.generate_series(
        CURRENT_DATE - (p_days - 1),
        CURRENT_DATE,
        INTERVAL '1 day'
    ) AS days(usage_date)
    LEFT JOIN public.ie_usage_reservations AS reservation
      ON reservation.created_at >= days.usage_date
     AND reservation.created_at < days.usage_date + INTERVAL '1 day'
     AND (p_user_id IS NULL OR reservation.user_id = p_user_id)
    GROUP BY days.usage_date
    ORDER BY days.usage_date;
END;
$$;

REVOKE ALL ON FUNCTION public.get_daily_usage_history(UUID, INT)
    FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.get_daily_usage_history(UUID, INT)
    TO authenticated, service_role;

-- =============================================
-- 7. RPC 함수: 일일 사용량 리셋 (선택)
-- =============================================

CREATE OR REPLACE FUNCTION public.reset_daily_usage()
RETURNS INT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_count INT;
BEGIN
    UPDATE public.ie_usage
    SET usage_count = 20,
        last_reset_date = CURRENT_DATE,
        updated_at = pg_catalog.now()
    WHERE last_reset_date < CURRENT_DATE;

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$;

REVOKE ALL ON FUNCTION public.reset_daily_usage()
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.reset_daily_usage()
    TO service_role;

-- =============================================
-- 8. RPC 함수: 만료 히스토리 자동 삭제 (7일 보존)
-- =============================================

CREATE OR REPLACE FUNCTION public.cleanup_expired_histories()
RETURNS INT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_count INT;
BEGIN
    DELETE FROM public.ie_histories
    WHERE created_at < pg_catalog.now() - INTERVAL '7 days';

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$;

REVOKE ALL ON FUNCTION public.cleanup_expired_histories()
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.cleanup_expired_histories()
    TO service_role;

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

-- 노출되지 않는 스키마의 definer 함수가 멤버 테이블 RLS를 우회해 단일
-- 멤버십만 확인한다. user_id를 인자로 받지 않아 호출자가 다른 사용자의
-- 멤버십을 대신 조회할 수 없다.
CREATE SCHEMA IF NOT EXISTS private;
REVOKE ALL ON SCHEMA private FROM PUBLIC, anon;
GRANT USAGE ON SCHEMA private TO authenticated;

CREATE OR REPLACE FUNCTION private.is_workspace_member(p_workspace_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
    SELECT p_workspace_id IS NOT NULL
       AND (SELECT auth.uid()) IS NOT NULL
       AND EXISTS (
            SELECT 1
            FROM public.ie_workspace_members AS membership
            WHERE membership.workspace_id = p_workspace_id
              AND membership.user_id = (SELECT auth.uid())
       );
$$;

REVOKE ALL ON FUNCTION private.is_workspace_member(UUID)
    FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION private.is_workspace_member(UUID)
    TO authenticated;

-- 워크스페이스: 멤버만 읽기 가능
CREATE POLICY workspace_member_read ON public.ie_workspaces FOR SELECT
    TO authenticated
    USING ((SELECT private.is_workspace_member(id)));

-- 워크스페이스: owner만 쓰기 가능
CREATE POLICY workspace_owner_write ON ie_workspaces FOR ALL
    USING (owner_id = auth.uid());

-- 멤버: 같은 워크스페이스 멤버만 읽기 가능
CREATE POLICY member_read ON public.ie_workspace_members FOR SELECT
    TO authenticated
    USING ((SELECT private.is_workspace_member(workspace_id)));

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

-- 사용 횟수 증가는 서버가 실제 템플릿 사용을 검증한 뒤 기록한다. 사용자에게
-- 직접 EXECUTE를 주면 공개 템플릿 랭킹을 임의로 조작할 수 있다.
CREATE OR REPLACE FUNCTION public.increment_template_usage(p_template_id UUID)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    UPDATE public.ie_prompt_templates
    SET usage_count = usage_count + 1,
        updated_at = pg_catalog.now()
    WHERE id = p_template_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'template not accessible'
            USING ERRCODE = '42501';
    END IF;
END;
$$;

REVOKE ALL ON FUNCTION public.increment_template_usage(UUID)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.increment_template_usage(UUID)
    TO service_role;

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
-- 16. 이전 증분 마이그레이션의 앱 테이블 통합
-- =============================================
-- 새 프로젝트는 이 파일 하나만 실행하므로 003~005에서 추가됐던 테이블도
-- 반드시 포함한다. 기존 프로젝트는 해당 마이그레이션 후 009를 적용한다.

CREATE TABLE IF NOT EXISTS public.ie_snippets (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    category TEXT NOT NULL DEFAULT 'general',
    label TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.ie_snippets ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS snippets_manage_own ON public.ie_snippets;
CREATE POLICY snippets_manage_own ON public.ie_snippets FOR ALL
    TO authenticated
    USING ((SELECT auth.uid()) = user_id)
    WITH CHECK ((SELECT auth.uid()) = user_id);

CREATE INDEX IF NOT EXISTS idx_ie_snippets_user_id
    ON public.ie_snippets(user_id);
CREATE INDEX IF NOT EXISTS idx_ie_snippets_category
    ON public.ie_snippets(user_id, category);

CREATE TABLE IF NOT EXISTS public.ie_channel_monitors (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    channel_id TEXT NOT NULL,
    channel_title TEXT DEFAULT '',
    style_id TEXT DEFAULT 'blog_seo',
    modifiers JSONB DEFAULT
        '{"length":"medium","writing_style":"conversational","language":"ko"}',
    interval_minutes INT DEFAULT 30 CHECK (interval_minutes >= 10),
    last_checked_at TIMESTAMPTZ,
    last_video_id TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.ie_channel_monitors ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS channel_monitors_select_own
    ON public.ie_channel_monitors;
DROP POLICY IF EXISTS channel_monitors_insert_own
    ON public.ie_channel_monitors;
DROP POLICY IF EXISTS channel_monitors_delete_own
    ON public.ie_channel_monitors;
CREATE POLICY channel_monitors_select_own
    ON public.ie_channel_monitors FOR SELECT
    TO authenticated
    USING ((SELECT auth.uid()) = user_id);
CREATE POLICY channel_monitors_insert_own
    ON public.ie_channel_monitors FOR INSERT
    TO authenticated
    WITH CHECK ((SELECT auth.uid()) = user_id);
CREATE POLICY channel_monitors_delete_own
    ON public.ie_channel_monitors FOR DELETE
    TO authenticated
    USING ((SELECT auth.uid()) = user_id);

CREATE INDEX IF NOT EXISTS idx_channel_monitors_user
    ON public.ie_channel_monitors(user_id);
CREATE INDEX IF NOT EXISTS idx_channel_monitors_active
    ON public.ie_channel_monitors(is_active) WHERE is_active = TRUE;

CREATE TABLE IF NOT EXISTS public.ie_workspace_contents (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    workspace_id UUID NOT NULL
        REFERENCES public.ie_workspaces(id) ON DELETE CASCADE,
    content_id TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'review', 'approved', 'published', 'rejected')),
    author_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
    reviewer_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    review_note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE OR REPLACE FUNCTION private.workspace_role(p_workspace_id UUID)
RETURNS TEXT
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
    SELECT membership.role
    FROM public.ie_workspace_members AS membership
    WHERE membership.workspace_id = p_workspace_id
      AND membership.user_id = (SELECT auth.uid())
    LIMIT 1;
$$;

REVOKE ALL ON FUNCTION private.workspace_role(UUID)
    FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION private.workspace_role(UUID)
    TO authenticated;

ALTER TABLE public.ie_workspace_contents ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS workspace_contents_select
    ON public.ie_workspace_contents;
DROP POLICY IF EXISTS workspace_contents_insert
    ON public.ie_workspace_contents;
DROP POLICY IF EXISTS workspace_contents_update
    ON public.ie_workspace_contents;
CREATE POLICY workspace_contents_select
    ON public.ie_workspace_contents FOR SELECT
    TO authenticated
    USING ((SELECT private.is_workspace_member(workspace_id)));
CREATE POLICY workspace_contents_insert
    ON public.ie_workspace_contents FOR INSERT
    TO authenticated
    WITH CHECK (
        author_id = (SELECT auth.uid())
        AND status = 'draft'
        AND reviewer_id IS NULL
        AND review_note IS NULL
        AND (SELECT private.workspace_role(workspace_id)) IN ('owner', 'editor')
    );
CREATE POLICY workspace_contents_update
    ON public.ie_workspace_contents FOR UPDATE
    TO authenticated
    USING (
        (SELECT private.workspace_role(workspace_id)) IN ('owner', 'editor')
    )
    WITH CHECK (
        (SELECT private.workspace_role(workspace_id)) IN ('owner', 'editor')
    );

CREATE OR REPLACE FUNCTION private.enforce_workspace_content_transition()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_actor UUID := (SELECT auth.uid());
    v_role TEXT;
    v_jwt_role TEXT := COALESCE((SELECT auth.jwt() ->> 'role'), '');
BEGIN
    NEW.updated_at := pg_catalog.now();

    IF v_jwt_role = 'service_role' THEN
        RETURN NEW;
    END IF;

    IF v_actor IS NULL THEN
        RAISE EXCEPTION 'workspace content authentication required'
            USING ERRCODE = '42501';
    END IF;

    IF NEW.id IS DISTINCT FROM OLD.id
       OR NEW.workspace_id IS DISTINCT FROM OLD.workspace_id
       OR NEW.content_id IS DISTINCT FROM OLD.content_id
       OR NEW.title IS DISTINCT FROM OLD.title
       OR NEW.author_id IS DISTINCT FROM OLD.author_id
       OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
        RAISE EXCEPTION 'workspace content immutable fields changed'
            USING ERRCODE = '42501';
    END IF;

    SELECT membership.role
    INTO v_role
    FROM public.ie_workspace_members AS membership
    WHERE membership.workspace_id = OLD.workspace_id
      AND membership.user_id = v_actor;

    IF OLD.status = 'draft' AND NEW.status = 'review'
       AND v_role IN ('owner', 'editor') THEN
        NEW.reviewer_id := NULL;
        NEW.review_note := NULL;
    ELSIF OLD.status = 'review' AND NEW.status = 'approved'
          AND v_role = 'owner' THEN
        NEW.reviewer_id := v_actor;
        NEW.review_note := NULL;
    ELSIF OLD.status = 'review' AND NEW.status = 'rejected'
          AND v_role = 'owner' THEN
        NEW.reviewer_id := v_actor;
    ELSIF OLD.status = 'approved' AND NEW.status = 'published'
          AND v_role = 'owner' THEN
        NEW.reviewer_id := OLD.reviewer_id;
        NEW.review_note := OLD.review_note;
    ELSIF OLD.status IN ('approved', 'rejected')
          AND NEW.status = 'draft'
          AND v_role IN ('owner', 'editor') THEN
        NEW.reviewer_id := NULL;
        NEW.review_note := NULL;
    ELSE
        RAISE EXCEPTION 'workspace content transition not allowed'
            USING ERRCODE = '42501';
    END IF;

    RETURN NEW;
END;
$$;

REVOKE ALL ON FUNCTION private.enforce_workspace_content_transition()
    FROM PUBLIC, anon, authenticated;
DROP TRIGGER IF EXISTS ie_workspace_contents_transition
    ON public.ie_workspace_contents;
CREATE TRIGGER ie_workspace_contents_transition
    BEFORE UPDATE ON public.ie_workspace_contents
    FOR EACH ROW
    EXECUTE FUNCTION private.enforce_workspace_content_transition();

CREATE INDEX IF NOT EXISTS idx_workspace_contents_workspace
    ON public.ie_workspace_contents(workspace_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_workspace_contents_author
    ON public.ie_workspace_contents(author_id);
CREATE INDEX IF NOT EXISTS idx_workspace_contents_reviewer
    ON public.ie_workspace_contents(reviewer_id)
    WHERE reviewer_id IS NOT NULL;

-- =============================================
-- 17. Data API 최소 권한 (명시적 opt-in)
-- =============================================
-- Supabase의 자동 public 테이블 노출 여부와 무관하게 동일하게 동작하도록
-- 기존 기본 권한을 먼저 제거한 뒤 실제 앱 호출에 필요한 연산만 되돌린다.
-- anon에는 공개 테이블 경로가 없으며, 예약 원장은 RPC 전용이다.

-- DATA_API_TABLE_ACL_BEGIN
REVOKE ALL ON TABLE public.ie_usage
    FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT ON TABLE public.ie_usage
    TO authenticated;
GRANT SELECT ON TABLE public.ie_usage
    TO service_role;

REVOKE ALL ON TABLE public.ie_usage_reservations
    FROM PUBLIC, anon, authenticated, service_role;

REVOKE ALL ON TABLE public.ie_histories
    FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT, INSERT ON TABLE public.ie_histories
    TO authenticated;
GRANT SELECT ON TABLE public.ie_histories
    TO service_role;

REVOKE ALL ON TABLE public.ie_api_keys
    FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT ON TABLE public.ie_api_keys
    TO authenticated;

REVOKE ALL ON TABLE public.ie_user_api_keys
    FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT, INSERT, UPDATE ON TABLE public.ie_user_api_keys
    TO authenticated;

REVOKE ALL ON TABLE public.ie_custom_styles
    FROM PUBLIC, anon, authenticated, service_role;

REVOKE ALL ON TABLE public.ie_admins
    FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT ON TABLE public.ie_admins
    TO service_role;

REVOKE ALL ON TABLE public.ie_scheduled_posts
    FROM PUBLIC, anon, authenticated, service_role;

REVOKE ALL ON TABLE public.ie_workspaces
    FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.ie_workspaces
    TO authenticated;

REVOKE ALL ON TABLE public.ie_workspace_members
    FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.ie_workspace_members
    TO authenticated;

REVOKE ALL ON TABLE public.ie_prompt_templates
    FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.ie_prompt_templates
    TO authenticated;

REVOKE ALL ON TABLE public.ie_style_profiles
    FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT, INSERT, UPDATE ON TABLE public.ie_style_profiles
    TO authenticated;

REVOKE ALL ON TABLE public.ie_snippets
    FROM PUBLIC, anon, authenticated, service_role;

REVOKE ALL ON TABLE public.ie_channel_monitors
    FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT, INSERT, DELETE ON TABLE public.ie_channel_monitors
    TO authenticated;
GRANT SELECT, UPDATE ON TABLE public.ie_channel_monitors
    TO service_role;

REVOKE ALL ON TABLE public.ie_workspace_contents
    FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT, INSERT, UPDATE ON TABLE public.ie_workspace_contents
    TO authenticated;

-- 모든 기본 키는 gen_random_uuid()를 사용하므로 Data API 역할에 필요한
-- 시퀀스가 없고 USAGE/SELECT 시퀀스 권한도 부여하지 않는다.
-- DATA_API_TABLE_ACL_END

-- 비파괴 운영 준비 상태 확인용 스키마 버전. 전체 스키마 생성의 마지막에
-- 두어 앞선 객체 생성이 실패한 부분 설치를 ready로 오인하지 않게 한다.
-- 마이그레이션이 추가되면 반환값과 readiness의 요구 버전을 함께 올린다.
CREATE OR REPLACE FUNCTION public.insight_engine_schema_version()
RETURNS INTEGER
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = ''
AS $$
    SELECT 9;
$$;

REVOKE ALL ON FUNCTION public.insight_engine_schema_version()
    FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.insight_engine_schema_version()
    TO anon, authenticated, service_role;

-- =============================================
-- 완료!
-- =============================================
-- 이제 .env 파일에 Supabase 설정을 추가하세요:
-- SUPABASE_URL=https://your-project.supabase.co
-- SUPABASE_PUBLISHABLE_KEY=your-publishable-key
-- SUPABASE_SECRET_KEY=your-secret-key  -- 서버에서만 사용
