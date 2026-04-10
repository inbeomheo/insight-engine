'use client';

import { useState } from 'react';
import { Search, Plus, Loader2, Youtube, Globe } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { recommendSources, type RecommendedSource } from '@/lib/api';

const SOURCE_ICONS: Record<string, typeof Globe> = {
  youtube: Youtube,
  webpage: Globe,
};

interface SourceRecommenderProps {
  onAddUrl: (url: string) => string | null;
}

export default function SourceRecommender({ onAddUrl }: SourceRecommenderProps) {
  const [topic, setTopic] = useState('');
  const [results, setResults] = useState<RecommendedSource[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [addedUrls, setAddedUrls] = useState<Set<string>>(new Set());

  async function handleSearch() {
    if (!topic.trim()) return;

    setLoading(true);
    setError('');
    setResults([]);

    try {
      const data = await recommendSources(topic.trim());
      setResults(data.sources || []);
      if (!data.sources?.length) {
        setError('관련 소스를 찾을 수 없습니다.');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : '소스 추천에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  }

  function handleAdd(url: string) {
    const err = onAddUrl(url);
    if (!err) {
      setAddedUrls(prev => new Set(prev).add(url));
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <Input
          value={topic}
          onChange={e => setTopic(e.target.value)}
          placeholder="주제를 입력하세요 (예: 파이썬 웹 개발)"
          onKeyDown={e => e.key === 'Enter' && handleSearch()}
          disabled={loading}
        />
        <Button
          variant="outline"
          size="sm"
          onClick={handleSearch}
          disabled={loading || !topic.trim()}
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Search className="h-4 w-4" />
          )}
          <span className="ml-1.5">찾기</span>
        </Button>
      </div>

      {error && (
        <p className="text-sm text-destructive">{error}</p>
      )}

      {results.length > 0 && (
        <ul className="space-y-1.5 max-h-60 overflow-y-auto">
          {results.map((source, i) => {
            const Icon = SOURCE_ICONS[source.source_type] || Globe;
            const isAdded = addedUrls.has(source.url);

            return (
              <li
                key={`${source.url}-${i}`}
                className="flex items-center gap-2 p-2 rounded-md border bg-card text-sm"
              >
                <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />
                <div className="flex-1 min-w-0">
                  <p className="truncate font-medium">{source.title}</p>
                  <p className="truncate text-xs text-muted-foreground">{source.url}</p>
                </div>
                <span className="text-xs text-muted-foreground shrink-0">
                  {Math.round(source.relevance_score * 100)}%
                </span>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 shrink-0"
                  onClick={() => handleAdd(source.url)}
                  disabled={isAdded}
                  title={isAdded ? '추가됨' : 'URL 추가'}
                >
                  {isAdded ? (
                    <span className="text-xs text-green-500">V</span>
                  ) : (
                    <Plus className="h-3.5 w-3.5" />
                  )}
                </Button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
