-- 비용 작업 전에 사용량을 예약하고 실패/캐시 적중 시 자신의 예약만
-- 환불하기 위한 멱등 원장과 RPC.

BEGIN;

ALTER TABLE public.ie_usage
    ADD COLUMN IF NOT EXISTS max_usage INT NOT NULL DEFAULT 20;

-- 레거시 직접 차감도 예약 RPC와 같은 소유권·원자성 경계를 사용한다.
-- 기존 SECURITY DEFINER(UUID) 함수는 PUBLIC 실행권과 사용자 일치 검사가 없어
-- 임의 사용자의 quota를 소진할 수 있었고, amount>1은 앱에서 반복 호출돼 부분
-- 차감될 수 있었다. 단일 p_amount UPDATE로 교체한다.
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
    END IF;
    RETURN pg_catalog.jsonb_build_object(
        'success', false,
        'reason', 'no_usage_left'
    );
END;
$$;

REVOKE ALL ON FUNCTION public.decrement_usage_safe(UUID, INT)
    FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.decrement_usage_safe(UUID, INT)
    TO authenticated, service_role;

CREATE TABLE IF NOT EXISTS public.ie_usage_reservations (
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

ALTER TABLE public.ie_usage_reservations ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.ie_usage_reservations
    FROM PUBLIC, anon, authenticated;

CREATE INDEX IF NOT EXISTS idx_ie_usage_reservations_user_created
    ON public.ie_usage_reservations(user_id, created_at DESC);

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

COMMIT;
