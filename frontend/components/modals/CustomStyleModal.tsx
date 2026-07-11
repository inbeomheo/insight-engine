'use client';

import { useState, useEffect } from 'react';
import { FileEdit, Star, Bookmark, Brain, Rocket } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Pencil, Trash2, BookTemplate } from 'lucide-react';
import { useUIStore } from '@/stores/uiStore';
import { useSettingsStore } from '@/stores/settingsStore';
import { toast } from 'sonner';
import { createTemplate } from '@/lib/api';
import { STYLE_OPTIONS } from '@/lib/constants';

const ICON_OPTIONS = ['edit_note', 'star', 'bookmark', 'psychology', 'rocket_launch'];
const DEFAULT_STYLE_BASE = STYLE_OPTIONS[0]?.id ?? 'summary';
const ICON_LABELS: Record<string, string> = {
  edit_note: '편집',
  star: '별',
  bookmark: '북마크',
  psychology: '분석',
  rocket_launch: '로켓',
};

export default function CustomStyleModal() {
  const { activeModal, editingCustomStyleId, setCustomStyleModalOpen } = useUIStore();
  const customStyleModalOpen = activeModal === 'customStyle';
  const { customStyles, addCustomStyle, updateCustomStyle, deleteCustomStyle } =
    useSettingsStore();

  const [name, setName] = useState('');
  const [icon, setIcon] = useState('edit_note');
  const [prompt, setPrompt] = useState('');

  const editing = editingCustomStyleId
    ? customStyles.find((s) => s.id === editingCustomStyleId)
    : null;

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (editing) {
      setName(editing.name);
      setIcon(editing.icon || 'edit_note');
      setPrompt(editing.prompt);
    } else {
      setName('');
      setIcon('edit_note');
      setPrompt('');
    }
  }, [editing, customStyleModalOpen]);
  /* eslint-enable react-hooks/set-state-in-effect */

  function handleSave() {
    if (!name.trim()) return toast.error('스타일 이름을 입력하세요.');
    if (!prompt.trim()) return toast.error('프롬프트를 입력하세요.');

    if (editing) {
      updateCustomStyle(editing.id, { name: name.trim(), icon, prompt: prompt.trim() });
      toast.success('스타일이 수정되었습니다.');
    } else {
      addCustomStyle({
        id: `custom_${Date.now()}`,
        name: name.trim(),
        icon,
        prompt: prompt.trim(),
        createdAt: Date.now(),
      });
      toast.success('스타일이 추가되었습니다.');
    }
    setCustomStyleModalOpen(false);
  }

  function handleDelete() {
    if (!editing) return;
    deleteCustomStyle(editing.id);
    toast.success('스타일이 삭제되었습니다.');
    setCustomStyleModalOpen(false);
  }

  async function handleSaveAsTemplate() {
    if (!name.trim()) return toast.error('스타일 이름을 입력하세요.');
    if (!prompt.trim()) return toast.error('프롬프트를 입력하세요.');

    try {
      await createTemplate({
        name: name.trim(),
        prompt_text: prompt.trim(),
        description: `커스텀 스타일에서 저장된 템플릿`,
        style_base: DEFAULT_STYLE_BASE,
        is_public: false,
      });
      toast.success('템플릿 갤러리에 저장되었습니다.');
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : '템플릿 저장에 실패했습니다.');
    }
  }

  return (
    <Dialog open={customStyleModalOpen} onOpenChange={(v) => setCustomStyleModalOpen(v)}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Pencil className="h-5 w-5 text-primary" />
            {editing ? '스타일 수정' : '새 스타일 만들기'}
          </DialogTitle>
          <DialogDescription>커스텀 스타일의 이름, 아이콘, 프롬프트를 설정합니다</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">
              스타일 이름
            </label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={20}
              placeholder="예: 내 분석 스타일"
            />
          </div>

          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">
              아이콘 선택
            </label>
            <div className="flex gap-2">
              {ICON_OPTIONS.map((ic) => (
                <button
                  key={ic}
                  onClick={() => setIcon(ic)}
                  aria-label={`${ic} 아이콘 선택`}
                  className={`flex-1 p-2 text-center rounded-lg border transition-all text-lg ${
                    icon === ic
                      ? 'border-primary bg-primary/10'
                      : 'border-border hover:border-primary/50'
                  }`}
                >
                  {(() => {
                    const icons: Record<string, React.ElementType> = { edit_note: FileEdit, star: Star, bookmark: Bookmark, psychology: Brain, rocket_launch: Rocket };
                    const I = icons[ic]; return I ? <I className="h-5 w-5 mx-auto" /> : <span>{ICON_LABELS[ic]}</span>;
                  })()}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">
              프롬프트
            </label>
            <Textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              maxLength={2000}
              rows={8}
              placeholder={`AI에게 전달할 지시사항을 작성하세요.\n\n예:\n당신은 마케팅 전문가입니다.\n아래 영상의 내용을 분석하여 마케팅 인사이트를 도출해주세요.`}
              className="font-mono text-sm"
            />
            <div className="text-right text-xs text-muted-foreground mt-1">
              {prompt.length}/2000자
            </div>
          </div>
        </div>

        <div className="flex justify-between pt-2 border-t">
          {editing ? (
            <Button variant="ghost" className="text-destructive" onClick={handleDelete}>
              <Trash2 className="h-4 w-4 mr-1" />
              삭제
            </Button>
          ) : (
            <div />
          )}
          <div className="flex gap-2">
            <Button variant="ghost" onClick={() => setCustomStyleModalOpen(false)}>
              취소
            </Button>
            <Button variant="outline" onClick={handleSaveAsTemplate} title="템플릿 갤러리에 저장">
              <BookTemplate className="h-4 w-4 mr-1" />
              템플릿으로 저장
            </Button>
            <Button onClick={handleSave}>저장</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
