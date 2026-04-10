'use client';

import { useState, useMemo } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  CheckSquare,
  Lightbulb,
  GitBranch,
  HelpCircle,
  Clock,
  ExternalLink,
  Filter,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import type {
  VideoEventType,
  VideoEvent,
  ActionItemEvent,
  EventSummary,
} from '@/lib/types';

// EventType alias (컴포넌트 내부 편의)
type EventType = VideoEventType;

// =============================================
// 이벤트 타입별 스타일 설정
// =============================================

const EVENT_CONFIG: Record<
  EventType,
  {
    label: string;
    icon: React.FC<{ className?: string }>;
    badgeClass: string;
    dotClass: string;
    borderClass: string;
  }
> = {
  action_item: {
    label: '액션 아이템',
    icon: CheckSquare,
    badgeClass: 'bg-red-100 text-red-700 border-red-200 dark:bg-red-950/40 dark:text-red-400 dark:border-red-800/50',
    dotClass: 'bg-red-500',
    borderClass: 'border-l-red-400 dark:border-l-red-600',
  },
  key_point: {
    label: '핵심 포인트',
    icon: Lightbulb,
    badgeClass: 'bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-950/40 dark:text-blue-400 dark:border-blue-800/50',
    dotClass: 'bg-blue-500',
    borderClass: 'border-l-blue-400 dark:border-l-blue-600',
  },
  decision: {
    label: '결정 사항',
    icon: GitBranch,
    badgeClass: 'bg-green-100 text-green-700 border-green-200 dark:bg-green-950/40 dark:text-green-400 dark:border-green-800/50',
    dotClass: 'bg-green-500',
    borderClass: 'border-l-green-400 dark:border-l-green-600',
  },
  question: {
    label: '질문',
    icon: HelpCircle,
    badgeClass: 'bg-orange-100 text-orange-700 border-orange-200 dark:bg-orange-950/40 dark:text-orange-400 dark:border-orange-800/50',
    dotClass: 'bg-orange-500',
    borderClass: 'border-l-orange-400 dark:border-l-orange-600',
  },
};

// 우선순위 배지 스타일
const PRIORITY_STYLES: Record<ActionItemEvent['priority'], string> = {
  high: 'bg-red-50 text-red-600 border-red-200 dark:bg-red-950/30 dark:text-red-400',
  medium: 'bg-yellow-50 text-yellow-600 border-yellow-200 dark:bg-yellow-950/30 dark:text-yellow-400',
  low: 'bg-gray-50 text-gray-500 border-gray-200 dark:bg-gray-800/50 dark:text-gray-400',
};

const PRIORITY_LABELS: Record<ActionItemEvent['priority'], string> = {
  high: '높음',
  medium: '보통',
  low: '낮음',
};

// =============================================
// 타임스탬프 → YouTube 딥링크 변환
// =============================================

function timestampToSeconds(timestamp: string): number {
  if (!timestamp) return 0;
  const parts = timestamp.split(':').map(Number);
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
  if (parts.length === 2) return parts[0] * 60 + parts[1];
  return 0;
}

function buildYoutubeDeeplink(videoUrl: string, timestamp: string): string {
  if (!videoUrl || !timestamp) return '';
  const seconds = timestampToSeconds(timestamp);
  const separator = videoUrl.includes('?') ? '&' : '?';
  return `${videoUrl}${separator}t=${seconds}`;
}

// =============================================
// 개별 이벤트 카드
// =============================================

function EventCard({ event, videoUrl }: { event: VideoEvent; videoUrl?: string }) {
  const [expanded, setExpanded] = useState(false);
  const config = EVENT_CONFIG[event.type];
  const Icon = config.icon;
  const deeplink = videoUrl && event.timestamp ? buildYoutubeDeeplink(videoUrl, event.timestamp) : '';

  return (
    <div className={`relative pl-4 border-l-2 ${config.borderClass} py-1`}>
      {/* 타임라인 점 */}
      <div className={`absolute -left-[5px] top-3 w-2 h-2 rounded-full ${config.dotClass}`} />

      <div className="bg-card border border-border/40 rounded-lg p-3 hover:border-border/70 transition-colors">
        {/* 헤더 */}
        <div className="flex items-start gap-2">
          <Icon className="h-4 w-4 mt-0.5 shrink-0 text-muted-foreground" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium leading-snug">{event.content}</p>

            {/* 메타 정보 */}
            <div className="flex items-center flex-wrap gap-1.5 mt-1.5">
              {/* 타임스탬프 */}
              {event.timestamp && (
                deeplink ? (
                  <a
                    href={deeplink}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-primary hover:underline font-mono"
                  >
                    <Clock className="h-3 w-3" />
                    {event.timestamp}
                    <ExternalLink className="h-2.5 w-2.5" />
                  </a>
                ) : (
                  <span className="inline-flex items-center gap-1 text-xs text-muted-foreground font-mono">
                    <Clock className="h-3 w-3" />
                    {event.timestamp}
                  </span>
                )
              )}

              {/* 액션 아이템 우선순위 */}
              {event.type === 'action_item' && (
                <Badge variant="outline" className={`text-[10px] px-1.5 py-0 ${PRIORITY_STYLES[event.priority]}`}>
                  {PRIORITY_LABELS[event.priority]}
                </Badge>
              )}

              {/* 핵심 포인트 중요도 */}
              {event.type === 'key_point' && (
                <span className="text-xs text-muted-foreground">
                  중요도 {Math.round(event.importance * 100)}%
                </span>
              )}

              {/* 질문 상태 */}
              {event.type === 'question' && (
                <Badge
                  variant="outline"
                  className={`text-[10px] px-1.5 py-0 ${
                    event.status === 'resolved'
                      ? 'bg-green-50 text-green-600 border-green-200 dark:bg-green-950/30 dark:text-green-400'
                      : 'bg-orange-50 text-orange-600 border-orange-200 dark:bg-orange-950/30 dark:text-orange-400'
                  }`}
                >
                  {event.status === 'resolved' ? '해결됨' : '미해결'}
                </Badge>
              )}

              {/* 결정 사항 이해관계자 */}
              {event.type === 'decision' && event.stakeholders.length > 0 && (
                <span className="text-xs text-muted-foreground">
                  {event.stakeholders.join(', ')}
                </span>
              )}
            </div>
          </div>

          {/* 상세 보기 토글 */}
          {event.context && (
            <button
              type="button"
              onClick={() => setExpanded((v) => !v)}
              className="shrink-0 text-muted-foreground hover:text-foreground transition-colors"
              aria-label={expanded ? '상세 닫기' : '상세 보기'}
            >
              {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            </button>
          )}
        </div>

        {/* 컨텍스트 (펼쳐진 경우) */}
        {expanded && event.context && (
          <p className="mt-2 text-xs text-muted-foreground leading-relaxed pl-6 border-t border-border/30 pt-2">
            {event.context}
          </p>
        )}
      </div>
    </div>
  );
}

// =============================================
// 이벤트 타임라인 메인 컴포넌트
// =============================================

interface EventTimelineProps {
  events: VideoEvent[];
  summary?: EventSummary;
  videoUrl?: string;
}

type FilterType = 'all' | EventType;

export default function EventTimeline({ events, summary, videoUrl }: EventTimelineProps) {
  const [activeFilter, setActiveFilter] = useState<FilterType>('all');

  const filteredEvents = useMemo(() => {
    if (activeFilter === 'all') return events;
    return events.filter((e) => e.type === activeFilter);
  }, [events, activeFilter]);

  if (!events || events.length === 0) {
    return (
      <div className="text-center py-8 text-sm text-muted-foreground">
        추출된 이벤트가 없습니다.
      </div>
    );
  }

  // 필터 버튼 목록 (이벤트가 있는 타입만)
  const filterOptions: { value: FilterType; label: string; count: number }[] = [
    { value: 'all', label: '전체', count: events.length },
    ...(Object.keys(EVENT_CONFIG) as EventType[])
      .map((type) => ({
        value: type as FilterType,
        label: EVENT_CONFIG[type].label,
        count: events.filter((e) => e.type === type).length,
      }))
      .filter((opt) => opt.count > 0),
  ];

  return (
    <div className="space-y-4">
      {/* 요약 통계 */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {(Object.keys(EVENT_CONFIG) as EventType[]).map((type) => {
            const count = summary.by_type[type] ?? 0;
            if (count === 0) return null;
            const config = EVENT_CONFIG[type];
            const Icon = config.icon;
            return (
              <div
                key={type}
                className="flex items-center gap-2 bg-muted/30 rounded-lg px-3 py-2"
              >
                <Icon className="h-4 w-4 text-muted-foreground shrink-0" />
                <div className="min-w-0">
                  <p className="text-xs text-muted-foreground truncate">{config.label}</p>
                  <p className="text-sm font-semibold">{count}개</p>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 타입별 필터 */}
      <div className="flex items-center gap-1.5 flex-wrap">
        <Filter className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
        {filterOptions.map((opt) => (
          <Button
            key={opt.value}
            variant={activeFilter === opt.value ? 'secondary' : 'ghost'}
            size="sm"
            className="h-7 text-xs px-2.5"
            onClick={() => setActiveFilter(opt.value)}
          >
            {opt.label}
            <span className="ml-1 text-muted-foreground">({opt.count})</span>
          </Button>
        ))}
      </div>

      {/* 타임라인 */}
      <div className="space-y-3 pl-2">
        {filteredEvents.map((event, idx) => (
          <EventCard
            key={`${event.type}-${idx}`}
            event={event}
            videoUrl={videoUrl}
          />
        ))}
      </div>
    </div>
  );
}
