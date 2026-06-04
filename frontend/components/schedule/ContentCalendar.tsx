'use client';

import { useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight, Trash2, ExternalLink, AlertCircle, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import type { ScheduledPost } from '@/lib/types';

interface ContentCalendarProps {
  schedules: ScheduledPost[];
  onDelete: (id: string) => boolean | void | Promise<boolean | void>;
}

const DAYS = ['일', '월', '화', '수', '목', '금', '토'];

function getMonthDays(year: number, month: number) {
  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const prevDays = new Date(year, month, 0).getDate();
  const cells: Array<{ day: number; current: boolean; date: Date }> = [];

  for (let i = firstDay - 1; i >= 0; i--) {
    const day = prevDays - i;
    cells.push({ day, current: false, date: new Date(year, month - 1, day) });
  }

  for (let day = 1; day <= daysInMonth; day++) {
    cells.push({ day, current: true, date: new Date(year, month, day) });
  }

  const remaining = 42 - cells.length;
  for (let day = 1; day <= remaining; day++) {
    cells.push({ day, current: false, date: new Date(year, month + 1, day) });
  }

  return cells;
}

function formatDateKey(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

const STATUS_STYLE: Record<string, { label: string; className: string }> = {
  pending: { label: '대기', className: 'bg-yellow-500/10 text-yellow-600 border-yellow-500/20' },
  published: { label: '발행됨', className: 'bg-green-500/10 text-green-600 border-green-500/20' },
  failed: { label: '실패', className: 'bg-red-500/10 text-red-600 border-red-500/20' },
  cancelled: { label: '취소', className: 'bg-muted text-muted-foreground border-border' },
};

const PLUGIN_LABELS: Record<string, string> = {
  wordpress: 'WordPress',
  naver_blog: '네이버 블로그',
  naver: '네이버 블로그',
  medium: 'Medium',
  substack: 'Substack',
};

const PUBLISH_STATUS_LABELS: Record<string, string> = {
  draft: '임시글',
  publish: '공개',
  pending: '검토 대기',
  private: '비공개',
};

function pluginLabel(pluginId: string) {
  return PLUGIN_LABELS[pluginId] ?? pluginId;
}

function formatTagSummary(value: unknown) {
  const rawTags = Array.isArray(value)
    ? value.filter((tag): tag is string => typeof tag === 'string')
    : typeof value === 'string'
      ? value.split(',')
      : [];

  return rawTags
    .map((tag) => tag.trim())
    .filter(Boolean)
    .slice(0, 5)
    .map((tag) => (tag.startsWith('#') ? tag : `#${tag}`))
    .join(' ');
}

function pluginOptionSummary(post: ScheduledPost) {
  const options = post.plugin_options ?? {};
  const parts: string[] = [];
  const status = typeof options.status === 'string' ? options.status : '';
  const siteUrl = typeof options.site_url === 'string' ? options.site_url : '';
  const username = typeof options.username === 'string' ? options.username : '';
  const blogId = typeof options.blog_id === 'string' ? options.blog_id : '';
  const category = typeof options.category === 'string' ? options.category : '';
  const tags = formatTagSummary(options.tags);

  if (status) parts.push(PUBLISH_STATUS_LABELS[status] ?? status);
  if (siteUrl) parts.push(siteUrl.replace(/^https?:\/\//, '').replace(/\/$/, ''));
  if (username) parts.push(`작성자 ${username}`);
  if (blogId) parts.push(`블로그 ${blogId}`);
  if (category) parts.push(`카테고리 ${category}`);
  if (tags) parts.push(tags);

  return parts.join(' · ');
}

export default function ContentCalendar({ schedules, onDelete }: ContentCalendarProps) {
  const [viewDate, setViewDate] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ScheduledPost | null>(null);
  const [deleteError, setDeleteError] = useState('');
  const [deleteBusy, setDeleteBusy] = useState(false);

  const year = viewDate.getFullYear();
  const month = viewDate.getMonth();
  const cells = useMemo(() => getMonthDays(year, month), [year, month]);
  const todayKey = formatDateKey(new Date());

  const schedulesByDate = useMemo(() => {
    const map: Record<string, ScheduledPost[]> = {};
    for (const schedule of schedules) {
      const date = new Date(schedule.scheduled_at);
      const key = formatDateKey(date);
      (map[key] ??= []).push(schedule);
    }
    return map;
  }, [schedules]);

  const selectedPosts = selectedDate ? (schedulesByDate[selectedDate] || []) : [];

  function prevMonth() {
    setViewDate(new Date(year, month - 1, 1));
    setSelectedDate(null);
  }

  function nextMonth() {
    setViewDate(new Date(year, month + 1, 1));
    setSelectedDate(null);
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    setDeleteBusy(true);
    setDeleteError('');
    try {
      const ok = await onDelete(deleteTarget.id);
      if (ok === false) {
        setDeleteError('예약 삭제 실패 · 다시 시도해주세요.');
        return;
      }
      setDeleteError('');
      setDeleteTarget(null);
    } catch {
      setDeleteError('예약 삭제 실패 · 다시 시도해주세요.');
    } finally {
      setDeleteBusy(false);
    }
  }

  return (
    <div data-testid="content-calendar" aria-labelledby="calendar-current-month" className="space-y-4">
      <div className="flex items-center justify-between">
        <Button data-testid="calendar-prev-month" aria-label="이전 달 보기" aria-controls="calendar-grid" variant="ghost" size="icon" onClick={prevMonth}>
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <h3 id="calendar-current-month" data-testid="calendar-current-month" aria-live="polite" className="text-lg font-semibold">
          {year}년 {month + 1}월
        </h3>
        <Button data-testid="calendar-next-month" aria-label="다음 달 보기" aria-controls="calendar-grid" variant="ghost" size="icon" onClick={nextMonth}>
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>

      <div className="grid grid-cols-7 gap-px text-center text-xs font-medium text-muted-foreground" aria-hidden="true">
        {DAYS.map((day) => (
          <div key={day} className="py-2">{day}</div>
        ))}
      </div>

      <div id="calendar-grid" data-testid="calendar-grid" role="grid" aria-labelledby="calendar-current-month" className="grid grid-cols-7 gap-px bg-border rounded-lg overflow-hidden">
        {cells.map((cell, index) => {
          const key = formatDateKey(cell.date);
          const posts = schedulesByDate[key] || [];
          const isToday = key === todayKey;
          const isSelected = key === selectedDate;

          return (
            <button
              key={`${key}-${index}`}
              type="button"
              role="gridcell"
              onClick={() => setSelectedDate(isSelected ? null : key)}
              aria-label={`${key} 날짜 선택`}
              aria-selected={isSelected}
              className={[
                'relative min-h-[72px] p-1.5 text-left bg-background transition-colors',
                !cell.current && 'opacity-40',
                isSelected && 'ring-2 ring-primary ring-inset',
                'hover:bg-muted/50',
              ]
                .filter(Boolean)
                .join(' ')}
            >
              <span
                className={[
                  'inline-flex items-center justify-center text-xs w-6 h-6 rounded-full',
                  isToday && 'bg-primary text-primary-foreground font-bold',
                ]
                  .filter(Boolean)
                  .join(' ')}
              >
                {cell.day}
              </span>
              {posts.length > 0 && (
                <div className="flex flex-wrap gap-0.5 mt-1" aria-hidden="true">
                  {posts.slice(0, 3).map((post) => (
                    <span
                      key={post.id}
                      className={[
                        'block w-1.5 h-1.5 rounded-full',
                        post.status === 'pending' && 'bg-yellow-500',
                        post.status === 'published' && 'bg-green-500',
                        post.status === 'failed' && 'bg-red-500',
                        post.status === 'cancelled' && 'bg-muted-foreground',
                      ]
                        .filter(Boolean)
                        .join(' ')}
                    />
                  ))}
                  {posts.length > 3 && (
                    <span className="text-[10px] text-muted-foreground">+{posts.length - 3}</span>
                  )}
                </div>
              )}
            </button>
          );
        })}
      </div>

      {selectedDate && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">
              {selectedDate} 예약 ({selectedPosts.length}건)
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {selectedPosts.length === 0 ? (
              <p className="text-sm text-muted-foreground">이 날짜에는 예약이 없습니다.</p>
            ) : (
              selectedPosts.map((post) => {
                const style = STATUS_STYLE[post.status] || STATUS_STYLE.pending;
                const time = new Date(post.scheduled_at).toLocaleTimeString('ko-KR', {
                  hour: '2-digit',
                  minute: '2-digit',
                });

                return (
                  <div
                    key={post.id}
                    className="flex items-start justify-between gap-2 rounded-md border p-3"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant="outline" className={`text-[10px] px-1.5 py-0 ${style.className}`}>
                          {post.status === 'published' && <CheckCircle2 className="h-3 w-3 mr-0.5" />}
                          {post.status === 'failed' && <AlertCircle className="h-3 w-3 mr-0.5" />}
                          {style.label}
                        </Badge>
                        <span className="text-xs text-muted-foreground">{time}</span>
                      </div>
                      <p className="text-sm font-medium truncate">{post.title}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        <span data-testid="calendar-plugin-label">{pluginLabel(post.target_plugin)}</span>
                        {pluginOptionSummary(post) && (
                          <span> · {pluginOptionSummary(post)}</span>
                        )}
                      </p>
                      {post.error_message && (
                        <p className="text-xs text-red-500 mt-1">{post.error_message}</p>
                      )}
                      {post.published_url && (
                        <a
                          href={post.published_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-xs text-primary hover:underline mt-1"
                        >
                          <ExternalLink className="h-3 w-3" />
                          발행 링크
                        </a>
                      )}
                    </div>
                    {post.status === 'pending' && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 shrink-0 text-destructive hover:text-destructive"
                        data-testid="calendar-delete-schedule"
                        aria-label={`${post.title} 예약 삭제`}
                        onClick={() => {
                          setDeleteError('');
                          setDeleteTarget(post);
                        }}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    )}
                  </div>
                );
              })
            )}
          </CardContent>
        </Card>
      )}

      <Dialog
        open={Boolean(deleteTarget)}
        onOpenChange={(open) => {
          if (!open && !deleteBusy) {
            setDeleteTarget(null);
            setDeleteError('');
          }
        }}
      >
        <DialogContent
          data-testid="calendar-delete-dialog"
          aria-labelledby="calendar-delete-title"
          aria-describedby="calendar-delete-description"
          className="max-w-sm"
        >
          <DialogHeader>
            <DialogTitle>
              <span id="calendar-delete-title" data-testid="calendar-delete-title">
                예약 삭제
              </span>
            </DialogTitle>
            <DialogDescription>
              <span id="calendar-delete-description" data-testid="calendar-delete-description">
                {deleteTarget ? `“${deleteTarget.title}” 예약을 삭제할까요? 이 작업은 되돌릴 수 없습니다.` : '예약을 삭제할까요?'}
              </span>
            </DialogDescription>
          </DialogHeader>
          {deleteError && (
            <p data-testid="calendar-delete-error" className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {deleteError}
            </p>
          )}
          <DialogFooter>
            <Button
              data-testid="calendar-delete-cancel"
              aria-label="예약 삭제 취소"
              variant="ghost"
              disabled={deleteBusy}
              onClick={() => {
                setDeleteError('');
                setDeleteTarget(null);
              }}
            >
              취소
            </Button>
            <Button data-testid="calendar-delete-confirm" aria-label="예약 영구 삭제" variant="destructive" disabled={deleteBusy} onClick={confirmDelete}>
              {deleteBusy ? '삭제 중...' : '삭제하기'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
