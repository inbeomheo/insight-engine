'use client';

import { useState, useEffect, useCallback, useRef, type KeyboardEvent } from 'react';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useTranslation } from '@/hooks/useTranslation';

interface TourStep {
  target: string; // CSS selector
  titleKey: string;
  descKey: string;
  placement: 'top' | 'bottom' | 'left' | 'right';
}

const TOUR_STEPS: TourStep[] = [
  { target: '#url-input', titleKey: 'tour.step1Title', descKey: 'tour.step1Desc', placement: 'bottom' },
  { target: '[data-testid="blueprint-style-options"]', titleKey: 'tour.step2Title', descKey: 'tour.step2Desc', placement: 'bottom' },
  { target: '[data-testid="generate-dock"]', titleKey: 'tour.step3Title', descKey: 'tour.step3Desc', placement: 'top' },
  { target: '#main-content', titleKey: 'tour.step4Title', descKey: 'tour.step4Desc', placement: 'top' },
];

const STORAGE_KEY = 'ie_tour_done';

interface GuidedTourProps {
  /** 외부에서 투어를 강제 시작할 때 true */
  forceStart?: boolean;
  onClose?: () => void;
}

export default function GuidedTour({ forceStart, onClose }: GuidedTourProps) {
  const [step, setStep] = useState(0);
  const [visible, setVisible] = useState(false);
  const [pos, setPos] = useState({ top: 0, left: 0 });
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);
  const { t } = useTranslation();

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (forceStart) {
      setVisible(true);
      setStep(0);
    }
  }, [forceStart]);
  /* eslint-enable react-hooks/set-state-in-effect */

  // 타겟 요소 위치 계산
  const updatePosition = useCallback(() => {
    if (!visible) return;
    const target = document.querySelector(TOUR_STEPS[step]?.target);
    if (!target) return;

    const rect = target.getBoundingClientRect();
    const placement = TOUR_STEPS[step].placement;
    let top = 0;
    const left = rect.left + rect.width / 2;

    if (placement === 'bottom') {
      top = rect.bottom + 12;
    } else if (placement === 'top') {
      top = rect.top - 12;
    }

    setPos({ top, left: Math.max(180, Math.min(left, window.innerWidth - 180)) });

    // 하이라이트
    target.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, [visible, step]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    updatePosition();
    window.addEventListener('resize', updatePosition);
    return () => window.removeEventListener('resize', updatePosition);
  }, [updatePosition]);

  useEffect(() => {
    if (!visible) return;
    const frame = requestAnimationFrame(() => closeButtonRef.current?.focus());
    return () => cancelAnimationFrame(frame);
  }, [visible, step]);

  const handleNext = () => {
    if (step < TOUR_STEPS.length - 1) {
      setStep(step + 1);
    } else {
      handleClose();
    }
  };

  const handleClose = () => {
    setVisible(false);
    localStorage.setItem(STORAGE_KEY, 'true');
    onClose?.();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Escape') handleClose();
  };

  if (!visible || !TOUR_STEPS[step]) return null;

  const current = TOUR_STEPS[step];
  const isLast = step === TOUR_STEPS.length - 1;
  const titleId = `guided-tour-title-${step}`;
  const descId = `guided-tour-desc-${step}`;

  return (
    <>
      {/* 오버레이 */}
      <div className="fixed inset-0 bg-black/30 z-[60]" onClick={handleClose} />

      {/* 툴팁 */}
      <div
        data-testid="guided-tour-dialog"
        className={cn(
          'fixed z-[61] w-72 bg-white rounded-xl shadow-xl border border-border/60 p-4 animate-fade-in',
          current.placement === 'top' && '-translate-y-full'
        )}
        style={{ top: pos.top, left: pos.left, transform: `translateX(-50%) ${current.placement === 'top' ? 'translateY(-100%)' : ''}` }}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descId}
        onKeyDown={handleKeyDown}
      >
        <button ref={closeButtonRef} data-testid="guided-tour-close" onClick={handleClose} className="absolute top-2 right-2 text-muted-foreground/50 hover:text-foreground" aria-label="가이드 투어 닫기">
          <X className="h-4 w-4" />
        </button>

        <h3 id={titleId} className="font-semibold text-sm mb-1">{t(current.titleKey)}</h3>
        <p id={descId} className="text-xs text-muted-foreground mb-3">{t(current.descKey)}</p>

        <div className="flex items-center justify-between">
          <span className="text-[10px] text-muted-foreground/50">
            {step + 1} / {TOUR_STEPS.length}
          </span>
          <div className="flex gap-1.5">
            <Button data-testid="guided-tour-skip" variant="ghost" size="sm" className="h-7 text-xs" onClick={handleClose}>
              {t('common.skip')}
            </Button>
            <Button data-testid="guided-tour-next" size="sm" className="h-7 text-xs gradient-primary" onClick={handleNext}>
              {isLast ? t('common.done') : t('common.next')}
            </Button>
          </div>
        </div>
      </div>
    </>
  );
}
