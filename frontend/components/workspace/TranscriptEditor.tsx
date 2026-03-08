'use client';

import { memo, useState, useMemo, useCallback, useEffect } from 'react';
import { Search, Pencil, Trash2, Undo2, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Textarea } from '@/components/ui/textarea';

/** 서버에서 반환하는 문장 구조 */
interface TranscriptSentence {
  index: number;
  text: string;
  start_time: number | null;
}

interface TranscriptEditorProps {
  videoId: string;
  onRegenerate?: (editedTranscript: string) => void;
}

/** 초를 mm:ss 또는 h:mm:ss 형식으로 변환 */
function formatTimestamp(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return h > 0
    ? `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
    : `${m}:${String(s).padStart(2, '0')}`;
}

/** 검색어 하이라이트 처리 */
function highlightText(text: string, query: string) {
  if (!query.trim()) return text;
  const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const parts = text.split(new RegExp(`(${escaped})`, 'gi'));
  return parts.map((part, i) =>
    part.toLowerCase() === query.toLowerCase() ? (
      <mark key={i} className="bg-yellow-300 dark:bg-yellow-600 rounded px-0.5">
        {part}
      </mark>
    ) : (
      part
    )
  );
}

export const TranscriptEditor = memo(function TranscriptEditor({
  videoId,
  onRegenerate,
}: TranscriptEditorProps) {
  const [sentences, setSentences] = useState<TranscriptSentence[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  // 편집 상태
  const [deletedIndices, setDeletedIndices] = useState<Set<number>>(new Set());
  const [modifiedMap, setModifiedMap] = useState<Record<number, string>>({});
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editText, setEditText] = useState('');

  // 자막 로드
  const fetchTranscript = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/transcript/${videoId}`);
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setSentences(data.sentences || []);
      // 편집 상태 초기화
      setDeletedIndices(new Set());
      setModifiedMap({});
      setEditingIndex(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : '자막을 불러올 수 없습니다.');
    } finally {
      setLoading(false);
    }
  }, [videoId]);

  useEffect(() => {
    if (videoId) fetchTranscript();
  }, [videoId, fetchTranscript]);

  // 검색 필터링
  const filtered = useMemo(() => {
    if (!search.trim()) return sentences;
    const q = search.toLowerCase();
    return sentences.filter((s) => {
      const displayText = modifiedMap[s.index] ?? s.text;
      return displayText.toLowerCase().includes(q);
    });
  }, [sentences, search, modifiedMap]);

  // 타임스탬프 클릭 → YouTube 이동
  const handleTimestampClick = useCallback(
    (seconds: number) => {
      window.open(
        `https://www.youtube.com/watch?v=${videoId}&t=${Math.floor(seconds)}s`,
        '_blank'
      );
    },
    [videoId]
  );

  // 문장 삭제 토글
  const toggleDelete = useCallback((index: number) => {
    setDeletedIndices((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  }, []);

  // 인라인 편집 시작
  const startEdit = useCallback(
    (sentence: TranscriptSentence) => {
      setEditingIndex(sentence.index);
      setEditText(modifiedMap[sentence.index] ?? sentence.text);
    },
    [modifiedMap]
  );

  // 인라인 편집 확정
  const confirmEdit = useCallback(() => {
    if (editingIndex === null) return;
    const original = sentences.find((s) => s.index === editingIndex);
    if (original && editText.trim() !== original.text) {
      setModifiedMap((prev) => ({ ...prev, [editingIndex]: editText.trim() }));
    } else {
      // 원본과 동일하면 수정 기록 제거
      setModifiedMap((prev) => {
        const next = { ...prev };
        delete next[editingIndex!];
        return next;
      });
    }
    setEditingIndex(null);
    setEditText('');
  }, [editingIndex, editText, sentences]);

  // 편집 취소
  const cancelEdit = useCallback(() => {
    setEditingIndex(null);
    setEditText('');
  }, []);

  // 편집된 자막으로 재생성
  const handleRegenerate = useCallback(() => {
    if (!onRegenerate) return;

    const parts: string[] = [];
    for (const s of sentences) {
      if (deletedIndices.has(s.index)) continue;
      const text = modifiedMap[s.index] ?? s.text;
      if (text.trim()) parts.push(text.trim());
    }
    onRegenerate(parts.join(' '));
  }, [sentences, deletedIndices, modifiedMap, onRegenerate]);

  const hasEdits = deletedIndices.size > 0 || Object.keys(modifiedMap).length > 0;

  // 로딩/에러/빈 상태
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12 text-sm text-zinc-500">
        자막을 불러오는 중...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center gap-2 py-8">
        <p className="text-sm text-red-500">{error}</p>
        <Button variant="outline" size="sm" onClick={fetchTranscript}>
          다시 시도
        </Button>
      </div>
    );
  }

  if (!sentences.length) {
    return (
      <div className="flex items-center justify-center py-12 text-sm text-zinc-500">
        자막 데이터가 없습니다.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* 검색 */}
      <div className="relative">
        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-zinc-400" />
        <Input
          placeholder="자막 검색..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9 h-9 text-sm"
        />
      </div>

      {/* 문장 목록 */}
      <ScrollArea className="h-[400px]">
        <div className="space-y-1">
          {filtered.map((sentence) => {
            const isDeleted = deletedIndices.has(sentence.index);
            const isEditing = editingIndex === sentence.index;
            const displayText = modifiedMap[sentence.index] ?? sentence.text;
            const isModified = sentence.index in modifiedMap;

            return (
              <div
                key={sentence.index}
                className={`flex gap-2 py-1.5 px-2 rounded group transition-colors ${
                  isDeleted
                    ? 'opacity-40 line-through bg-red-50 dark:bg-red-950/20'
                    : 'hover:bg-zinc-100 dark:hover:bg-zinc-800'
                } ${isModified && !isDeleted ? 'bg-blue-50 dark:bg-blue-950/20' : ''}`}
              >
                {/* 타임스탬프 */}
                {sentence.start_time !== null && (
                  <button
                    onClick={() => handleTimestampClick(sentence.start_time!)}
                    aria-label={`${formatTimestamp(sentence.start_time)} 타임스탬프로 이동`}
                    className="text-xs font-mono text-blue-500 hover:text-blue-700 dark:text-blue-400 shrink-0 pt-0.5 min-w-[3.5rem] text-right"
                  >
                    {formatTimestamp(sentence.start_time)}
                  </button>
                )}

                {/* 텍스트 또는 편집 영역 */}
                <div className="flex-1 min-w-0">
                  {isEditing ? (
                    <div className="space-y-1.5">
                      <Textarea
                        value={editText}
                        onChange={(e) => setEditText(e.target.value)}
                        className="text-sm min-h-[2.5rem]"
                        autoFocus
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            confirmEdit();
                          }
                          if (e.key === 'Escape') cancelEdit();
                        }}
                      />
                      <div className="flex gap-1">
                        <Button size="xs" onClick={confirmEdit}>
                          확인
                        </Button>
                        <Button size="xs" variant="ghost" onClick={cancelEdit}>
                          취소
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <span className="text-sm text-zinc-700 dark:text-zinc-300">
                      {highlightText(displayText, search)}
                    </span>
                  )}
                </div>

                {/* 액션 버튼 */}
                {!isEditing && (
                  <div className="flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                    <Button
                      variant="ghost"
                      size="icon-xs"
                      onClick={() => startEdit(sentence)}
                      title="문장 수정"
                    >
                      <Pencil className="size-3" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-xs"
                      onClick={() => toggleDelete(sentence.index)}
                      title={isDeleted ? '문장 복원' : '문장 삭제'}
                    >
                      {isDeleted ? (
                        <Undo2 className="size-3" />
                      ) : (
                        <Trash2 className="size-3" />
                      )}
                    </Button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </ScrollArea>

      {/* 편집된 자막으로 재생성 버튼 */}
      {onRegenerate && (
        <div className="flex items-center justify-between pt-2 border-t border-zinc-200 dark:border-zinc-700">
          <span className="text-xs text-zinc-500">
            {hasEdits
              ? `${deletedIndices.size}개 삭제, ${Object.keys(modifiedMap).length}개 수정됨`
              : '편집 없음'}
          </span>
          <Button
            size="sm"
            disabled={!hasEdits}
            onClick={handleRegenerate}
          >
            <RefreshCw className="size-3.5 mr-1" />
            편집된 자막으로 재생성
          </Button>
        </div>
      )}
    </div>
  );
});

export default TranscriptEditor;
