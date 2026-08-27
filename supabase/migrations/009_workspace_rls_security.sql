-- 워크스페이스 멤버 RLS의 자기 참조 재귀를 제거하고, 운영 유지보수
-- SECURITY DEFINER 함수의 실행 권한을 service_role로 제한한다.

BEGIN;

-- Keep the idempotency ledger bounded without deleting active or recent
-- reservations. The server-only reservation insert path performs a bounded
-- cleanup batch, so cleanup capacity grows with ledger write volume.
CREATE INDEX IF NOT EXISTS idx_ie_usage_reservations_refunded_at
    ON public.ie_usage_reservations(refunded_at)
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

-- 관리자 이메일 조인 뷰가 view-owner 권한으로 RLS를 우회하거나 Data API의
-- 일반 역할에 노출되지 않도록 invoker 권한과 service-role 전용 ACL을 강제한다.
ALTER VIEW public.ie_usage_with_email
    SET (security_invoker = true, security_barrier = true);
ALTER VIEW public.ie_histories_with_email
    SET (security_invoker = true, security_barrier = true);
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

-- RLS를 우회해야 하는 멤버십 조회는 Data API에 노출되지 않는 스키마에
-- 두고, 호출자 자신의 auth.uid()만 검사한다.
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

DROP POLICY IF EXISTS workspace_member_read ON public.ie_workspaces;
CREATE POLICY workspace_member_read ON public.ie_workspaces FOR SELECT
    TO authenticated
    USING ((SELECT private.is_workspace_member(id)));

DROP POLICY IF EXISTS member_read ON public.ie_workspace_members;
CREATE POLICY member_read ON public.ie_workspace_members FOR SELECT
    TO authenticated
    USING ((SELECT private.is_workspace_member(workspace_id)));

-- 003~005의 초기 정책을 현재 사용자 JWT와 workspace 역할에 맞춰 수렴시킨다.
DROP POLICY IF EXISTS "Users can manage own snippets" ON public.ie_snippets;
DROP POLICY IF EXISTS snippets_manage_own ON public.ie_snippets;
CREATE POLICY snippets_manage_own ON public.ie_snippets FOR ALL
    TO authenticated
    USING ((SELECT auth.uid()) = user_id)
    WITH CHECK ((SELECT auth.uid()) = user_id);

DROP POLICY IF EXISTS "자신의 모니터만 조회"
    ON public.ie_channel_monitors;
DROP POLICY IF EXISTS "자신의 모니터만 수정"
    ON public.ie_channel_monitors;
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

-- 005의 기존 테이블에는 사용자 FK가 없었다. fresh schema와 동일한 삭제
-- 의미(RESTRICT/SET NULL)로 수렴하며, orphan이 있으면 조용히 삭제하지 않고
-- 마이그레이션을 실패시켜 운영자가 먼저 데이터를 확인하게 한다.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_catalog.pg_constraint
        WHERE conname = 'ie_workspace_contents_author_id_fkey'
          AND conrelid = 'public.ie_workspace_contents'::regclass
    ) THEN
        ALTER TABLE public.ie_workspace_contents
            ADD CONSTRAINT ie_workspace_contents_author_id_fkey
            FOREIGN KEY (author_id) REFERENCES auth.users(id)
            ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_catalog.pg_constraint
        WHERE conname = 'ie_workspace_contents_reviewer_id_fkey'
          AND conrelid = 'public.ie_workspace_contents'::regclass
    ) THEN
        ALTER TABLE public.ie_workspace_contents
            ADD CONSTRAINT ie_workspace_contents_reviewer_id_fkey
            FOREIGN KEY (reviewer_id) REFERENCES auth.users(id)
            ON DELETE SET NULL;
    END IF;
END $$;

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

-- 사용자는 quota 행을 직접 만들거나 수정하지 않는다. 자기 행 SELECT만 RLS로
-- 허용하고 생성·일일 리셋·관리자 변경은 검증된 RPC로 수렴시킨다.
DROP POLICY IF EXISTS "Users can insert own usage" ON public.ie_usage;
DROP POLICY IF EXISTS "Users can update own usage" ON public.ie_usage;

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

-- 유지보수 로직은 그대로 두되, 객체 가로채기를 막도록 빈 search_path와
-- 정규화된 객체명을 사용하고 서버 전용 역할만 호출할 수 있게 한다.
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

-- 랭킹 값은 서버가 검증한 실제 사용 흐름에서만 증가시킨다. 사용자 JWT의
-- 직접 RPC 반복 호출로 usage_count를 조작하지 못하게 service_role 전용으로 둔다.
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

-- 현재 ie_usage 행에는 과거 날짜가 보존되지 않으므로 멱등 예약 원장에서
-- 실제 환불되지 않은 일별 사용량을 집계한다.
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

-- 예약 원장은 앱 서버만 변경한다. 사용자 JWT에 이 RPC를 노출하면 새 멱등
-- 키를 반복 생성해 quota를 환불하면서 원장 행을 무제한 증폭할 수 있다.
REVOKE ALL ON FUNCTION public.reserve_usage_safe(UUID, TEXT, TEXT, TEXT, INT)
    FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.refund_usage_reservation_safe(UUID, TEXT, TEXT, TEXT)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.reserve_usage_safe(UUID, TEXT, TEXT, TEXT, INT)
    TO service_role;
GRANT EXECUTE ON FUNCTION public.refund_usage_reservation_safe(UUID, TEXT, TEXT, TEXT)
    TO service_role;

-- Data API 자동 노출 기본값이 켜진 기존 프로젝트와 꺼진 새 프로젝트가
-- 동일한 ACL로 수렴하도록 모든 앱 테이블 권한을 명시적으로 재설정한다.
-- anon 공개 테이블은 없고, 사용량 예약 원장은 SECURITY DEFINER RPC만 접근한다.
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

-- 모든 앱 테이블이 UUID 기본 키를 사용하므로 별도 시퀀스 권한은 없다.
-- DATA_API_TABLE_ACL_END

-- /ready가 데이터를 변경하지 않고 필수 스키마 적용 여부를 확인할 수 있는
-- 상수형, invoker 권한 RPC.
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

COMMIT;
