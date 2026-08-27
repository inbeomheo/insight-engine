'use client';

import { Dialog, DialogContent, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { VisuallyHidden } from '@radix-ui/react-visually-hidden';
import { Button } from '@/components/ui/button';
import { Sparkles, Check } from 'lucide-react';
import { useUIStore } from '@/stores/uiStore';
import { useSettingsStore } from '@/stores/settingsStore';
import { useTranslation } from '@/hooks/useTranslation';
import { setOnboardingDone } from '@/lib/storage';

export default function OnboardingModal() {
  const activeModal = useUIStore((state) => state.activeModal);
  const setOnboardingOpen = useUIStore((state) => state.setOnboardingOpen);
  const onboardingOpen = activeModal === 'onboarding';
  const providers = useSettingsStore((state) => state.providers);
  const activeProvider = Object.values(providers)[0] ?? null;
  const hasModels = Boolean(activeProvider?.models.length);
  const { t } = useTranslation();

  // 어떤 경로로 닫히든(시작 버튼 / X / Esc / 오버레이) 완료로 기록한다.
  // 기록을 남기지 않으면 AI 모델 목록을 못 불러오는 동안 매 방문마다 모달이 다시 떠 앱 전체가 잠긴다.
  function dismiss() {
    setOnboardingDone();
    setOnboardingOpen(false);
  }

  return (
    <Dialog open={onboardingOpen} onOpenChange={(open) => { if (!open) dismiss(); }}>
      <DialogContent className="max-w-sm p-8">
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

        {activeProvider ? (
          <div
            role="group"
            aria-label={t('onboarding.serviceInfoLabel')}
            className="mb-4 flex items-center gap-3 rounded-xl border border-primary/20 bg-primary/5 p-4 text-left"
          >
            <div className="flex-1">
              <div className="text-sm font-medium">{activeProvider.name}</div>
              <div className="text-xs text-muted-foreground">
                {t('onboarding.singleService')} · {t('onboarding.modelCount', { count: activeProvider.models.length })}
              </div>
            </div>
            <Check className="h-4 w-4 text-primary" aria-hidden="true" />
          </div>
        ) : (
          <p className="text-xs text-muted-foreground text-center mb-4">
            {t('onboarding.noServer')}
          </p>
        )}
        {activeProvider && !hasModels && (
          <p role="alert" className="mb-4 text-center text-xs text-destructive">
            {t('onboarding.noModels')}
          </p>
        )}

        <Button
          className="w-full h-12 gradient-primary hover:opacity-90 transition-opacity rounded-xl text-base font-medium shadow-md shadow-indigo-200/30"
          onClick={dismiss}
          disabled={!hasModels}
        >
          <Check className="h-4 w-4 mr-2" />
          {t('onboarding.start')}
        </Button>
      </DialogContent>
    </Dialog>
  );
}
