'use client';

import { memo, useState, useEffect, useCallback } from 'react';
import { Plus, Trash2, Radio, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';

interface Monitor {
  id: string;
  channel_id: string;
  channel_title: string;
  style_id: string;
  interval_minutes: number;
  is_active: boolean;
  last_checked_at: string | null;
  last_video_id: string | null;
  created_at: string;
}

/** 채널 모니터링 설정 패널 */
export const ChannelMonitorSettings = memo(function ChannelMonitorSettings() {
  const [monitors, setMonitors] = useState<Monitor[]>([]);
  const [loading, setLoading] = useState(true);
  const [channelInput, setChannelInput] = useState('');
  const [creating, setCreating] = useState(false);

  const fetchMonitors = useCallback(async () => {
    try {
      const res = await fetch('/api/channel-monitors');
      if (!res.ok) throw new Error('조회 실패');
      const data = await res.json();
      setMonitors(data.monitors || []);
    } catch {
      toast.error('채널 모니터 목록을 불러올 수 없습니다.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMonitors();
  }, [fetchMonitors]);

  /** 채널 URL/ID에서 채널 ID 추출 */
  function extractChannelId(input: string): string {
    const trimmed = input.trim();
    // https://www.youtube.com/channel/UC... 형식
    const channelMatch = trimmed.match(/youtube\.com\/channel\/(UC[\w-]+)/);
    if (channelMatch) return channelMatch[1];
    // @handle 또는 순수 ID
    if (trimmed.startsWith('UC') && trimmed.length >= 20) return trimmed;
    return trimmed;
  }

  async function handleCreate() {
    if (!channelInput.trim()) return;
    setCreating(true);
    try {
      const channelId = extractChannelId(channelInput);
      const res = await fetch('/api/channel-monitors', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ channel_id: channelId }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || '등록 실패');
      }
      toast.success('채널 모니터가 등록되었습니다.');
      setChannelInput('');
      fetchMonitors();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : '등록에 실패했습니다.');
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      const res = await fetch(`/api/channel-monitors/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error();
      toast.success('모니터가 삭제되었습니다.');
      setMonitors((prev) => prev.filter((m) => m.id !== id));
    } catch {
      toast.error('삭제에 실패했습니다.');
    }
  }

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold flex items-center gap-2">
        <Radio className="h-4 w-4" />
        채널 모니터링
      </h3>
      <p className="text-xs text-muted-foreground">
        YouTube 채널 URL 또는 ID를 등록하면 30분마다 신규 영상을 감지합니다.
      </p>

      {/* 입력 폼 */}
      <div className="flex gap-2">
        <Input
          placeholder="채널 URL 또는 ID (UC...)"
          value={channelInput}
          onChange={(e) => setChannelInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
          className="flex-1 h-8 text-sm"
        />
        <Button
          size="sm"
          className="h-8"
          onClick={handleCreate}
          disabled={creating || !channelInput.trim()}
        >
          {creating ? <Loader2 className="h-3 w-3 animate-spin" /> : <Plus className="h-3 w-3" />}
        </Button>
      </div>

      {/* 목록 */}
      {loading ? (
        <div className="flex justify-center py-4">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      ) : monitors.length === 0 ? (
        <p className="text-xs text-muted-foreground text-center py-4">
          등록된 모니터가 없습니다.
        </p>
      ) : (
        <ul className="space-y-2">
          {monitors.map((m) => (
            <li
              key={m.id}
              className="flex items-center justify-between rounded-md border px-3 py-2 text-sm"
            >
              <div className="min-w-0 flex-1">
                <div className="font-medium truncate">
                  {m.channel_title || m.channel_id}
                </div>
                <div className="text-xs text-muted-foreground">
                  스타일: {m.style_id} / {m.interval_minutes}분 간격
                  {m.last_checked_at && (
                    <> / 마지막 확인: {new Date(m.last_checked_at).toLocaleString('ko-KR')}</>
                  )}
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0 text-destructive hover:text-destructive"
                onClick={() => handleDelete(m.id)}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
});

export default ChannelMonitorSettings;
