'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { Bell, CheckCheck, X, FileText, Users, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { apiUrl } from '@/lib/api';

interface Notification {
  id: string;
  type: string;
  title: string;
  message: string;
  link?: string;
  read: boolean;
  created_at: string;
}

/** 알림 타입별 아이콘 */
const TYPE_ICONS: Record<string, typeof Bell> = {
  generation_complete: FileText,
  workspace_invite: Users,
  usage_warning: AlertTriangle,
  system: Bell,
};

/** localStorage 기반 user_id 조회 (Supabase 인증 미연동 상태) */
function getUserId(): string {
  try {
    const profile = localStorage.getItem('ie_profile');
    if (profile) {
      const parsed = JSON.parse(profile);
      if (parsed.email) return parsed.email;
    }
  } catch { /* 파싱 실패 무시 */ }
  return 'anonymous';
}

/** 알림 센터 드롭다운 (F5-13) */
export default function NotificationCenter() {
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const pollRef = useRef<ReturnType<typeof setInterval>>(undefined);

  // 알림 로드
  const loadNotifications = useCallback(async () => {
    const uid = getUserId();
    try {
      const res = await fetch(apiUrl(`/api/notifications?user_id=${encodeURIComponent(uid)}&limit=20`));
      if (res.ok) {
        const data = await res.json();
        setNotifications(data.notifications || []);
        setUnreadCount(data.unread_count || 0);
      }
    } catch {
      // 로드 실패 무시
    }
  }, []);

  // 30초마다 알림 폴링
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadNotifications();
    pollRef.current = setInterval(loadNotifications, 30000);
    return () => clearInterval(pollRef.current);
  }, [loadNotifications]);

  // 알림 읽음 처리
  const markRead = useCallback(async (id: string) => {
    const uid = getUserId();
    try {
      await fetch(apiUrl(`/api/notifications/${id}/read?user_id=${encodeURIComponent(uid)}`), { method: 'POST' });
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read: true } : n)),
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch {
      // 실패 무시
    }
  }, []);

  // 전체 읽음 처리
  const markAllRead = useCallback(async () => {
    const uid = getUserId();
    try {
      await fetch(apiUrl('/api/notifications/read-all'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: uid }),
      });
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
      setUnreadCount(0);
    } catch {
      // 실패 무시
    }
  }, []);

  // 상대 시간 포맷
  const formatTime = useCallback((dateStr: string) => {
    const diff = Date.now() - new Date(dateStr).getTime();
    const minutes = Math.floor(diff / 60000);
    if (minutes < 1) return '방금';
    if (minutes < 60) return `${minutes}분 전`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}시간 전`;
    return `${Math.floor(hours / 24)}일 전`;
  }, []);

  return (
    <div className="relative">
      {/* 벨 버튼 */}
      <Button
        variant="ghost"
        size="icon"
        className="h-9 w-9 hover:bg-accent relative"
        onClick={() => setOpen(!open)}
        aria-label="알림"
      >
        <Bell className="h-[18px] w-[18px]" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 px-1
                           bg-red-500 text-white text-[10px] font-semibold rounded-full
                           flex items-center justify-center">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </Button>

      {/* 드롭다운 */}
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-2 w-[360px] bg-white dark:bg-zinc-800 border border-border/60
                          rounded-xl shadow-xl z-50 overflow-hidden"
               role="listbox" aria-expanded={open}>
            {/* 헤더 */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-border/40">
              <span className="text-sm font-semibold">알림</span>
              <div className="flex items-center gap-1">
                {unreadCount > 0 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs gap-1 text-muted-foreground"
                    onClick={markAllRead}
                  >
                    <CheckCheck className="h-3 w-3" />
                    모두 읽음
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={() => setOpen(false)}
                >
                  <X className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>

            {/* 알림 목록 */}
            <div className="max-h-[400px] overflow-y-auto">
              {notifications.length === 0 ? (
                <div className="py-12 text-center text-sm text-muted-foreground/50">
                  새로운 알림이 없습니다
                </div>
              ) : (
                notifications.map((n) => {
                  const Icon = TYPE_ICONS[n.type] || Bell;
                  return (
                    <div
                      key={n.id}
                      className={`flex items-start gap-3 px-4 py-3 border-b border-border/20
                                  cursor-pointer transition-colors hover:bg-accent/30 ${
                                    !n.read ? 'bg-primary/3' : ''
                                  }`}
                      onClick={() => !n.read && markRead(n.id)}
                    >
                      <div className={`mt-0.5 w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${
                        !n.read ? 'bg-primary/10 text-primary' : 'bg-muted/50 text-muted-foreground/40'
                      }`}>
                        <Icon className="h-3.5 w-3.5" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className={`text-xs font-medium ${!n.read ? 'text-foreground' : 'text-foreground/70'}`}>
                            {n.title}
                          </span>
                          {!n.read && (
                            <div className="w-1.5 h-1.5 rounded-full bg-primary shrink-0" />
                          )}
                        </div>
                        <p className="text-[11px] text-muted-foreground/60 mt-0.5 line-clamp-2">
                          {n.message}
                        </p>
                        <span className="text-[10px] text-muted-foreground/40 mt-1 block">
                          {formatTime(n.created_at)}
                        </span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
