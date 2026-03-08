'use client';

import { useState, useCallback } from 'react';
import { Tags, X, Plus, Loader2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface AutoTagsProps {
  /** 콘텐츠 텍스트 (태그 자동 생성용) */
  content: string;
}

interface TagResult {
  tags: string[];
  category: string;
}

export default function AutoTags({ content }: AutoTagsProps) {
  const [result, setResult] = useState<TagResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState(false);
  const [newTag, setNewTag] = useState('');

  const generateTags = useCallback(async () => {
    if (loading || !content) return;
    setLoading(true);
    try {
      const res = await fetch('/api/auto-tags', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      });
      if (!res.ok) throw new Error('태그 생성 실패');
      const data: TagResult = await res.json();
      setResult(data);
    } catch {
      // 실패 시 무시
    } finally {
      setLoading(false);
    }
  }, [content, loading]);

  const removeTag = useCallback((tag: string) => {
    if (!result) return;
    setResult({
      ...result,
      tags: result.tags.filter((t) => t !== tag),
    });
  }, [result]);

  const addTag = useCallback(() => {
    if (!result || !newTag.trim()) return;
    if (result.tags.includes(newTag.trim())) {
      setNewTag('');
      return;
    }
    setResult({
      ...result,
      tags: [...result.tags, newTag.trim()],
    });
    setNewTag('');
  }, [result, newTag]);

  // 아직 생성 안 했으면 버튼 표시
  if (!result) {
    return (
      <Button
        variant="ghost"
        size="sm"
        className="h-7 text-xs gap-1"
        onClick={generateTags}
        disabled={loading}
      >
        {loading ? (
          <Loader2 className="h-3 w-3 animate-spin" />
        ) : (
          <Tags className="h-3 w-3" />
        )}
        태그 생성
      </Button>
    );
  }

  return (
    <div className="space-y-2">
      {/* 카테고리 배지 */}
      <div className="flex items-center gap-2 flex-wrap">
        <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
          {result.category}
        </Badge>

        {/* 태그 목록 */}
        {result.tags.map((tag) => (
          <Badge
            key={tag}
            variant="outline"
            className="text-[10px] px-1.5 py-0 gap-0.5"
          >
            #{tag}
            {editing && (
              <button
                onClick={() => removeTag(tag)}
                aria-label={`${tag} 태그 제거`}
                className="ml-0.5 hover:text-destructive"
              >
                <X className="h-2.5 w-2.5" />
              </button>
            )}
          </Badge>
        ))}

        {/* 편집 토글 */}
        <Button
          variant="ghost"
          size="sm"
          className="h-5 w-5 p-0"
          onClick={() => setEditing(!editing)}
        >
          {editing ? <X className="h-3 w-3" /> : <Plus className="h-3 w-3" />}
        </Button>
      </div>

      {/* 태그 추가 입력 */}
      {editing && (
        <div className="flex gap-1">
          <Input
            value={newTag}
            onChange={(e) => setNewTag(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && addTag()}
            placeholder="새 태그"
            className="h-6 text-xs"
          />
          <Button size="sm" className="h-6 text-xs px-2" onClick={addTag}>
            추가
          </Button>
        </div>
      )}
    </div>
  );
}
