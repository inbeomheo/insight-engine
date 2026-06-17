'use client';

import { useEffect } from 'react';
import { Settings, RotateCcw, Eye, EyeOff, FileText, BarChart3, Zap, Calendar, Star } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useDashboardStore, type DashboardWidget } from '@/stores/dashboardStore';

/** 위젯 타입별 아이콘 */
const WIDGET_ICONS: Record<string, typeof FileText> = {
  recent_content: FileText,
  usage_stats: BarChart3,
  quick_actions: Zap,
  upcoming_schedule: Calendar,
  quality_overview: Star,
};

/** 위젯 내부 렌더링 (플레이스홀더) */
function WidgetContent({ widget }: { widget: DashboardWidget }) {
  const Icon = WIDGET_ICONS[widget.type] || FileText;

  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 text-muted-foreground/50">
      <div className="flex h-10 w-10 items-center justify-center rounded-sm border border-border bg-muted">
        <Icon className="h-5 w-5" />
      </div>
      <span className="signal-meta text-[10px]">{widget.title}</span>
    </div>
  );
}

/** 커스터마이저블 대시보드 (F5-06) */
export default function CustomizableDashboard() {
  const { widgets, editMode, setEditMode, toggleWidget, resetLayout, hydrate } = useDashboardStore();

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  const visibleWidgets = widgets.filter((w) => w.visible);

  return (
    <div className="space-y-5">
      {/* 대시보드 헤더 */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="signal-meta mb-1 text-[10px] font-semibold text-primary">DASHBOARD</p>
          <h2 className="text-2xl font-bold tracking-[-0.02em]">대시보드</h2>
        </div>
        <div className="flex items-center gap-2">
          {editMode && (
            <Button variant="ghost" size="sm" className="signal-meta h-8 rounded-sm text-[10px] gap-1" onClick={resetLayout}>
              <RotateCcw className="h-3 w-3" />
              초기화
            </Button>
          )}
          <Button
            variant={editMode ? 'default' : 'ghost'}
            size="sm"
            className="signal-meta h-8 rounded-sm text-[10px] gap-1"
            onClick={() => setEditMode(!editMode)}
          >
            <Settings className="h-3 w-3" />
            {editMode ? '완료' : '편집'}
          </Button>
        </div>
      </div>

      {/* 편집 모드: 위젯 토글 리스트 */}
      {editMode && (
        <div className="flex flex-wrap gap-2 rounded-sm border border-border bg-muted/30 p-3">
          {widgets.map((w) => (
            <button
              key={w.id}
              aria-label={`${w.title} 위젯 ${w.visible ? '숨기기' : '표시'}`}
              className={`signal-meta flex items-center gap-1.5 rounded-full border px-2.5 py-1.5 text-[10px] transition-colors ${
                w.visible
                  ? 'bg-primary/10 border-primary/30 text-primary'
                  : 'bg-white border-border text-muted-foreground/60'
              }`}
              onClick={() => toggleWidget(w.id)}
            >
              {w.visible ? <Eye className="h-3 w-3" /> : <EyeOff className="h-3 w-3" />}
              {w.title}
            </button>
          ))}
        </div>
      )}

      {/* 위젯 그리드 */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {visibleWidgets.map((widget) => (
          <div
            key={widget.id}
            className={`min-h-[160px] rounded-sm border border-border bg-card p-4 shadow-none transition-colors
                        ${editMode ? 'ring-2 ring-primary/20 ring-dashed' : ''}
                        ${widget.w === 2 ? 'md:col-span-2' : ''}`}
          >
            {/* 위젯 헤더 */}
            <div className="flex items-center justify-between mb-3">
              <span className="signal-meta text-[10px] font-semibold text-muted-foreground/70">{widget.title}</span>
            </div>
            <WidgetContent widget={widget} />
          </div>
        ))}
      </div>

      {visibleWidgets.length === 0 && (
        <div className="rounded-sm border border-dashed border-border py-12 text-center text-sm text-muted-foreground/60">
          표시할 위젯이 없습니다. 편집 모드에서 위젯을 활성화하세요.
        </div>
      )}
    </div>
  );
}
