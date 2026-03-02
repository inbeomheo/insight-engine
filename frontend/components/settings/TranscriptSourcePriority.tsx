'use client';

import { memo, useState, useCallback, useEffect } from 'react';
import { GripVertical } from 'lucide-react';

/** 자막 소스 항목 */
interface SourceItem {
  id: string;
  label: string;
  description: string;
}

/** 기본 자막 소스 우선순위 */
const DEFAULT_SOURCES: SourceItem[] = [
  { id: 'youtube_api', label: '공식 자막 API', description: '무료, 가장 정확' },
  { id: 'watch_page', label: '웹 페이지 추출', description: '무료, 폴백' },
  { id: 'supadata', label: '외부 API (Supadata)', description: '유료, API 키 필요' },
  { id: 'whisper', label: '음성 인식 (Whisper)', description: '로컬, 느림' },
];

const STORAGE_KEY = 'ie_transcript_priority';

/** localStorage에서 우선순위 로드 */
function loadPriority(): SourceItem[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return DEFAULT_SOURCES;

    const ids: string[] = JSON.parse(stored);
    if (!Array.isArray(ids)) return DEFAULT_SOURCES;

    // 저장된 순서대로 정렬, 누락된 항목은 뒤에 추가
    const map = new Map(DEFAULT_SOURCES.map((s) => [s.id, s]));
    const result: SourceItem[] = [];
    for (const id of ids) {
      const item = map.get(id);
      if (item) {
        result.push(item);
        map.delete(id);
      }
    }
    // 저장되지 않은 새 소스 추가
    for (const item of map.values()) {
      result.push(item);
    }
    return result;
  } catch {
    return DEFAULT_SOURCES;
  }
}

/** localStorage에 우선순위 저장 */
function savePriority(sources: SourceItem[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sources.map((s) => s.id)));
  } catch {
    // 저장 실패 무시
  }
}

export const TranscriptSourcePriority = memo(function TranscriptSourcePriority() {
  const [sources, setSources] = useState<SourceItem[]>(DEFAULT_SOURCES);
  const [dragIndex, setDragIndex] = useState<number | null>(null);

  // 마운트 시 저장된 우선순위 로드
  useEffect(() => {
    setSources(loadPriority());
  }, []);

  const handleDragStart = useCallback((index: number) => {
    setDragIndex(index);
  }, []);

  const handleDragOver = useCallback(
    (e: React.DragEvent, targetIndex: number) => {
      e.preventDefault();
      if (dragIndex === null || dragIndex === targetIndex) return;

      setSources((prev) => {
        const next = [...prev];
        const [moved] = next.splice(dragIndex, 1);
        next.splice(targetIndex, 0, moved);
        return next;
      });
      setDragIndex(targetIndex);
    },
    [dragIndex]
  );

  const handleDragEnd = useCallback(() => {
    setDragIndex(null);
    // 정렬 결과 저장
    setSources((current) => {
      savePriority(current);
      return current;
    });
  }, []);

  return (
    <div className="space-y-2">
      <p className="text-xs text-zinc-500 dark:text-zinc-400">
        자막 추출 시 시도할 소스 우선순위를 드래그하여 변경할 수 있습니다.
        (표시용이며, 백엔드는 자체 폴백 순서를 사용합니다.)
      </p>
      <div className="space-y-1">
        {sources.map((source, index) => (
          <div
            key={source.id}
            draggable
            onDragStart={() => handleDragStart(index)}
            onDragOver={(e) => handleDragOver(e, index)}
            onDragEnd={handleDragEnd}
            className={`flex items-center gap-2 px-3 py-2 rounded-md border transition-colors cursor-grab active:cursor-grabbing ${
              dragIndex === index
                ? 'border-blue-400 bg-blue-50 dark:bg-blue-950/30 dark:border-blue-600'
                : 'border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 hover:border-zinc-300 dark:hover:border-zinc-600'
            }`}
          >
            <GripVertical className="size-4 text-zinc-400 shrink-0" />
            <span className="text-xs font-medium text-zinc-400 dark:text-zinc-500 w-4 text-center shrink-0">
              {index + 1}
            </span>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-zinc-700 dark:text-zinc-200">
                {source.label}
              </div>
              <div className="text-xs text-zinc-500 dark:text-zinc-400">
                {source.description}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
});

export default TranscriptSourcePriority;
