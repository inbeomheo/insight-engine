-- 사용량 환불 RPC. 기존 데이터는 삭제하지 않는다.
CREATE OR REPLACE FUNCTION increment_usage_safe(p_user_id UUID)
RETURNS JSON
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_new_count INT;
BEGIN
    UPDATE ie_usage
    SET usage_count = usage_count + 1,
        updated_at = NOW()
    WHERE user_id = p_user_id
    RETURNING usage_count INTO v_new_count;

    IF FOUND THEN
        RETURN json_build_object(
            'success', true,
            'new_count', v_new_count
        );
    ELSE
        RETURN json_build_object(
            'success', false,
            'reason', 'not_found'
        );
    END IF;
END;
$$ LANGUAGE plpgsql;

GRANT EXECUTE ON FUNCTION increment_usage_safe(UUID) TO authenticated;
