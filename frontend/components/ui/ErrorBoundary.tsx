'use client';

import { Component, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface Props {
  children: ReactNode;
  /** 에러 시 대체 표시할 커스텀 UI */
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * 컴포넌트별 에러 바운더리 — 하위 트리 렌더링 오류를 격리
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      return (
        <div className="flex flex-col items-center justify-center gap-3 p-6 rounded-xl border border-destructive/20 bg-destructive/5 text-center" role="alert">
          <div className="w-10 h-10 rounded-full bg-destructive/10 flex items-center justify-center">
            <AlertTriangle className="h-5 w-5 text-destructive" />
          </div>
          <div>
            <p className="text-sm font-medium text-foreground mb-1">이 영역에서 문제가 발생했습니다</p>
            <p className="text-xs text-muted-foreground">
              {this.state.error?.message || '알 수 없는 오류'}
            </p>
          </div>
          <Button variant="outline" size="sm" className="gap-1.5" onClick={this.handleReset}>
            <RefreshCw className="h-3.5 w-3.5" />
            복구하기
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}
