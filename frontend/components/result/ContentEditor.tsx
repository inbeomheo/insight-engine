'use client';

// 생성된 문서 인라인 편집기 — 제목/본문(마크다운)을 직접 수정한다.
// 저장 로직은 ResultCard가 주입(onSave)하고, 이 컴포넌트는 입력 상태만 관리한다.
import { useCallback, useId, useState } from 'react';
import { Check, Loader2, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { useTranslation } from '@/hooks/useTranslation';
import type { ReportDraft } from '@/lib/report-edit';

interface ContentEditorProps {
  initialTitle: string;
  initialContent: string;
  onSave: (draft: ReportDraft) => void | Promise<void>;
  onCancel: () => void;
}

export default function ContentEditor({
  initialTitle,
  initialContent,
  onSave,
  onCancel,
}: ContentEditorProps) {
  const { t } = useTranslation();
  const fieldId = useId();
  const [title, setTitle] = useState(initialTitle);
  const [content, setContent] = useState(initialContent);
  const [saving, setSaving] = useState(false);

  const handleSave = useCallback(async () => {
    if (saving) return;
    setSaving(true);
    try {
      await onSave({ title, content });
    } finally {
      setSaving(false);
    }
  }, [saving, title, content, onSave]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onCancel();
        return;
      }
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault();
        void handleSave();
      }
    },
    [handleSave, onCancel],
  );

  return (
    <div className="not-prose flex flex-col gap-3" onKeyDown={handleKeyDown}>
      <div className="flex flex-col gap-1.5">
        <label htmlFor={`${fieldId}-title`} className="text-xs font-medium text-muted-foreground">
          {t('result.editTitleLabel')}
        </label>
        <Input
          id={`${fieldId}-title`}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="rounded-sm text-base font-semibold"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor={`${fieldId}-content`} className="text-xs font-medium text-muted-foreground">
          {t('result.editContentLabel')}
        </label>
        <Textarea
          id={`${fieldId}-content`}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          className="min-h-[360px] rounded-sm font-mono text-[13.5px] leading-[1.7]"
          spellCheck={false}
        />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-[11px] text-muted-foreground">
          {t('result.editHint')} · {content.length.toLocaleString()}자
        </span>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" className="h-8 rounded-sm" onClick={onCancel} disabled={saving}>
            <X className="mr-1 h-3.5 w-3.5" />
            {t('result.editCancel')}
          </Button>
          <Button size="sm" className="h-8 rounded-sm" onClick={handleSave} disabled={saving}>
            {saving ? (
              <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
            ) : (
              <Check className="mr-1 h-3.5 w-3.5" />
            )}
            {t('result.editSave')}
          </Button>
        </div>
      </div>
    </div>
  );
}
