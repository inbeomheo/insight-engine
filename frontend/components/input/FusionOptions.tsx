'use client';

import { useSettingsStore } from '@/stores/settingsStore';

export default function FusionOptions() {
  const {
    generationMode,
    enableWebResearch, setEnableWebResearch,
    enableDeepComments, setEnableDeepComments,
  } = useSettingsStore();

  if (generationMode !== 'fusion') return null;

  return (
    <div className="mt-2 space-y-2 rounded-lg border border-[var(--border-primary)] p-3" role="group" aria-label="퓨전 옵션">
      <p className="text-xs font-medium text-[var(--text-secondary)]">퓨전 옵션</p>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={enableWebResearch}
          onChange={(e) => setEnableWebResearch(e.target.checked)}
          className="rounded"
        />
        <span>웹 리서치 (관련 기사 자동 검색)</span>
      </label>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={enableDeepComments}
          onChange={(e) => setEnableDeepComments(e.target.checked)}
          className="rounded"
        />
        <span>댓글 심층 분석 (FAQ, 팩트체크 포함)</span>
      </label>
      <p className="text-xs text-[var(--text-tertiary)]">
        퓨전 분석은 2~5개 URL이 필요합니다
      </p>
    </div>
  );
}
