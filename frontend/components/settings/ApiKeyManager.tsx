'use client';

import { memo, useEffect, useState } from 'react';
import { Key, Plus, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { toast } from 'sonner';
import { useApiCall } from '@/hooks/useApiCall';
import { apiUrl } from '@/lib/api';

interface ApiKeyInfo {
  key_id: string;
  name: string;
  key_preview: string;
  usage_count: number;
  created_at: string;
  last_used_at: string | null;
}

export const ApiKeyManager = memo(function ApiKeyManager() {
  const [keys, setKeys] = useState<ApiKeyInfo[]>([]);
  const [newKeyName, setNewKeyName] = useState('');
  const [revokeTarget, setRevokeTarget] = useState<ApiKeyInfo | null>(null);

  const createCall = useApiCall<{ key?: string; error?: string }>();
  const revokeCall = useApiCall<void>();

  const fetchKeys = () => {
    fetch(apiUrl('/api/keys'))
      .then((r) => (r.ok ? r.json() : { keys: [] }))
      .then((d) => setKeys(d.keys ?? []))
      .catch(() => {});
  };

  useEffect(fetchKeys, []);

  const handleCreate = async () => {
    await createCall.execute(async () => {
      const res = await fetch(apiUrl('/api/keys'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newKeyName || 'default' }),
      });
      const data = await res.json();
      if (data.key) {
        // 생성된 키를 클립보드에 복사
        await navigator.clipboard.writeText(data.key);
        toast.success('API 키가 생성되어 클립보드에 복사되었습니다. 이 키는 다시 볼 수 없으니 안전하게 보관하세요.');
        setNewKeyName('');
        fetchKeys();
      } else {
        toast.error(data.error || 'API 키 생성 실패');
      }
      return data;
    }, '요청 중 오류가 발생했습니다.');
  };

  const handleRevoke = async (keyId: string) => {
    await revokeCall.execute(async () => {
      const res = await fetch(apiUrl(`/api/keys/${keyId}`), { method: 'DELETE' });
      if (res.ok) {
        toast.success('API 키가 비활성화되었습니다.');
        setRevokeTarget(null);
        fetchKeys();
      } else {
        toast.error('삭제에 실패했습니다.');
      }
    }, '요청 중 오류가 발생했습니다.');
  };

  return (
    <>
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Key className="h-5 w-5 text-primary" />
        <h3 className="font-semibold">API 키 관리</h3>
      </div>

      {/* 키 생성 */}
      <div className="flex gap-2">
        <Input
          placeholder="키 이름 (선택)"
          value={newKeyName}
          onChange={(e) => setNewKeyName(e.target.value)}
          className="max-w-xs"
        />
        <Button onClick={handleCreate} disabled={createCall.isLoading} size="sm">
          <Plus className="h-4 w-4 mr-1" />
          {createCall.isLoading ? '생성 중...' : '새 키 생성'}
        </Button>
      </div>

      {/* 키 목록 */}
      {keys.length === 0 ? (
        <p className="text-sm text-muted-foreground">발급된 API 키가 없습니다.</p>
      ) : (
        <div className="space-y-2">
          {keys.map((k) => (
            <div key={k.key_id} className="flex items-center gap-3 rounded border p-3 text-sm">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{k.name}</span>
                  <code className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                    {k.key_preview}
                  </code>
                </div>
                <div className="text-xs text-muted-foreground mt-0.5">
                  사용: {k.usage_count}회
                  {k.last_used_at && ` | 마지막: ${new Date(k.last_used_at).toLocaleDateString('ko-KR')}`}
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-destructive hover:text-destructive"
                onClick={() => setRevokeTarget(k)}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
    <Dialog open={Boolean(revokeTarget)} onOpenChange={(open) => !open && setRevokeTarget(null)}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-destructive">
            <Trash2 className="h-5 w-5" />
            API 키 비활성화
          </DialogTitle>
          <DialogDescription>
            “{revokeTarget?.name}” 키를 비활성화합니다. 이 작업은 되돌릴 수 없습니다.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => setRevokeTarget(null)}>
            취소
          </Button>
          <Button
            type="button"
            variant="destructive"
            onClick={() => revokeTarget && handleRevoke(revokeTarget.key_id)}
            disabled={revokeCall.isLoading}
          >
            비활성화
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
    </>
  );
});
