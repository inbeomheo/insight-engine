'use client';

import { useEffect, useState } from 'react';
import { useApiCall } from '@/hooks/useApiCall';

export default function NotionConnect() {
  const [apiKey, setApiKey] = useState('');
  const [configured, setConfigured] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // 상태 조회용 / 테스트용 API 호출 분리
  const statusCall = useApiCall<{ configured: boolean }>();
  const testCall = useApiCall<{ error?: string }>();

  useEffect(() => {
    fetch('/api/notion/status')
      .then((res) => res.json())
      .then((data) => setConfigured(data.configured))
      .catch(() => setConfigured(false));
  }, []);

  const handleTest = async () => {
    if (!apiKey.trim()) {
      setMessage({ type: 'error', text: 'API 키를 입력해주세요.' });
      return;
    }

    setMessage(null);

    const result = await testCall.execute(async () => {
      const res = await fetch('/api/notion/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: '', api_key: apiKey }),
      });
      const data = await res.json();

      if (res.ok || data.error?.includes('URL')) {
        // URL 오류는 API 키 자체는 유효한 것으로 간주
        setMessage({ type: 'success', text: 'API 키가 설정되었습니다. Notion 페이지 URL을 입력하여 사용하세요.' });
      } else {
        setMessage({ type: 'error', text: data.error || '연결 실패' });
      }
      return data;
    }, '서버 연결에 실패했습니다.');
  };

  if (statusCall.isLoading) {
    return <p className="text-sm text-muted-foreground">Notion 연결 상태 확인 중...</p>;
  }

  return (
    <div className="space-y-3">
      <label className="text-sm font-medium text-muted-foreground block">
        Notion 연동
      </label>

      <div className="flex items-center gap-2 text-sm">
        <span
          className={`w-2 h-2 rounded-full ${configured ? 'bg-green-500' : 'bg-gray-400'}`}
        />
        <span className="text-muted-foreground">
          {configured ? '환경변수로 설정됨' : '미설정'}
        </span>
      </div>

      {!configured && (
        <div className="space-y-2">
          <input
            type="password"
            placeholder="Notion Integration API 키"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background"
          />
          <button
            onClick={handleTest}
            disabled={testCall.isLoading}
            aria-label="Notion 연결 테스트"
            className="px-3 py-1.5 text-sm rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {testCall.isLoading ? '확인 중...' : '연결 테스트'}
          </button>
        </div>
      )}

      {message && (
        <p className={`text-xs ${message.type === 'success' ? 'text-green-600' : 'text-destructive'}`}>
          {message.text}
        </p>
      )}
    </div>
  );
}
