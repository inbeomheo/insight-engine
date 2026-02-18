'use client';

import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Pencil, Trash2 } from 'lucide-react';
import { useUIStore } from '@/stores/uiStore';
import { useSettingsStore } from '@/stores/settingsStore';
import { toast } from 'sonner';

const ICON_OPTIONS = ['edit_note', 'star', 'bookmark', 'psychology', 'rocket_launch'];
const ICON_EMOJIS: Record<string, string> = {
  edit_note: '📝',
  star: '⭐',
  bookmark: '🔖',
  psychology: '🧠',
  rocket_launch: '🚀',
};

export default function CustomStyleModal() {
  const { customStyleModalOpen, editingCustomStyleId, setCustomStyleModalOpen } = useUIStore();
  const { customStyles, addCustomStyle, updateCustomStyle, deleteCustomStyle } =
    useSettingsStore();

  const [name, setName] = useState('');
  const [icon, setIcon] = useState('edit_note');
  const [prompt, setPrompt] = useState('');

  const editing = editingCustomStyleId
    ? customStyles.find((s) => s.id === editingCustomStyleId)
    : null;

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
                  className={`flex-1 p-2 text-center rounded-lg border transition-all text-lg ${
                    icon === ic
                      ? 'border-primary bg-primary/10'
                      : 'border-border hover:border-primary/50'
                  }`}
                >
                  {ICON_EMOJIS[ic]}
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
            <Button onClick={handleSave}>저장</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
