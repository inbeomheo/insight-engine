-- 채널 모니터링 테이블
CREATE TABLE IF NOT EXISTS ie_channel_monitors (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    channel_id text NOT NULL,
    channel_title text DEFAULT '',
    style_id text DEFAULT 'blog_seo',
    modifiers jsonb DEFAULT '{"length":"medium","writing_style":"conversational","language":"ko"}',
    interval_minutes int DEFAULT 30 CHECK (interval_minutes >= 10),
    last_checked_at timestamptz,
    last_video_id text,
    is_active boolean DEFAULT true,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- RLS
ALTER TABLE ie_channel_monitors ENABLE ROW LEVEL SECURITY;

CREATE POLICY "자신의 모니터만 조회" ON ie_channel_monitors
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "자신의 모니터만 수정" ON ie_channel_monitors
    FOR ALL USING (auth.uid() = user_id);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_channel_monitors_user ON ie_channel_monitors(user_id);
CREATE INDEX IF NOT EXISTS idx_channel_monitors_active ON ie_channel_monitors(is_active) WHERE is_active = true;
