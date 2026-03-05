'use client';

import { useState, useEffect, useCallback } from 'react';
import { History, RotateCcw, Eye, GitCompare } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface Version {
  id: string;
  version: number;
  title: string;
  note: string;
  created_at: string;
}

interface VersionHistoryProps {
  contentId: string;
  onRestore?: (content: string, html: string) => void;
}

/** 버전 히스토리 패널 (F5-04) */
export default function VersionHistory({ contentId, onRestore }: VersionHistoryProps) {
  const [versions, setVersions] = useState<Version[]>([]);
  const [selectedVersion, setSelectedVersion] = useState<string | null>(null);
  const [versionContent, setVersionContent] = useState<string>('');
  const [diffResult, setDiffResult] = useState<string>('');
  const [loading, setLoading] = useState(false);

  // 버전 목록 로드
  useEffect(() => {
    async function loadVersions() {
      try {
        const res = await fetch(`/api/content/${contentId}/versions`);
        if (res.ok) {
          const data = await res.json();
          setVersions(data.versions || []);
        }
      } catch {
        // 로드 실패 무시
      }
    }
    loadVersions();
  }, [contentId]);

  // 버전 상세 보기
  const viewVersion = useCallback(async (versionId: string) => {
    setSelectedVersion(versionId);
    setDiffResult('');
    try {
      const res = await fetch(`/api/content/${contentId}/versions/${versionId}`);
      if (res.ok) {
        const data = await res.json();
        setVersionContent(data.content || '');
      }
    } catch {
      // 실패 무시
    }
  }, [contentId]);

  // 버전 비교
  const compareToPrevious = useCallback(async (versionId: string) => {
    const idx = versions.findIndex((v) => v.id === versionId);
    if (idx < 0 || idx >= versions.length - 1) return;
    const prevId = versions[idx + 1].id;

    try {
      const res = await fetch(
        `/api/content/${contentId}/versions/diff?a=${prevId}&b=${versionId}`
      );
      if (res.ok) {
        const data = await res.json();
        setDiffResult(data.diff || '');
        setSelectedVersion(versionId);
      }
    } catch {
      // 실패 무시
    }
  }, [contentId, versions]);

  // 버전 복원
  const restoreVersion = useCallback(async (versionId: string) => {
    setLoading(true);
    try {
      const res = await fetch(
        `/api/content/${contentId}/versions/${versionId}/restore`,
        { method: 'POST' },
      );
      if (res.ok) {
        const data = await res.json();
        onRestore?.(data.content, data.html || '');
        // 목록 새로고침
        const listRes = await fetch(`/api/content/${contentId}/versions`);
        if (listRes.ok) {
          const listData = await listRes.json();
          setVersions(listData.versions || []);
        }
      }
    } catch {
      // 실패 무시
    } finally {
      setLoading(false);
    }
  }, [contentId, onRestore]);

  if (versions.length === 0) {
    return (
      <div className="text-center py-8 text-sm text-muted-foreground/60">
        <History className="h-8 w-8 mx-auto mb-2 opacity-30" />
        <p>버전 기록이 없습니다</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold flex items-center gap-2">
        <History className="h-4 w-4" />
        버전 히스토리
      </h3>

      {/* 버전 목록 */}
      <div className="space-y-1.5 max-h-[300px] overflow-y-auto">
        {versions.map((ver) => (
          <div
            key={ver.id}
            className={`group flex items-center gap-2 px-3 py-2 rounded-lg text-sm cursor-pointer
                        transition-colors ${
                          selectedVersion === ver.id
                            ? 'bg-primary/8 border border-primary/20'
                            : 'hover:bg-accent/50 border border-transparent'
                        }`}
            onClick={() => viewVersion(ver.id)}
          >
            <div className="w-6 h-6 rounded-full bg-muted/60 flex items-center justify-center
                            text-[11px] font-semibold text-muted-foreground shrink-0">
              v{ver.version}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs truncate">
                {ver.note || ver.title || `버전 ${ver.version}`}
              </div>
              <div className="text-[10px] text-muted-foreground/50">
                {new Date(ver.created_at).toLocaleString('ko-KR')}
              </div>
            </div>
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                onClick={(e) => { e.stopPropagation(); compareToPrevious(ver.id); }}
                title="이전 버전과 비교"
              >
                <GitCompare className="h-3 w-3" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                onClick={(e) => { e.stopPropagation(); restoreVersion(ver.id); }}
                disabled={loading}
                title="이 버전으로 복원"
              >
                <RotateCcw className="h-3 w-3" />
              </Button>
            </div>
          </div>
        ))}
      </div>

      {/* 선택된 버전 미리보기 또는 diff */}
      {selectedVersion && (diffResult || versionContent) && (
        <div className="border border-border/40 rounded-lg p-3 bg-muted/10">
          <div className="text-[11px] font-medium text-muted-foreground/60 mb-2">
            {diffResult ? 'Diff 비교' : '버전 미리보기'}
          </div>
          <pre className="text-xs font-mono whitespace-pre-wrap max-h-[200px] overflow-y-auto text-foreground/80">
            {diffResult || versionContent.slice(0, 500)}
            {!diffResult && versionContent.length > 500 && '...'}
          </pre>
        </div>
      )}
    </div>
  );
}
