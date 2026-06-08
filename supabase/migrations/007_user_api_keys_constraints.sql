-- =============================================
-- Migration 007: ie_user_api_keys 제약/인덱스 보정
-- =============================================
-- 배경:
--   006(ie_user_api_keys)이 이미 적용된 환경은 `CREATE TABLE IF NOT EXISTS`가
--   스킵되므로, 006을 사후 수정해도 구(舊) 정의가 그대로 남는다. 구체적으로:
--     - 구 row_kind 제약: (key_hash IS NOT NULL OR encrypted_key IS NOT NULL)
--       → 두 도메인이 모두 채워진 모호한 행을 허용
--     - 구 유니크 인덱스: (user_id, provider, label) WHERE provider IS NOT NULL
--       → 부분 인덱스라 PostgREST upsert의 on_conflict 추론이 불가 → BYO 키
--         저장/회전이 "matching unique constraint 없음" 오류로 실패
--
--   본 마이그레이션은 위 두 가지를 기존 DB에도 멱등(idempotent)하게 보정한다.
--     (1) row_kind를 XOR로 강화 (정확히 하나만 non-null)
--     (2) (user_id, provider, label) 유니크 인덱스를 비부분(non-partial)으로 교체
--
-- 주의 (비파괴적):
--   - 본 마이그레이션은 데이터를 변경/삭제하지 않는다.
--   - (1) 추가 시 기존에 두 컬럼이 모두 채워졌거나 모두 비어있는 행이 있으면
--     ADD CONSTRAINT가 실패하고, (2)에서 (user_id, provider, label) 중복 행이
--     있으면 CREATE UNIQUE INDEX가 실패한다. 이는 정합성 문제를 드러내는 의도된
--     동작이며, 데이터 정리는 사용자 확인 하에 별도로 수행한다.
--
-- 관련: PR #22 (Codex 리뷰 — 006 in-place 수정은 신규 DB에만 반영되는 한계 보완)

DO $$
BEGIN
    -- 테이블이 없는 신규 환경에서는 006이 올바른 정의로 생성하므로 스킵.
    IF to_regclass('public.ie_user_api_keys') IS NULL THEN
        RAISE NOTICE 'ie_user_api_keys 없음 — 007 스킵 (006이 생성 담당)';
        RETURN;
    END IF;

    -- (1) row_kind XOR 제약 재정의
    ALTER TABLE ie_user_api_keys
        DROP CONSTRAINT IF EXISTS ie_user_api_keys_row_kind;
    ALTER TABLE ie_user_api_keys
        ADD CONSTRAINT ie_user_api_keys_row_kind CHECK (
            (key_hash IS NOT NULL AND encrypted_key IS NULL)
            OR (key_hash IS NULL AND encrypted_key IS NOT NULL)
        );

    -- (2) 부분 유니크 인덱스 → 비부분으로 교체
    DROP INDEX IF EXISTS uq_ie_user_api_keys_provider;
    CREATE UNIQUE INDEX uq_ie_user_api_keys_provider
        ON ie_user_api_keys(user_id, provider, label);
END $$;
