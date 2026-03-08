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
    <div className="h-full flex flex-col items-center justify-center text-muted-foreground/40 gap-2">
      <Icon className="h-6 w-6" />
      <span className="text-xs">{widget.title}</span>
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
    <div className="space-y-4">
      {/* 대시보드 헤더 */}
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold">대시보드</h2>
        <div className="flex items-center gap-2">
          {editMode && (
            <Button variant="ghost" size="sm" className="h-7 text-xs gap-1" onClick={resetLayout}>
              <RotateCcw className="h-3 w-3" />
              초기화
            </Button>
          )}
          <Button
            variant={editMode ? 'default' : 'ghost'}
            size="sm"
            className="h-7 text-xs gap-1"
            onClick={() => setEditMode(!editMode)}
          >
            <Settings className="h-3 w-3" />
            {editMode ? '완료' : '편집'}
          </Button>
        </div>
      </div>

      {/* 편집 모드: 위젯 토글 리스트 */}
      {editMode && (
        <div className="flex flex-wrap gap-2 p-3 bg-muted/30 rounded-lg border border-border/40">
          {widgets.map((w) => (
            <button
              key={w.id}
              aria-label={`${w.title} 위젯 ${w.visible ? '숨기기' : '표시'}`}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs transition-colors border ${
                w.visible
                  ? 'bg-primary/8 border-primary/20 text-primary'
                  : 'bg-white border-border/40 text-muted-foreground/60'
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
      <div className="grid grid-cols-3 gap-4">
        {visibleWidgets.map((widget) => (
          <div
            key={widget.id}
            className={`border border-border/60 rounded-xl bg-white p-4 min-h-[160px]
                        transition-all ${editMode ? 'ring-2 ring-primary/20 ring-dashed' : ''}
                        ${widget.w === 2 ? 'col-span-2' : ''}`}
          >
            {/* 위젯 헤더 */}
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-medium text-muted-foreground/70">{widget.title}</span>
            </div>
            <WidgetContent widget={widget} />
          </div>
        ))}
      </div>

      {visibleWidgets.length === 0 && (
        <div className="text-center py-12 text-sm text-muted-foreground/50">
          표시할 위젯이 없습니다. 편집 모드에서 위젯을 활성화하세요.
        </div>
      )}
    </div>
  );
}
