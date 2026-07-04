'use client';

import { Rocket, FileText, Smartphone } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import type { CampaignPack } from '@/lib/types';

// 스타일 ID → 한국어 라벨
const STYLE_LABELS: Record<string, string> = {
  blog_seo: '블로그+SEO',
  summary: '요약',
  tutorial: '튜토리얼',
  qna: 'Q&A',
  app_ideas: '앱 아이디어',
  yozm_it: '요즘IT',
  brunch_essay: '브런치',
  naver_popular: '네이버',
  sns_post: 'SNS',
  newsletter: '뉴스레터',
  show_notes: '쇼노트',
  shorts_script: '쇼츠',
  geo_seo: 'GEO 검색',
  course: 'AI 코스',
  quiz: '퀴즈',
};

// 팩 ID → 아이콘 컴포넌트
const PACK_ICONS: Record<string, React.ElementType> = {
  full: Rocket,
  blog_focused: FileText,
  social: Smartphone,
};

interface CampaignPackSelectorProps {
  packs: Record<string, CampaignPack>;
  selectedPack: string | null;
  onSelect: (packId: string | null) => void;
}

export default function CampaignPackSelector({
  packs,
  selectedPack,
  onSelect,
}: CampaignPackSelectorProps) {
  const packEntries = Object.entries(packs);

  if (packEntries.length === 0) return null;

  return (
    <div className="space-y-2">
      <p className="text-xs font-medium text-[var(--text-secondary)]">
        캠페인 팩 (1회 사용량으로 다중 스타일 생성)
      </p>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
        {packEntries.map(([packId, pack]) => {
          const isSelected = selectedPack === packId;
          return (
            <button
              key={packId}
              type="button"
              onClick={() => onSelect(isSelected ? null : packId)}
              aria-label={`${pack.name} 캠페인 팩 선택`}
              className={`rounded-lg border p-3 text-left transition-all ${
                isSelected
                  ? 'border-[var(--accent-primary)] bg-[var(--accent-primary)]/10 ring-1 ring-[var(--accent-primary)]'
                  : 'border-[var(--border-primary)] hover:border-[var(--accent-primary)]/50'
              }`}
            >
              <div className="flex items-center gap-1.5 mb-1">
                {(() => { const Icon = PACK_ICONS[packId]; return Icon ? <Icon className="h-4 w-4 text-primary" /> : <Rocket className="h-4 w-4 text-muted-foreground" />; })()}
                <span className="text-sm font-semibold text-[var(--text-primary)]">
                  {pack.name}
                </span>
              </div>
              <p className="text-xs text-[var(--text-secondary)] mb-2">
                {pack.description}
              </p>
              <div className="flex flex-wrap gap-1">
                {pack.styles.map((styleId) => (
                  <Badge key={styleId} variant="outline" className="text-[10px] px-1.5 py-0">
                    {STYLE_LABELS[styleId] || styleId}
                  </Badge>
                ))}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
