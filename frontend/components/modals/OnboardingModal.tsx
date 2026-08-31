'use client';

import { Dialog, DialogContent, DialogTitle, DialogDescription } from '@/components/ui/dialog';

import { Button } from '@/components/ui/button';
import { Sparkles, Check } from 'lucide-react';
import { useUIStore } from '@/stores/uiStore';
import { useSettingsStore } from '@/stores/settingsStore';
import { useTranslation } from '@/hooks/useTranslation';
import { setOnboardingDone } from '@/lib/storage';

export default function OnboardingModal() {
  const { activeModal, setOnboardingOpen } = useUIStore();
  const onboardingOpen = activeModal === 'onboarding';
  const { providers } = useSettingsStore();
  const activeProviders = Object.values(providers);
  const providerNames = activeProviders.map((provider) => provider.name).filter(Boolean);
  const totalModels = activeProviders.reduce((sum, provider) => sum + (provider.models?.length ?? 0), 0);
  const hasModels = totalModels > 0;
  const { t } = useTranslation();

  function handleStart() {
    setOnboardingDone();
    setOnboardingOpen(false);
  }

  return (
    <Dialog open={onboardingOpen} onOpenChange={setOnboardingOpen}>
      <DialogContent className="max-w-sm p-8">
        <div className="text-center mb-8">
          <div className="w-18 h-18 mx-auto mb-5 gradient-primary rounded-2xl flex items-center justify-center shadow-lg shadow-indigo-200/50" style={{width: '72px', height: '72px'}}>
            <Sparkles className="h-8 w-8 text-white" />
          </div>
          <DialogTitle className="text-xl font-bold mb-2 text-foreground">{t('onboarding.title')}</DialogTitle>
          <DialogDescription className="text-sm text-muted-foreground/70 leading-relaxed">
            {t('onboarding.description').split('\n').map((line, i) => (
              <span key={i}>{line}{i === 0 && <br />}</span>
            ))}
          </DialogDescription>
        </div>

        {providerNames.length > 0 ? (
          <div
            role="group"
            aria-label={t('onboarding.serviceInfoLabel')}
            className="mb-4 flex items-center gap-3 rounded-xl border border-primary/20 bg-primary/5 p-4 text-left"
          >
            <div className="flex-1">
              <div className="text-sm font-medium">{providerNames.join(' · ')}</div>
              <div className="text-xs text-muted-foreground">
                {t('onboarding.serviceCount', { count: providerNames.length })} · {t('onboarding.modelCount', { count: totalModels })}
              </div>
            </div>
            <Check className="h-4 w-4 text-primary" aria-hidden="true" />
          </div>
        ) : (
          <p className="text-xs text-muted-foreground text-center mb-4">
            {t('onboarding.noServer')}
          </p>
        )}
        {providerNames.length > 0 && !hasModels && (
          <p role="alert" className="mb-4 text-center text-xs text-destructive">
            {t('onboarding.noModels')}
          </p>
        )}

        <Button disabled={!hasModels} className="w-full h-12 gradient-primary hover:opacity-90 transition-opacity rounded-xl text-base font-medium shadow-md shadow-indigo-200/30" onClick={handleStart}>
          <Check className="h-4 w-4 mr-2" />
          {t('onboarding.start')}
        </Button>
      </DialogContent>
    </Dialog>
  );
}
