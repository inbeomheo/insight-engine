'use client';

import { useState } from 'react';
import { X, BookOpen, Keyboard, HelpCircle, ChevronDown, ChevronRight, Globe, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { useTranslation } from '@/hooks/useTranslation';

interface HelpPanelProps {
  open: boolean;
  onClose: () => void;
}

interface FaqItemProps {
  question: string;
  answer: string;
}

function FaqItem({ question, answer }: FaqItemProps) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="border-b border-border/30 last:border-0">
      <button
        className="w-full flex items-center gap-2 py-3 text-left text-sm hover:text-primary transition-colors"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
      >
        {expanded ? <ChevronDown className="h-3.5 w-3.5 shrink-0" /> : <ChevronRight className="h-3.5 w-3.5 shrink-0" />}
        <span className="font-medium">{question}</span>
      </button>
      {expanded && (
        <p className="text-xs text-muted-foreground pb-3 pl-5.5 animate-fade-in">{answer}</p>
      )}
    </div>
  );
}

export default function HelpPanel({ open, onClose }: HelpPanelProps) {
  const { t } = useTranslation();

  if (!open) return null;

  return (
    <>
      {/* 오버레이 */}
      <div className="fixed inset-0 bg-black/10 z-40" onClick={onClose} />

      {/* 패널 */}
      <aside
        className={cn(
          'fixed right-0 top-0 h-full w-80 sm:w-96 bg-white border-l border-border/60 z-50',
          'shadow-xl animate-slide-in-right'
        )}
        role="complementary"
        aria-label={t('help.title')}
      >
        {/* 헤더 */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border/40">
          <h2 className="font-semibold text-base flex items-center gap-2">
            <HelpCircle className="h-4.5 w-4.5 text-primary" />
            {t('help.title')}
          </h2>
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onClose} aria-label={t('common.close')}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        <ScrollArea className="h-[calc(100%-60px)]">
          <div className="p-5 space-y-6">
            {/* 시작하기 */}
            <section>
              <h3 className="flex items-center gap-2 text-sm font-semibold mb-2">
                <Zap className="h-4 w-4 text-amber-500" />
                {t('help.gettingStarted')}
              </h3>
              <p className="text-xs text-muted-foreground leading-relaxed">
                {t('help.gettingStartedDesc')}
              </p>
            </section>

            {/* 지원 소스 */}
            <section>
              <h3 className="flex items-center gap-2 text-sm font-semibold mb-2">
                <Globe className="h-4 w-4 text-blue-500" />
                {t('help.supportedSources')}
              </h3>
              <p className="text-xs text-muted-foreground leading-relaxed">
                {t('help.supportedSourcesDesc')}
              </p>
            </section>

            {/* 단축키 */}
            <section>
              <h3 className="flex items-center gap-2 text-sm font-semibold mb-2">
                <Keyboard className="h-4 w-4 text-green-500" />
                {t('help.shortcuts')}
              </h3>
              <p className="text-xs text-muted-foreground leading-relaxed">
                {t('help.shortcutsDesc')}
              </p>
              <div className="mt-2 space-y-1.5">
                {[
                  { key: 'Enter', desc: 'URL 추가 / 생성 시작' },
                  { key: 'Ctrl+V', desc: '다중 URL 붙여넣기' },
                  { key: 'Esc', desc: '모달 닫기' },
                ].map(({ key, desc }) => (
                  <div key={key} className="flex items-center gap-2 text-xs">
                    <kbd className="px-1.5 py-0.5 bg-muted/60 rounded text-[10px] font-mono border border-border/50">
                      {key}
                    </kbd>
                    <span className="text-muted-foreground">{desc}</span>
                  </div>
                ))}
              </div>
            </section>

            {/* FAQ */}
            <section>
              <h3 className="flex items-center gap-2 text-sm font-semibold mb-2">
                <BookOpen className="h-4 w-4 text-purple-500" />
                {t('help.faq')}
              </h3>
              <div>
                <FaqItem question={t('help.faqApiKey')} answer={t('help.faqApiKeyAnswer')} />
                <FaqItem question={t('help.faqOffline')} answer={t('help.faqOfflineAnswer')} />
              </div>
            </section>
          </div>
        </ScrollArea>
      </aside>
    </>
  );
}
