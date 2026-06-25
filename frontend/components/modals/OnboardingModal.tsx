'use client';

import { useState } from 'react';
import { Dialog, DialogContent, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { VisuallyHidden } from '@radix-ui/react-visually-hidden';
import { Button } from '@/components/ui/button';
import { Sparkles, Check, Image as ImageIcon } from 'lucide-react';
import { useUIStore } from '@/stores/uiStore';
import { useSettingsStore } from '@/stores/settingsStore';
import { useTranslation } from '@/hooks/useTranslation';
import { setOnboardingDone } from '@/lib/storage';
import { ALLOWED_GENERATION_PROVIDER_IDS } from '@/lib/constants';
import { TUTORIAL_ONBOARDING_STEPS, type TutorialOnboardingStep } from '@/lib/tutorialAssets';

function TutorialPreview({
  step,
  broken,
  onError,
}: {
  step: TutorialOnboardingStep;
  broken: boolean;
  onError: (id: string) => void;
}) {
  if (broken) {
    return (
      <div className="flex aspect-[16/10] flex-col items-center justify-center gap-2 bg-muted/45 px-4 text-center">
        <ImageIcon className="h-6 w-6 text-muted-foreground/55" />
        <p className="text-sm font-semibold text-foreground">{step.fallbackLabel}</p>
        <p className="text-xs leading-5 text-muted-foreground">{step.description}</p>
      </div>
    );
  }

  return (
    <img
      src={step.imageSrc}
      alt={step.imageAlt}
      loading="lazy"
      className="aspect-[16/10] w-full object-cover"
      onError={() => onError(step.id)}
    />
  );
}

export default function OnboardingModal() {
  const { activeModal, setOnboardingOpen } = useUIStore();
  const onboardingOpen = activeModal === 'onboarding';
  const { providers, selectedProvider, setSelectedProvider, setSelectedModel } =
    useSettingsStore();
  const [brokenImages, setBrokenImages] = useState<Record<string, boolean>>({});

  const providerIds = ALLOWED_GENERATION_PROVIDER_IDS.filter((id) => providers[id]);
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

  function markImageBroken(id: string) {
    setBrokenImages((prev) => ({ ...prev, [id]: true }));
  }

  return (
    <Dialog open={onboardingOpen} onOpenChange={setOnboardingOpen}>
      <DialogContent className="max-h-[calc(100vh-2rem)] max-w-[920px] overflow-y-auto p-0">
        <VisuallyHidden>
          <DialogTitle>{t('onboarding.title')}</DialogTitle>
          <DialogDescription>{t('onboarding.description')}</DialogDescription>
        </VisuallyHidden>
        <div className="px-5 pb-6 pt-7 sm:px-8">
          <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start">
            <div className="gradient-primary flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl shadow-lg shadow-indigo-200/50">
              <Sparkles className="h-7 w-7 text-white" />
            </div>
            <div className="min-w-0">
              <h2 className="mb-2 text-xl font-bold text-foreground">{t('onboarding.title')}</h2>
              <p className="text-sm leading-relaxed text-muted-foreground/75">
                {t('onboarding.description').split('\n').map((line, i) => (
                  <span key={i}>{line}{i === 0 && <br />}</span>
                ))}
              </p>
            </div>
          </div>

          <section className="mb-6" aria-label="사진 기반 온보딩 튜토리얼">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-sm font-bold text-foreground">사진 기반 빠른 안내</h3>
              <p className="text-xs text-muted-foreground">이미지가 없어도 설명으로 계속 진행됩니다</p>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              {TUTORIAL_ONBOARDING_STEPS.map((step, index) => (
                <article
                  key={step.id}
                  className="overflow-hidden rounded-lg border border-border bg-card"
                >
                  <TutorialPreview
                    step={step}
                    broken={Boolean(brokenImages[step.id])}
                    onError={markImageBroken}
                  />
                  <div className="space-y-1 p-3">
                    <p className="text-[11px] font-bold text-primary">STEP {index + 1}</p>
                    <h4 className="text-sm font-bold text-foreground">{step.title}</h4>
                    <p className="text-xs leading-5 text-muted-foreground">{step.description}</p>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section className="border-t border-border pt-5" aria-label="AI 프로바이더 선택">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-sm font-bold text-foreground">사용할 AI 모델 확인</h3>
              <span className="text-xs text-muted-foreground">기본값은 ChatMock/Spark입니다</span>
            </div>

            {providerIds.length > 0 ? (
              <div className="mb-4 grid gap-2 sm:grid-cols-2">
                {providerIds.map((id) => (
                  <button
                    key={id}
                    onClick={() => selectProvider(id)}
                    aria-label={`${id} 프로바이더 선택`}
                    className={`flex w-full items-center gap-3 rounded-xl border-2 p-4 text-left transition-all ${
                      selectedProvider === id
                        ? 'border-primary bg-indigo-50/50 shadow-sm'
                        : 'border-border/50 hover:border-primary/30 hover:bg-muted/30'
                    }`}
                  >
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-medium">{providers[id].name}</div>
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
              <p className="mb-4 rounded-lg border border-border bg-muted/30 p-3 text-center text-xs text-muted-foreground">
                {t('onboarding.noServer')}
              </p>
            )}

            <Button className="h-12 w-full rounded-xl gradient-primary text-base font-medium shadow-md shadow-indigo-200/30 transition-opacity hover:opacity-90" onClick={handleStart}>
              <Check className="mr-2 h-4 w-4" />
              {t('onboarding.start')}
            </Button>
          </section>
        </div>
      </DialogContent>
    </Dialog>
  );
}
