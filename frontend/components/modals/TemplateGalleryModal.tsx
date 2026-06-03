'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  BookTemplate,
  Search,
  Plus,
  Trash2,
  Globe,
  Lock,
  Check,
  ChevronLeft,
  ChevronRight,
  Edit2,
} from 'lucide-react';
import { useUIStore } from '@/stores/uiStore';
import { toast } from 'sonner';
import {
  getTemplates,
  createTemplate,
  updateTemplate,
  deleteTemplate,
  useTemplate,
  type PromptTemplate,
} from '@/lib/api';

// 스타일 라벨 매핑
const STYLE_LABELS: Record<string, string> = {
  blog_seo: 'SEO 블로그',
  summary: '요약',
  tutorial: '튜토리얼',
  qna: 'Q&A',
  app_ideas: '앱 아이디어',
  yozm_it: 'Yozm IT',
  brunch_essay: '브런치 에세이',
  naver_popular: '네이버 인기',
  sns_post: 'SNS 포스트',
  newsletter: '뉴스레터',
  show_notes: '쇼노트',
  shorts_script: 'Shorts 스크립트',
  geo_seo: 'GEO SEO',
};

type ViewMode = 'list' | 'create' | 'edit';

interface FormState {
  name: string;
  description: string;
  prompt_text: string;
  style_base: string;
  is_public: boolean;
}

const EMPTY_FORM: FormState = {
  name: '',
  description: '',
  prompt_text: '',
  style_base: 'blog_seo',
  is_public: false,
};

interface TemplateGalleryModalProps {
  /** 프롬프트 적용 콜백 (선택) */
  onApply?: (promptText: string) => void;
}

export default function TemplateGalleryModal({ onApply }: TemplateGalleryModalProps) {
  const { activeModal, setTemplateGalleryOpen } = useUIStore();
  const isOpen = activeModal === 'templateGallery';

  const [view, setView] = useState<ViewMode>('list');
  const [templates, setTemplates] = useState<PromptTemplate[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<PromptTemplate | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);

  // 목록 불러오기
  const loadTemplates = useCallback(
    async (p: number = 1, q: string = search) => {
      setLoading(true);
      try {
        const res = await getTemplates(p, q);
        setTemplates(res.templates);
        setTotal(res.total);
        setPage(p);
        setHasMore(res.has_more);
      } catch {
        toast.error('템플릿 목록을 불러오지 못했습니다.');
      } finally {
        setLoading(false);
      }
    },
    [search]
  );

  useEffect(() => {
    if (isOpen) {
      setView('list');
      setSearch('');
      loadTemplates(1, '');
    }
  }, [isOpen]); // eslint-disable-line react-hooks/exhaustive-deps

  // 검색 디바운스 (300ms)
  useEffect(() => {
    const timer = setTimeout(() => {
      if (isOpen && view === 'list') {
        loadTemplates(1, search);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [search]); // eslint-disable-line react-hooks/exhaustive-deps

  function openCreate() {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setView('create');
  }

  function openEdit(t: PromptTemplate) {
    setEditingId(t.id);
    setForm({
      name: t.name,
      description: t.description,
      prompt_text: t.prompt_text,
      style_base: t.style_base,
      is_public: t.is_public,
    });
    setView('edit');
  }

  async function handleSave() {
    if (!form.name.trim()) return toast.error('템플릿 이름을 입력하세요.');
    if (!form.prompt_text.trim()) return toast.error('프롬프트를 입력하세요.');

    setSaving(true);
    try {
      if (view === 'edit' && editingId) {
        await updateTemplate(editingId, form);
        toast.success('템플릿이 수정되었습니다.');
      } else {
        await createTemplate(form);
        toast.success('템플릿이 저장되었습니다.');
      }
      setView('list');
      loadTemplates(1, search);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : '저장에 실패했습니다.');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    try {
      await deleteTemplate(deleteTarget.id);
      toast.success('삭제되었습니다.');
      setDeleteTarget(null);
      loadTemplates(page, search);
    } catch {
      toast.error('삭제에 실패했습니다.');
    }
  }

  async function handleApply(t: PromptTemplate) {
    try {
      // eslint-disable-next-line react-hooks/rules-of-hooks
      const result = await useTemplate(t.id);
      if (onApply) {
        onApply(result.prompt_text);
        toast.success(`"${t.name}" 프롬프트가 적용되었습니다.`);
        setTemplateGalleryOpen(false);
      } else {
        await navigator.clipboard.writeText(result.prompt_text);
        toast.success('프롬프트가 클립보드에 복사되었습니다.');
      }
    } catch {
      toast.error('템플릿 적용에 실패했습니다.');
    }
  }

  const perPage = 20;
  const totalPages = Math.ceil(total / perPage);

  return (
    <>
    <Dialog open={isOpen} onOpenChange={(v) => {
      setTemplateGalleryOpen(v);
      if (!v) setDeleteTarget(null);
    }}>
      <DialogContent className="max-w-2xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <BookTemplate className="h-5 w-5 text-primary" />
            {view === 'list' ? '프롬프트 템플릿 갤러리' : view === 'create' ? '새 템플릿 만들기' : '템플릿 수정'}
          </DialogTitle>
          <DialogDescription>
            {view === 'list'
              ? '저장된 프롬프트 템플릿을 재사용하거나 새로 만드세요'
              : '이름, 프롬프트, 공개 여부를 설정합니다'}
          </DialogDescription>
        </DialogHeader>

        {/* 목록 뷰 */}
        {view === 'list' && (
          <>
            {/* 검색 + 추가 버튼 */}
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="템플릿 검색..."
                  className="pl-8"
                />
              </div>
              <Button size="sm" onClick={openCreate}>
                <Plus className="h-4 w-4 mr-1" />
                새 템플릿
              </Button>
            </div>

            {/* 목록 */}
            <ScrollArea className="flex-1 min-h-0 max-h-[55vh]">
              {loading ? (
                <div className="flex items-center justify-center h-32 text-muted-foreground text-sm">
                  불러오는 중...
                </div>
              ) : templates.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-32 gap-2 text-muted-foreground text-sm">
                  <BookTemplate className="h-8 w-8 opacity-30" />
                  <span>{search ? '검색 결과가 없습니다.' : '저장된 템플릿이 없습니다.'}</span>
                </div>
              ) : (
                <div className="space-y-2 pr-2">
                  {templates.map((t) => (
                    <div
                      key={t.id}
                      className="border rounded-lg p-3 hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1.5 mb-0.5">
                            <span className="font-medium text-sm truncate">{t.name}</span>
                            {t.is_public ? (
                              <Globe className="h-3 w-3 text-blue-500 shrink-0" aria-label="공개" />
                            ) : (
                              <Lock className="h-3 w-3 text-muted-foreground shrink-0" aria-label="비공개" />
                            )}
                          </div>
                          {t.description && (
                            <p className="text-xs text-muted-foreground truncate">{t.description}</p>
                          )}
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                              {STYLE_LABELS[t.style_base] || t.style_base}
                            </span>
                            <span className="text-xs text-muted-foreground">
                              사용 {t.usage_count}회
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center gap-1 shrink-0">
                          {t.is_owner && (
                            <>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7"
                                onClick={() => openEdit(t)}
                                title="수정"
                              >
                                <Edit2 className="h-3.5 w-3.5" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7 text-destructive hover:text-destructive"
                                onClick={() => setDeleteTarget(t)}
                                title="삭제"
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </Button>
                            </>
                          )}
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-7 text-xs"
                            onClick={() => handleApply(t)}
                          >
                            <Check className="h-3 w-3 mr-1" />
                            적용
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </ScrollArea>

            {/* 페이지네이션 */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between pt-2 border-t text-sm text-muted-foreground">
                <span>
                  {total}개 중 {(page - 1) * perPage + 1}-{Math.min(page * perPage, total)}개
                </span>
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    disabled={page <= 1}
                    onClick={() => loadTemplates(page - 1)}
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <span className="text-xs px-1">
                    {page} / {totalPages}
                  </span>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    disabled={!hasMore}
                    onClick={() => loadTemplates(page + 1)}
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </>
        )}

        {/* 생성/수정 폼 뷰 */}
        {(view === 'create' || view === 'edit') && (
          <div className="space-y-4 flex-1 overflow-y-auto">
            {/* 이름 */}
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">
                템플릿 이름 <span className="text-destructive">*</span>
              </label>
              <Input
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                maxLength={50}
                placeholder="예: 마케팅 분석 전문가"
              />
              <div className="text-right text-xs text-muted-foreground mt-0.5">
                {form.name.length}/50
              </div>
            </div>

            {/* 설명 */}
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">
                설명 (선택)
              </label>
              <Input
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                maxLength={200}
                placeholder="이 템플릿에 대한 간단한 설명"
              />
            </div>

            {/* 기반 스타일 */}
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">
                기반 스타일
              </label>
              <select
                value={form.style_base}
                onChange={(e) => setForm((f) => ({ ...f, style_base: e.target.value }))}
                className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm"
              >
                {Object.entries(STYLE_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>

            {/* 프롬프트 */}
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">
                프롬프트 <span className="text-destructive">*</span>
              </label>
              <Textarea
                value={form.prompt_text}
                onChange={(e) => setForm((f) => ({ ...f, prompt_text: e.target.value }))}
                maxLength={5000}
                rows={8}
                placeholder={`AI에게 전달할 지시사항을 작성하세요.\n\n예:\n당신은 마케팅 전문가입니다.\n아래 영상 내용을 분석하여 핵심 마케팅 인사이트를 도출해주세요.`}
                className="font-mono text-sm"
              />
              <div className="text-right text-xs text-muted-foreground mt-0.5">
                {form.prompt_text.length}/5000
              </div>
            </div>

            {/* 공개 여부 */}
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={form.is_public}
                onChange={(e) => setForm((f) => ({ ...f, is_public: e.target.checked }))}
                className="accent-primary h-4 w-4"
              />
              <span className="text-sm">
                <Globe className="h-3.5 w-3.5 inline mr-1 text-blue-500" />
                다른 사용자에게 공개
              </span>
            </label>

            {/* 하단 버튼 */}
            <div className="flex justify-between pt-2 border-t">
              <Button variant="ghost" onClick={() => setView('list')}>
                <ChevronLeft className="h-4 w-4 mr-1" />
                목록으로
              </Button>
              <Button onClick={handleSave} disabled={saving}>
                {saving ? '저장 중...' : view === 'edit' ? '수정 완료' : '저장'}
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
    <Dialog open={Boolean(deleteTarget)} onOpenChange={(open) => !open && setDeleteTarget(null)}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-destructive">
            <Trash2 className="h-5 w-5" />
            템플릿 삭제
          </DialogTitle>
          <DialogDescription>
            “{deleteTarget?.name}” 템플릿을 삭제합니다. 이 작업은 되돌릴 수 없습니다.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => setDeleteTarget(null)}>
            취소
          </Button>
          <Button type="button" variant="destructive" onClick={handleDelete}>
            삭제하기
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
    </>
  );
}
