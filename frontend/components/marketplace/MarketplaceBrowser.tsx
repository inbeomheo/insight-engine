'use client';

import { useState, useEffect } from 'react';
import { Search, Download, Star } from 'lucide-react';
import { toast } from 'sonner';
import { apiUrl } from '@/lib/api';

interface Template {
  id: string;
  title: string;
  description: string;
  category: string;
  downloads: number;
  rating: number;
  rating_count: number;
  price: number;
  tags: string[];
}

/** 프롬프트 템플릿 마켓플레이스 브라우저 (F4-14) */
export default function MarketplaceBrowser() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchTemplates = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (query) params.set('q', query);
      if (category) params.set('category', category);

      const res = await fetch(apiUrl(`/api/marketplace?${params}`));
      const data = await res.json();
      setTemplates(data.templates || []);
    } catch {
      // 네트워크 오류 무시
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTemplates();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [category]);

  const handleDownload = async (templateId: string) => {
    try {
      const res = await fetch(apiUrl(`/api/marketplace/${templateId}/download`), { method: 'POST' });
      const data = await res.json();
      if (data.prompt_text) {
        await navigator.clipboard.writeText(data.prompt_text);
        toast.success('프롬프트가 클립보드에 복사되었습니다.');
      }
    } catch {
      toast.error('다운로드에 실패했습니다.');
    }
  };

  const categories = ['general', 'blog', 'marketing', 'education', 'tech'];

  return (
    <div className="space-y-4">
      {/* 검색 + 카테고리 필터 */}
      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && fetchTemplates()}
            placeholder="템플릿 검색..."
            className="w-full rounded-lg border border-white/10 bg-white/5 py-2 pl-10 pr-3 text-sm placeholder:text-gray-500 focus:border-indigo-500 focus:outline-none"
          />
        </div>
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm"
        >
          <option value="">전체 카테고리</option>
          {categories.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      {/* 템플릿 카드 그리드 */}
      {loading ? (
        <p className="text-center text-sm text-gray-400">로딩 중...</p>
      ) : templates.length === 0 ? (
        <p className="text-center text-sm text-gray-400">템플릿이 없습니다.</p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {templates.map((t) => (
            <div key={t.id} className="rounded-xl border border-white/10 bg-white/5 p-4 space-y-2">
              <h3 className="font-semibold text-sm">{t.title}</h3>
              <p className="text-xs text-gray-400 line-clamp-2">{t.description}</p>
              <div className="flex items-center gap-3 text-xs text-gray-500">
                <span className="flex items-center gap-1">
                  <Download className="h-3 w-3" /> {t.downloads}
                </span>
                <span className="flex items-center gap-1">
                  <Star className="h-3 w-3" /> {t.rating.toFixed(1)} ({t.rating_count})
                </span>
                {t.price > 0 && <span>{t.price.toLocaleString()}원</span>}
              </div>
              <div className="flex flex-wrap gap-1">
                {t.tags.slice(0, 3).map((tag) => (
                  <span key={tag} className="rounded-full bg-indigo-500/20 px-2 py-0.5 text-xs text-indigo-300">
                    {tag}
                  </span>
                ))}
              </div>
              <button
                onClick={() => handleDownload(t.id)}
                aria-label={`${t.title} 템플릿 다운로드`}
                className="w-full rounded-lg bg-indigo-600 py-1.5 text-xs font-medium text-white hover:bg-indigo-500"
              >
                {t.price > 0 ? '구매' : '무료 다운로드'}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
