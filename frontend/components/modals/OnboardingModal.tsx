'use client';

import { type KeyboardEvent } from 'react';
import { Dialog, DialogContent, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { VisuallyHidden } from '@radix-ui/react-visually-hidden';
import { Button } from '@/components/ui/button';
import { Sparkles, Check } from 'lucide-react';
import { useUIStore } from '@/stores/uiStore';
import { useSettingsStore } from '@/stores/settingsStore';
import { useTranslation } from '@/hooks/useTranslation';
import { setOnboardingDone } from '@/lib/storage';

export default function OnboardingModal() {
  const { activeModal, setOnboardingOpen } = useUIStore();
  const onboardingOpen = activeModal === 'onboarding';
  const { providers, selectedProvider, setSelectedProvider, setSelectedModel } =
    useSettingsStore();

  const providerIds = Object.keys(providers);
  const { t } = useTranslation();

  function handleStart() {
    setOnboardingDone();
    setOnboardingOpen(false);
  }

  function selectProvider(id: string) {
    setSelectedProvider(id);
    const first = providers[id]?.models[0];
    if (first) setSelectedModel(first.id);
  }

  function focusProvider(id: string) {
    requestAnimationFrame(() => document.querySelector<HTMLButtonElement>(`[data-testid='onboarding-provider-${id}']`)?.focus());
  }

  function handleProviderKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    if (!['ArrowRight', 'ArrowDown', 'ArrowLeft', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const nextIndex =
      event.key === 'Home'
        ? 0
        : event.key === 'End'
          ? providerIds.length - 1
          : (index + (['ArrowRight', 'ArrowDown'].includes(event.key) ? 1 : -1) + providerIds.length) % providerIds.length;
    const nextId = providerIds[nextIndex];
    selectProvider(nextId);
    focusProvider(nextId);
  }

  return (
    <Dialog open={onboardingOpen} onOpenChange={setOnboardingOpen}>
      <DialogContent aria-modal="true" className="max-w-sm p-8">
        <VisuallyHidden>
          <DialogTitle>{t('onboarding.title')}</DialogTitle>
          <DialogDescription>{t('onboarding.description')}</DialogDescription>
        </VisuallyHidden>
        <div className="text-center mb-8">
          <div className="w-18 h-18 mx-auto mb-5 gradient-primary rounded-2xl flex items-center justify-center shadow-lg shadow-indigo-200/50" style={{width: '72px', height: '72px'}}>
            <Sparkles className="h-8 w-8 text-white" />
          </div>
          <h2 className="text-xl font-bold mb-2 text-foreground">{t('onboarding.title')}</h2>
          <p className="text-sm text-muted-foreground/70 leading-relaxed">
            {t('onboarding.description').split('\n').map((line, i) => (
              <span key={i}>{line}{i === 0 && <br />}</span>
            ))}
          </p>
        </div>

        {providerIds.length > 0 ? (
          <div data-testid="onboarding-provider-options" role="radiogroup" aria-label="AI 프로바이더" className="space-y-2 mb-4">
            {providerIds.map((id, index) => (
              <button
                key={id}
                type="button"
                data-testid={`onboarding-provider-${id}`}
                onClick={() => selectProvider(id)}
                onKeyDown={(event) => handleProviderKeyDown(event, index)}
                aria-label={`${providers[id].name} 프로바이더 선택`}
                role="radio"
                aria-checked={selectedProvider === id}
                tabIndex={selectedProvider === id ? 0 : -1}
                className={`w-full flex items-center gap-3 p-4 rounded-xl border-2 transition-all text-left ${
                  selectedProvider === id
                    ? 'border-primary bg-indigo-50/50 shadow-sm'
                    : 'border-border/50 hover:border-primary/30 hover:bg-muted/30'
                }`}
              >
                <div className="flex-1">
                  <div className="text-sm font-medium">{providers[id].name}</div>
                  <div className="text-xs text-muted-foreground">
                    {t('onboarding.modelCount', { count: providers[id].models.length })}
                  </div>
                </div>
                {selectedProvider === id && (
                  <Check className="h-4 w-4 text-primary" />
                )}
              </button>
            ))}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground text-center mb-4">
            {t('onboarding.noServer')}
          </p>
        )}

        <Button data-testid="onboarding-start" className="w-full h-12 gradient-primary hover:opacity-90 transition-opacity rounded-xl text-base font-medium shadow-md shadow-indigo-200/30" onClick={handleStart}>
          <Check className="h-4 w-4 mr-2" />
          {t('onboarding.start')}
        </Button>
      </DialogContent>
    </Dialog>
  );
}
