'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { Users, Circle } from 'lucide-react';
import PresenceCursors from './PresenceCursors';
import { apiUrl } from '@/lib/api';

interface Participant {
  user_id: string;
  name: string;
  cursor_position: number;
  color: string;
}

interface CollaborativeEditorProps {
  contentId: string;
  initialContent?: string;
  userId?: string;
  userName?: string;
}

/** 실시간 협업 편집기 (F5-02) — 폴링 기반 동기화 */
export default function CollaborativeEditor({
  contentId,
  initialContent = '',
  userId = 'anonymous',
  userName = '',
}: CollaborativeEditorProps) {
  const [content, setContent] = useState(initialContent);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [version, setVersion] = useState(0);
  const [connected, setConnected] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval>>(undefined);

  // 세션 생성/참가
  useEffect(() => {
    let currentSessionId: string | null = null;
    async function joinSession() {
      try {
        const res = await fetch(apiUrl('/api/collab/session'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content_id: contentId, user_id: userId, user_name: userName }),
        });
        if (!res.ok) return;
        const data = await res.json();
        currentSessionId = data.session_id;
        setSessionId(data.session_id);
        if (data.content) setContent(data.content);
        setVersion(data.version);
        setParticipants(data.participants || []);
        setConnected(true);
      } catch {
        // 오프라인 모드로 폴백
      }
    }
    joinSession();

    return () => {
      // 세션 퇴장
      if (currentSessionId) {
        fetch(apiUrl(`/api/collab/session/${currentSessionId}/leave`), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: userId }),
        }).catch(() => {});
      }
    };
  }, [contentId, userId, userName]);

  // 폴링으로 세션 상태 동기화 (2초 간격)
  useEffect(() => {
    if (!sessionId) return;

    pollRef.current = setInterval(async () => {
      try {
        // 하트비트
        await fetch(apiUrl(`/api/collab/session/${sessionId}/heartbeat`), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: userId,
            cursor_position: textareaRef.current?.selectionStart ?? 0,
          }),
        });

        // 세션 상태 폴링
        const res = await fetch(apiUrl(`/api/collab/session/${sessionId}`));
        if (!res.ok) return;
        const data = await res.json();
        setParticipants(data.participants || []);

        // 다른 사용자가 수정한 경우에만 콘텐츠 업데이트
        if (data.version > version) {
          setContent(data.content);
          setVersion(data.version);
        }
      } catch {
        // 폴링 실패 무시
      }
    }, 2000);

    return () => clearInterval(pollRef.current);
  }, [sessionId, version, userId]);

  // 콘텐츠 변경 시 서버로 전송
  const handleChange = useCallback(
    async (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const newContent = e.target.value;
      setContent(newContent);

      if (!sessionId) return;
      try {
        const res = await fetch(apiUrl(`/api/collab/session/${sessionId}/update`), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: userId,
            content: newContent,
            cursor_position: e.target.selectionStart,
          }),
        });
        if (res.ok) {
          const data = await res.json();
          setVersion(data.version);
          setParticipants(data.participants || []);
        }
      } catch {
        // 전송 실패 시 로컬 변경 유지
      }
    },
    [sessionId, userId],
  );

  const otherParticipants = participants.filter((p) => p.user_id !== userId);

  return (
    <div className="relative border rounded-xl overflow-hidden bg-white">
      {/* 참가자 표시 바 */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-border/40 bg-muted/20">
        <Users className="h-3.5 w-3.5 text-muted-foreground/60" />
        <span className="text-xs text-muted-foreground/60">
          {participants.length}명 참여 중
        </span>
        <div className="flex items-center gap-1 ml-auto">
          {participants.map((p) => (
            <div
              key={p.user_id}
              className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px]"
              style={{ backgroundColor: `${p.color}15`, color: p.color }}
            >
              <Circle className="h-2 w-2 fill-current" />
              {p.name}
            </div>
          ))}
        </div>
        {connected && (
          <div className="flex items-center gap-1 text-[10px] text-green-600">
            <Circle className="h-1.5 w-1.5 fill-current" />
            연결됨
          </div>
        )}
      </div>

      {/* 에디터 영역 */}
      <div className="relative">
        <textarea
          ref={textareaRef}
          value={content}
          onChange={handleChange}
          className="w-full min-h-[400px] p-4 text-sm font-mono leading-relaxed
                     bg-transparent outline-none resize-y"
          placeholder="콘텐츠를 입력하세요..."
        />
        <PresenceCursors participants={otherParticipants} />
      </div>
    </div>
  );
}
