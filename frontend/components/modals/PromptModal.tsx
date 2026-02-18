'use client';

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Copy, Code } from 'lucide-react';
import { useUIStore } from '@/stores/uiStore';
import { toast } from 'sonner';

export default function PromptModal() {
  const { promptModalOpen, activePrompt, setPromptModalOpen } = useUIStore();

  function handleCopy() {
    navigator.clipboard.writeText(activePrompt);
    toast.success('프롬프트 복사 완료');
  }

  return (
    <Dialog open={promptModalOpen} onOpenChange={(v) => setPromptModalOpen(v)}>
      <DialogContent className="max-w-3xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Code className="h-5 w-5 text-primary" />
            AI 입력 프롬프트
          </DialogTitle>
          <DialogDescription>AI에 전달된 전체 프롬프트를 확인합니다</DialogDescription>
        </DialogHeader>

        <div className="flex justify-end">
          <Button variant="ghost" size="sm" className="text-xs" onClick={handleCopy}>
            <Copy className="h-3.5 w-3.5 mr-1" />
            복사
          </Button>
        </div>

        <ScrollArea className="flex-1 max-h-[60vh]">
          <pre className="text-xs font-mono leading-relaxed text-muted-foreground whitespace-pre-wrap p-4 bg-muted rounded-lg">
            {activePrompt || '프롬프트가 없습니다.'}
          </pre>
        </ScrollArea>

        <div className="text-xs text-muted-foreground pt-2 border-t">
          {activePrompt.length.toLocaleString()}자 · 스타일 프롬프트 + 자막 + 댓글
        </div>
      </DialogContent>
    </Dialog>
  );
}
