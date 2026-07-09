'use client';

import { useState, useCallback } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Eye, EyeOff, Loader2, CheckCircle2, XCircle, Circle } from 'lucide-react';
import { validateProvider } from '@/lib/api';
import type { ProviderInfo } from '@/lib/types';

// 프로바이더별 라벨 (SVG 아이콘 대신 텍스트 약어)
const PROVIDER_LABELS: Record<string, string> = {
  chatmock: 'CM',
  gemini: 'G',
  deepseek: 'DS',
  zhipuai: 'ZH',
  openrouter: 'OR',
  openai: 'AI',
  anthropic: 'AN',
};

type ValidationStatus = 'untested' | 'testing' | 'valid' | 'invalid';

interface ProviderState {
  apiKey: string;
  showKey: boolean;
  status: ValidationStatus;
  error?: string;
}

interface ProviderSetupProps {
  providers: Record<string, ProviderInfo>;
}

export default function ProviderSetup({ providers }: ProviderSetupProps) {
  const providerIds = Object.keys(providers);

  const [states, setStates] = useState<Record<string, ProviderState>>(() => {
    const init: Record<string, ProviderState> = {};
    for (const id of providerIds) {
      init[id] = { apiKey: '', showKey: false, status: 'untested' };
    }
    return init;
  });

  const updateState = useCallback((id: string, partial: Partial<ProviderState>) => {
    setStates((prev) => ({ ...prev, [id]: { ...prev[id], ...partial } }));
  }, []);

  const handleTest = useCallback(async (providerId: string) => {
    const state = states[providerId];
    const isChatMock = providerId === 'chatmock';

    if (!isChatMock && !state.apiKey) return;

    updateState(providerId, { status: 'testing', error: undefined });

    try {
      const result = await validateProvider(providerId, state.apiKey || 'dummy');
      if (result.valid) {
        updateState(providerId, { status: 'valid' });
      } else {
        updateState(providerId, { status: 'invalid', error: result.error });
      }
    } catch (err) {
      updateState(providerId, {
        status: 'invalid',
        error: err instanceof Error ? err.message : '테스트 실패',
      });
    }
  }, [states, updateState]);

  const statusIcon = (status: ValidationStatus) => {
    switch (status) {
      case 'testing':
        return <Loader2 className="h-4 w-4 animate-spin text-yellow-500" />;
      case 'valid':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case 'invalid':
        return <XCircle className="h-4 w-4 text-red-500" />;
      default:
        return <Circle className="h-4 w-4 text-[var(--text-tertiary)]" />;
    }
  };

  const statusBadge = (status: ValidationStatus) => {
    const map: Record<ValidationStatus, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
      untested: { label: '미검증', variant: 'outline' },
      testing: { label: '검증 중…', variant: 'secondary' },
      valid: { label: '유효', variant: 'default' },
      invalid: { label: '무효', variant: 'destructive' },
    };
    const { label, variant } = map[status];
    return <Badge variant={variant}>{label}</Badge>;
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-[var(--text-primary)]">
          AI 프로바이더 설정
        </h3>
        <p className="text-xs text-[var(--text-tertiary)]">
          API 키는 서버 .env에서 관리됩니다
        </p>
      </div>

      {/* 활성 프로바이더 우선순위 */}
      <div className="rounded-lg border border-[var(--border-primary)] p-3">
        <p className="mb-2 text-xs font-medium text-[var(--text-secondary)]">
          활성 프로바이더 (우선순위 순)
        </p>
        <ol className="space-y-1">
          {providerIds.map((id, idx) => (
            <li
              key={id}
              className="flex items-center gap-2 text-sm text-[var(--text-primary)]"
            >
              <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-[var(--accent-primary)] text-xs font-bold text-white">
                {idx + 1}
              </span>
              <span>{PROVIDER_LABELS[id] || 'AI'}</span>
              <span>{providers[id].name}</span>
              {statusIcon(states[id]?.status ?? 'untested')}
            </li>
          ))}
        </ol>
      </div>

      {/* 프로바이더별 키 입력 + 테스트 */}
      <div className="space-y-3">
        {providerIds.map((id) => {
          const provider = providers[id];
          const state = states[id];
          const isChatMock = id === 'chatmock';

          return (
            <div
              key={id}
              className="rounded-lg border border-[var(--border-primary)] p-3 space-y-2"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-lg">{PROVIDER_LABELS[id] || 'AI'}</span>
                  <span className="text-sm font-medium text-[var(--text-primary)]">
                    {provider.name}
                  </span>
                </div>
                {statusBadge(state.status)}
              </div>

              {isChatMock && (
                <div className="rounded-md border border-blue-500/20 bg-blue-500/5 p-3 text-xs text-[var(--text-secondary)]">
                  <p className="font-medium text-[var(--text-primary)]">ChatMock 실행 순서</p>
                  <ol className="mt-1 list-decimal space-y-1 pl-4">
                    <li><code>pipx install chatmock</code> 또는 Homebrew로 설치</li>
                    <li><code>chatmock login</code></li>
                    <li><code>chatmock serve</code></li>
                  </ol>
                  <p className="mt-2">
                    Base URL: <code>{provider.api_base || 'http://127.0.0.1:8000/v1'}</code> · API key는 <code>dummy</code>
                  </p>
                </div>
              )}

              <div className="flex gap-2">
                {!isChatMock && (
                  <div className="relative flex-1">
                    <Input
                      type={state.showKey ? 'text' : 'password'}
                      placeholder="API 키 입력"
                      value={state.apiKey}
                      onChange={(e) => updateState(id, { apiKey: e.target.value, status: 'untested' })}
                      className="pr-9 text-sm"
                    />
                    <button
                      type="button"
                      onClick={() => updateState(id, { showKey: !state.showKey })}
                      aria-label={state.showKey ? 'API 키 숨기기' : 'API 키 보기'}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]"
                    >
                      {state.showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                )}
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleTest(id)}
                  disabled={state.status === 'testing' || (!isChatMock && !state.apiKey)}
                  className={isChatMock ? 'w-full' : undefined}
                >
                  {state.status === 'testing' ? (
                    <Loader2 className="h-3 w-3 animate-spin mr-1" />
                  ) : null}
                  테스트
                </Button>
              </div>

              {state.status === 'invalid' && state.error && (
                <p className="text-xs text-red-500">{state.error}</p>
              )}

              {/* 모델 목록 */}
              <div className="flex flex-wrap gap-1">
                {provider.models.map((m) => (
                  <Badge key={m.id} variant="outline" className="text-xs">
                    {m.name}
                  </Badge>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
