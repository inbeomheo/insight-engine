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
          'relative rounded-sm border bg-white transition-all duration-200',
          focused
            ? 'border-foreground ring-0 signal-input-shadow'
            : 'border-border hover:border-foreground/50',
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
