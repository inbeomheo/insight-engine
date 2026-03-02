'use client';

import { useState, useEffect, useCallback } from 'react';
import { cn } from '@/lib/utils';
import type { ContentStatus, WorkspaceContent } from '@/lib/types';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

// === 상태별 설정 ===

const STATUS_CONFIG: Record<ContentStatus, { label: string; color: string }> = {
  draft: { label: '초안', color: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300' },
  review: { label: '검토중', color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300' },
  approved: { label: '승인됨', color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' },
  published: { label: '발행됨', color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300' },
  rejected: { label: '반려됨', color: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300' },
};

const TAB_FILTERS: Array<{ value: string; label: string }> = [
  { value: 'all', label: '전체' },
  { value: 'draft', label: '초안' },
  { value: 'review', label: '검토중' },
  { value: 'approved', label: '승인됨' },
  { value: 'published', label: '발행됨' },
  { value: 'rejected', label: '반려됨' },
];

// === API 호출 ===

async function fetchContents(workspaceId: string, status?: string): Promise<WorkspaceContent[]> {
  const params = status && status !== 'all' ? `?status=${status}` : '';
  const res = await fetch(`/api/workspace/${workspaceId}/contents${params}`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.contents ?? [];
}

async function postAction(contentId: string, action: string, body?: Record<string, string>): Promise<{ ok: boolean; error?: string }> {
  const res = await fetch(`/api/workspace/contents/${contentId}/${action}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    return { ok: false, error: data.error ?? '요청에 실패했습니다.' };
  }
  return { ok: true };
}

// === 상태 뱃지 ===

function StatusBadge({ status }: { status: ContentStatus }) {
  const config = STATUS_CONFIG[status];
  return (
    <Badge variant="outline" className={cn('border-0', config.color)}>
      {config.label}
    </Badge>
  );
}

// === 날짜 포맷 ===

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

// === 콘텐츠 카드 ===

interface ContentCardProps {
  content: WorkspaceContent;
  userRole?: string;
  onAction: () => void;
}

function ContentCard({ content, userRole, onAction }: ContentCardProps) {
  const [loading, setLoading] = useState(false);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState('');

  const handleAction = async (action: string, body?: Record<string, string>) => {
    setLoading(true);
    const result = await postAction(content.id, action, body);
    setLoading(false);
    if (!result.ok) {
      alert(result.error);
      return;
    }
    onAction();
  };

  const handleReject = async () => {
    if (!rejectReason.trim()) return;
    await handleAction('reject', { reason: rejectReason.trim() });
    setRejectOpen(false);
    setRejectReason('');
  };

  const isOwner = userRole === 'owner';
  const canEdit = userRole === 'owner' || userRole === 'editor';

  return (
    <>
      <div className="flex items-start justify-between gap-4 rounded-lg border p-4 transition-colors hover:bg-muted/50">
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex items-center gap-2">
            <h4 className="truncate text-sm font-medium">{content.title}</h4>
            <StatusBadge status={content.status} />
          </div>
          <p className="text-xs text-muted-foreground">
            {formatDate(content.updated_at)}
          </p>
          {content.review_note && (
            <p className="text-xs text-red-600 dark:text-red-400">
              반려 사유: {content.review_note}
            </p>
          )}
        </div>

        {/* 상태별 액션 버튼 */}
        <div className="flex shrink-0 items-center gap-2">
          {content.status === 'draft' && canEdit && (
            <Button size="sm" variant="outline" disabled={loading} onClick={() => handleAction('submit-review')}>
              리뷰 요청
            </Button>
          )}
          {content.status === 'review' && isOwner && (
            <>
              <Button size="sm" variant="default" disabled={loading} onClick={() => handleAction('approve')}>
                승인
              </Button>
              <Button size="sm" variant="destructive" disabled={loading} onClick={() => setRejectOpen(true)}>
                반려
              </Button>
            </>
          )}
          {content.status === 'approved' && isOwner && (
            <>
              <Button size="sm" variant="default" disabled={loading} onClick={() => handleAction('publish')}>
                발행
              </Button>
              <Button size="sm" variant="outline" disabled={loading} onClick={() => handleAction('revert-draft')}>
                초안으로
              </Button>
            </>
          )}
          {content.status === 'rejected' && canEdit && (
            <Button size="sm" variant="outline" disabled={loading} onClick={() => handleAction('revert-draft')}>
              재편집
            </Button>
          )}
        </div>
      </div>

      {/* 반려 사유 다이얼로그 */}
      <Dialog open={rejectOpen} onOpenChange={setRejectOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>콘텐츠 반려</DialogTitle>
            <DialogDescription>반려 사유를 입력해주세요.</DialogDescription>
          </DialogHeader>
          <Textarea
            placeholder="반려 사유를 작성하세요..."
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            rows={3}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setRejectOpen(false)}>
              취소
            </Button>
            <Button variant="destructive" disabled={!rejectReason.trim() || loading} onClick={handleReject}>
              반려 확인
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

// === 메인 컴포넌트 ===

interface ApprovalFlowProps {
  workspaceId: string;
  userRole?: string;
}

export default function ApprovalFlow({ workspaceId, userRole }: ApprovalFlowProps) {
  const [contents, setContents] = useState<WorkspaceContent[]>([]);
  const [activeTab, setActiveTab] = useState('all');
  const [loading, setLoading] = useState(true);

  const loadContents = useCallback(async () => {
    setLoading(true);
    const status = activeTab === 'all' ? undefined : activeTab;
    const data = await fetchContents(workspaceId, status);
    setContents(data);
    setLoading(false);
  }, [workspaceId, activeTab]);

  useEffect(() => {
    loadContents();
  }, [loadContents]);

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">콘텐츠 승인 관리</h3>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          {TAB_FILTERS.map((tab) => (
            <TabsTrigger key={tab.value} value={tab.value}>
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>

        {TAB_FILTERS.map((tab) => (
          <TabsContent key={tab.value} value={tab.value}>
            {loading ? (
              <p className="py-8 text-center text-sm text-muted-foreground">불러오는 중...</p>
            ) : contents.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">
                {tab.value === 'all' ? '등록된 콘텐츠가 없습니다.' : `${tab.label} 상태의 콘텐츠가 없습니다.`}
              </p>
            ) : (
              <div className="space-y-2">
                {contents.map((item) => (
                  <ContentCard
                    key={item.id}
                    content={item}
                    userRole={userRole}
                    onAction={loadContents}
                  />
                ))}
              </div>
            )}
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}
