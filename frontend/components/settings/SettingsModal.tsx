'use client';

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useUIStore } from '@/stores/uiStore';
import { useSettingsStore } from '@/stores/settingsStore';
import { Trash2, Bot } from 'lucide-react';
import { clearCache } from '@/lib/api';
import { toast } from 'sonner';

export default function SettingsModal() {
  const { settingsModalOpen, setSettingsModalOpen } = useUIStore();
  const {
    providers,
    selectedProvider,
    selectedModel,
    setSelectedProvider,
    setSelectedModel,
  } = useSettingsStore();

  const providerIds = Object.keys(providers);
  const currentModels = selectedProvider ? providers[selectedProvider]?.models || [] : [];

  async function handleClearCache() {
    try {
      await clearCache();
      toast.success('캐시가 삭제되었습니다.');
    } catch {
      toast.error('캐시 삭제에 실패했습니다.');
    }
  }

  return (
    <Dialog open={settingsModalOpen} onOpenChange={setSettingsModalOpen}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-primary" />
            설정
          </DialogTitle>
          <DialogDescription>AI 서비스와 캐시를 관리합니다</DialogDescription>
        </DialogHeader>

        {/* AI 서비스 */}
        <div className="space-y-3">
          <h3 className="text-sm font-semibold flex items-center gap-2">AI 서비스</h3>

          {providerIds.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              사용 가능한 AI 서비스가 없습니다. Flask 서버를 실행하고 API 키를 설정하세요.
            </p>
          ) : (
            <div className="space-y-2">
              <Select
                value={selectedProvider}
                onValueChange={(v) => {
                  setSelectedProvider(v);
                  const first = providers[v]?.models[0];
                  if (first) setSelectedModel(first.id);
                }}
              >
                <SelectTrigger className="text-sm">
                  <SelectValue placeholder="서비스 선택" />
                </SelectTrigger>
                <SelectContent>
                  {providerIds.map((id) => (
                    <SelectItem key={id} value={id}>
                      {providers[id].name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={selectedModel} onValueChange={setSelectedModel}>
                <SelectTrigger className="text-sm">
                  <SelectValue placeholder="모델 선택" />
                </SelectTrigger>
                <SelectContent>
                  {currentModels.map((m) => (
                    <SelectItem key={m.id} value={m.id}>
                      {m.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
        </div>

        {/* 캐시 관리 */}
        <div className="pt-4 border-t space-y-2">
          <h3 className="text-sm font-semibold">캐시 관리</h3>
          <p className="text-xs text-muted-foreground">
            저장된 자막/댓글 캐시를 삭제합니다.
          </p>
          <Button
            variant="outline"
            className="w-full text-destructive border-destructive/30 hover:bg-destructive/10"
            onClick={handleClearCache}
          >
            <Trash2 className="h-4 w-4 mr-2" />
            전체 캐시 삭제
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
