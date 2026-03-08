'use client';

import { memo, useState, useEffect, useCallback } from 'react';
import { Plus, Trash2, Rss, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import { useApiCall } from '@/hooks/useApiCall';
import { apiUrl } from '@/lib/api';

interface Subscription {
  id: string;
  feed_url: string;
  title: string;
  created_at: string;
  last_checked_at: string | null;
}

/** RSS 피드 구독 관리 패널 */
export const RssSubscription = memo(function RssSubscription() {
  const [subs, setSubs] = useState<Subscription[]>([]);
  const [feedInput, setFeedInput] = useState('');

  const listCall = useApiCall<{ subscriptions: Subscription[] }>();
  const subscribeCall = useApiCall<{ error?: string }>();
  const unsubscribeCall = useApiCall<void>();

  const fetchSubs = useCallback(async () => {
    const result = await listCall.execute(async () => {
      const res = await fetch(apiUrl('/api/rss/list'));
      if (!res.ok) throw new Error('조회 실패');
      return res.json();
    }, 'RSS 구독 목록을 불러올 수 없습니다.');
    if (result) setSubs(result.subscriptions || []);
  }, [listCall.execute]);

  useEffect(() => {
    fetchSubs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSubscribe() {
    const url = feedInput.trim();
    if (!url) return;

    const result = await subscribeCall.execute(async () => {
      const res = await fetch(apiUrl('/api/rss/subscribe'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ feed_url: url }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || '구독 실패');
      toast.success('RSS 피드가 구독되었습니다.');
      setFeedInput('');
      fetchSubs();
      return data;
    }, '구독에 실패했습니다.');
  }

  async function handleUnsubscribe(id: string) {
    await unsubscribeCall.execute(async () => {
      const res = await fetch(apiUrl(`/api/rss/unsubscribe/${id}`), { method: 'DELETE' });
      if (!res.ok) throw new Error();
      toast.success('구독이 해제되었습니다.');
      setSubs((prev) => prev.filter((s) => s.id !== id));
    }, '구독 해제에 실패했습니다.');
  }

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold flex items-center gap-2">
        <Rss className="h-4 w-4" />
        RSS 피드 구독
      </h3>
      <p className="text-xs text-muted-foreground">
        RSS/Atom 피드 URL을 등록하면 30분마다 새 글을 감지합니다.
      </p>

      {/* 입력 폼 */}
      <div className="flex gap-2">
        <Input
          placeholder="RSS 피드 URL (예: https://example.com/feed)"
          value={feedInput}
          onChange={(e) => setFeedInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSubscribe()}
          className="flex-1 h-8 text-sm"
        />
        <Button
          size="sm"
          className="h-8"
          onClick={handleSubscribe}
          disabled={subscribeCall.isLoading || !feedInput.trim()}
        >
          {subscribeCall.isLoading ? <Loader2 className="h-3 w-3 animate-spin" /> : <Plus className="h-3 w-3" />}
        </Button>
      </div>

      {/* 목록 */}
      {listCall.isLoading ? (
        <div className="flex justify-center py-4">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      ) : subs.length === 0 ? (
        <p className="text-xs text-muted-foreground text-center py-4">
          등록된 구독이 없습니다.
        </p>
      ) : (
        <ul className="space-y-2">
          {subs.map((s) => (
            <li
              key={s.id}
              className="flex items-center justify-between rounded-md border px-3 py-2 text-sm"
            >
              <div className="min-w-0 flex-1">
                <div className="font-medium truncate">{s.title}</div>
                <div className="text-xs text-muted-foreground truncate">
                  {s.feed_url}
                  {s.last_checked_at && (
                    <> / 마지막 확인: {new Date(s.last_checked_at).toLocaleString('ko-KR')}</>
                  )}
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0 text-destructive hover:text-destructive"
                onClick={() => handleUnsubscribe(s.id)}
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

export default RssSubscription;
