-- 스니펫 라이브러리 테이블
CREATE TABLE IF NOT EXISTS ie_snippets (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    category TEXT NOT NULL DEFAULT 'general',
    label TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS 정책
ALTER TABLE ie_snippets ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own snippets" ON ie_snippets
    FOR ALL USING (auth.uid() = user_id);

-- 인덱스
CREATE INDEX idx_ie_snippets_user_id ON ie_snippets(user_id);
CREATE INDEX idx_ie_snippets_category ON ie_snippets(user_id, category);
