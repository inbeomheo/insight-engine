'use client';

import { cn } from '@/lib/utils';

/**
 * 입력 컴포넌트 공통 래퍼
 * - 포커스/비포커스 스타일 통일
 * - 하단 에러 메시지 표시 (3초 타임아웃은 사용 측에서 관리)
 */
interface InputWrapperProps {
  focused: boolean;
  error?: string;
  className?: string;
  children: React.ReactNode;
}

export default function InputWrapper({ focused, error, className, children }: InputWrapperProps) {
  return (
    <div className="w-full">
      <div
        className={cn(
          'relative border rounded-2xl bg-white shadow-sm transition-all duration-200',
          focused
            ? 'border-primary/40 shadow-[0_0_0_3px_rgba(79,70,229,0.08)] ring-0'
            : 'border-border/60 hover:border-border',
          className,
        )}
      >
        {children}
      </div>
      {error && (
        <p className="text-xs text-destructive mt-2 px-2 animate-fade-in">{error}</p>
      )}
    </div>
  );
}
