'use client';

/**
 * NLP 분석 상세 대시보드 컴포넌트
 * - 토픽 분포: CSS 전용 가로 바 차트 (차트 라이브러리 불필요)
 * - 감성 측면별 목록
 * - 키워드 클라우드
 */

import type { NlpAnalysis } from '@/lib/types';

interface Props {
  analysis: NlpAnalysis;
}

// 감성 라벨/색상 설정
const SENTIMENT_LABEL: Record<string, { label: string; bar: string; text: string }> = {
  positive: { label: '긍정', bar: 'bg-emerald-500', text: 'text-emerald-600 dark:text-emerald-400' },
  neutral:  { label: '중립', bar: 'bg-slate-400',   text: 'text-slate-500 dark:text-slate-400'    },
  negative: { label: '부정', bar: 'bg-rose-500',    text: 'text-rose-600 dark:text-rose-400'      },
};

export default function AnalysisDashboard({ analysis }: Props) {
  const { keywords, sentiment, topics } = analysis;

  return (
    <div className="px-4 pb-4 space-y-5 border-t border-border/50 pt-3">
      {/* 토픽 분포 */}
      {topics.length > 0 && (
        <section>
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            토픽 분포
          </h4>
          <div className="space-y-2">
            {topics.map((t) => (
              <div key={t.topic} className="space-y-0.5">
                <div className="flex justify-between text-xs">
                  <span className="font-medium">{t.topic}</span>
                  <span className="text-muted-foreground">{Math.round(t.confidence * 100)}%</span>
                </div>
                <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary/70 transition-all"
                    style={{ width: `${Math.round(t.confidence * 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* 감성 측면별 분석 */}
      {sentiment.aspects.length > 0 && (
        <section>
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            측면별 감성
          </h4>
          <div className="space-y-1.5">
            {sentiment.aspects.map((a) => {
              const cfg = SENTIMENT_LABEL[a.sentiment] ?? SENTIMENT_LABEL.neutral;
              const pct = Math.round(((a.score + 1) / 2) * 100);
              return (
                <div key={a.aspect} className="flex items-center gap-2 text-xs">
                  <span className="w-28 shrink-0 truncate font-medium">{a.aspect}</span>
                  <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
                    <div
                      className={`h-full rounded-full ${cfg.bar} transition-all`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className={`w-8 text-right shrink-0 ${cfg.text}`}>{cfg.label}</span>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* 키워드 클라우드 */}
      {keywords.length > 0 && (
        <section>
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            키워드
          </h4>
          <div className="flex flex-wrap gap-1.5">
            {keywords.map((kw) => {
              // 관련도에 따라 폰트 크기 조정 (0.7~1.0 → text-xs~text-sm)
              const size = kw.relevance >= 0.8 ? 'text-sm' : 'text-xs';
              const weight = kw.relevance >= 0.8 ? 'font-semibold' : 'font-normal';
              return (
                <span
                  key={kw.word}
                  className={`inline-flex items-center px-2.5 py-1 rounded-full border border-border/60 bg-muted/40 ${size} ${weight} text-foreground/80`}
                  title={`관련도: ${Math.round(kw.relevance * 100)}%`}
                >
                  {kw.word}
                </span>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}
