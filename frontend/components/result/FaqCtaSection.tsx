'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, HelpCircle, MousePointerClick } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { FaqSchema, CtaData } from '@/lib/types';

interface FaqCtaSectionProps {
  faqSchema?: FaqSchema;
  cta?: CtaData;
}

interface AccordionItemProps {
  question: string;
  answer: string;
  index: number;
}

function AccordionItem({ question, answer, index }: AccordionItemProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="border border-border/50 rounded-md overflow-hidden">
      <button
        className="w-full flex items-center justify-between px-3 py-2 text-left text-sm font-medium hover:bg-muted/50 transition-colors"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
      >
        <span className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground shrink-0">Q{index + 1}</span>
          {question}
        </span>
        {open ? (
          <ChevronUp className="h-4 w-4 shrink-0 text-muted-foreground" />
        ) : (
          <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
        )}
      </button>
      {open && (
        <div className="px-3 py-2 text-sm text-muted-foreground bg-muted/30 border-t border-border/50">
          {answer}
        </div>
      )}
    </div>
  );
}

export default function FaqCtaSection({ faqSchema, cta }: FaqCtaSectionProps) {
  const hasFaq = faqSchema && faqSchema.mainEntity && faqSchema.mainEntity.length > 0;
  const hasCta = cta && (cta.primary || cta.secondary);

  if (!hasFaq && !hasCta) return null;

  return (
    <div className="mt-4 space-y-3">
      {/* FAQ 아코디언 */}
      {hasFaq && (
        <div className="p-3 border border-border rounded-lg bg-muted/50">
          <div className="flex items-center gap-1.5 mb-2 text-xs font-semibold">
            <HelpCircle className="h-3.5 w-3.5 text-primary" />
            자주 묻는 질문 (FAQ)
          </div>
          <div className="space-y-1.5">
            {faqSchema.mainEntity.map((item, i) => (
              <AccordionItem
                key={i}
                index={i}
                question={item.name}
                answer={item.acceptedAnswer.text}
              />
            ))}
          </div>
        </div>
      )}

      {/* CTA 버튼 */}
      {hasCta && (
        <div className="p-3 border border-border rounded-lg bg-muted/50">
          <div className="flex items-center gap-1.5 mb-2 text-xs font-semibold">
            <MousePointerClick className="h-3.5 w-3.5 text-primary" />
            추천 액션
          </div>
          <div className="flex flex-wrap gap-2">
            {cta.primary && (
              <Button size="sm" variant="default" className="text-xs h-7">
                {cta.primary}
              </Button>
            )}
            {cta.secondary && (
              <Button size="sm" variant="outline" className="text-xs h-7">
                {cta.secondary}
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
