'use client';

import { Trash2, Settings, Zap, FileText, Search, RefreshCw, ShieldCheck, Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { PipelineStepDef } from './PipelineBuilder';

const STEP_ICONS: Record<string, typeof Zap> = {
  transcript: FileText,
  generate: Zap,
  seo: Search,
  rewrite: RefreshCw,
  qa: ShieldCheck,
  publish: Send,
};

interface PipelineNodeProps {
  step: PipelineStepDef;
  onRemove: () => void;
  onConfigChange: (config: Record<string, string>) => void;
}

/** 파이프라인 단일 노드 (F5-03) */
export default function PipelineNode({ step, onRemove, onConfigChange }: PipelineNodeProps) {
  const Icon = STEP_ICONS[step.type] || Zap;

  return (
    <div className="group border border-border/60 rounded-lg bg-white dark:bg-zinc-900 p-3 hover:border-primary/30 transition-colors">
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 rounded-lg bg-primary/8 flex items-center justify-center shrink-0">
          <Icon className="h-4 w-4 text-primary" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium">{step.label}</div>
          <div className="text-[11px] text-muted-foreground/60">
            {step.type === 'generate' && step.config.style
              ? `스타일: ${step.config.style}`
              : step.type}
          </div>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground/40 hover:text-destructive"
          onClick={onRemove}
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* 설정 영역: generate 타입일 때만 스타일 선택 표시 */}
      {step.type === 'generate' && (
        <div className="mt-2 pt-2 border-t border-border/30">
          <label className="text-[11px] text-muted-foreground/60">스타일</label>
          <select
            value={step.config.style || 'blog_seo'}
            onChange={(e) => onConfigChange({ style: e.target.value })}
            className="mt-1 w-full text-xs border border-border/40 rounded px-2 py-1 bg-white dark:bg-zinc-800"
          >
            <option value="blog_seo">블로그 SEO</option>
            <option value="summary">요약</option>
            <option value="tutorial">튜토리얼</option>
            <option value="newsletter">뉴스레터</option>
            <option value="sns_post">SNS 포스트</option>
            <option value="shorts_script">Shorts 스크립트</option>
          </select>
        </div>
      )}

      {step.type === 'rewrite' && (
        <div className="mt-2 pt-2 border-t border-border/30">
          <label className="text-[11px] text-muted-foreground/60">플랫폼</label>
          <select
            value={step.config.platform || 'twitter'}
            onChange={(e) => onConfigChange({ platform: e.target.value })}
            className="mt-1 w-full text-xs border border-border/40 rounded px-2 py-1 bg-white dark:bg-zinc-800"
          >
            <option value="twitter">Twitter</option>
            <option value="linkedin">LinkedIn</option>
            <option value="instagram">Instagram</option>
            <option value="threads">Threads</option>
          </select>
        </div>
      )}
    </div>
  );
}
