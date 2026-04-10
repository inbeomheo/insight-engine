'use client';

import { useState, useEffect, useCallback } from 'react';
import { Activity, FileText, Send, MessageSquare, CheckCircle } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useTranslation } from '@/hooks/useTranslation';
import { apiUrl } from '@/lib/api';

interface ActivityItem {
  id: string;
  user_email?: string;
  user_id: string;
  action: string;
  target_title: string;
  created_at: number;
}

const ACTION_ICONS: Record<string, typeof Activity> = {
  generated: FileText,
  published: Send,
  commented: MessageSquare,
  approved: CheckCircle,
};

const ACTION_COLORS: Record<string, string> = {
  generated: 'text-blue-500 bg-blue-50',
  published: 'text-green-500 bg-green-50',
  commented: 'text-amber-500 bg-amber-50',
  approved: 'text-purple-500 bg-purple-50',
};

interface ActivityFeedProps {
  workspaceId: string;
}

export default function ActivityFeed({ workspaceId }: ActivityFeedProps) {
  const [items, setItems] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const { t } = useTranslation();

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (!workspaceId) return;

    setLoading(true);
    fetch(apiUrl(`/api/workspaces/${workspaceId}/activity?limit=50`))
      .then((res) => res.ok ? res.json() : { items: [] })
      .then((data) => setItems(data.items || []))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [workspaceId]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const formatTime = useCallback(function formatTime(ts: number): string {
    const diff = Date.now() / 1000 - ts;
    if (diff < 60) return '방금 전';
    if (diff < 3600) return `${Math.floor(diff / 60)}분 전`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}시간 전`;
    return `${Math.floor(diff / 86400)}일 전`;
  }, []);

  if (loading) {
    return (
      <div className="p-4 text-center text-xs text-muted-foreground">
        {t('common.loading')}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="p-6 text-center">
        <Activity className="h-8 w-8 mx-auto mb-2 text-muted-foreground/30" />
        <p className="text-xs text-muted-foreground/60">{t('activity.noActivity')}</p>
      </div>
    );
  }

  return (
    <ScrollArea className="max-h-[400px]">
      <div className="space-y-1 p-2">
        {items.map((item) => {
          const Icon = ACTION_ICONS[item.action] || Activity;
          const colorClass = ACTION_COLORS[item.action] || 'text-muted-foreground bg-muted';

          return (
            <div key={item.id} className="flex items-start gap-3 px-3 py-2.5 rounded-lg hover:bg-muted/30 transition-colors">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${colorClass}`}>
                <Icon className="h-3.5 w-3.5" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs">
                  <span className="font-medium">{item.user_email || item.user_id}</span>
                  {' '}
                  <span className="text-muted-foreground">
                    {t(`activity.${item.action}` as 'activity.generated')}
                  </span>
                </p>
                <p className="text-[11px] text-muted-foreground/70 truncate">
                  {item.target_title}
                </p>
              </div>
              <span className="text-[10px] text-muted-foreground/50 shrink-0 mt-0.5">
                {formatTime(item.created_at)}
              </span>
            </div>
          );
        })}
      </div>
    </ScrollArea>
  );
}
