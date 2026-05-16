/**
 * 에러 리포팅 유틸리티
 *
 * Sentry SDK가 로드되어 있으면 captureException 호출, 없으면 console.error로 폴백.
 * 빌드 의존성을 추가하지 않고 옵션 통합을 위해 window 전역 참조 방식 사용.
 *
 * Sentry 통합 시 _app 또는 layout에서 `@sentry/nextjs`를 import하여
 * `window.Sentry`로 노출되도록 초기화 필요.
 */

type SentryGlobal = {
  captureException?: (error: unknown, ctx?: Record<string, unknown>) => void;
  captureMessage?: (msg: string, level?: string) => void;
};

function getSentry(): SentryGlobal | undefined {
  if (typeof window === 'undefined') return undefined;
  const w = window as Window & { Sentry?: SentryGlobal };
  return w.Sentry;
}

export function reportError(
  error: unknown,
  context?: { component?: string; digest?: string; extra?: Record<string, unknown> }
) {
  const sentry = getSentry();
  if (sentry?.captureException) {
    try {
      sentry.captureException(error, context);
      return;
    } catch {
      // fall through to console
    }
  }
  // eslint-disable-next-line no-console
  console.error('[errorReporting]', context?.component ?? 'app', error, context);
}

export function reportMessage(message: string, level: 'info' | 'warning' | 'error' = 'info') {
  const sentry = getSentry();
  if (sentry?.captureMessage) {
    try {
      sentry.captureMessage(message, level);
      return;
    } catch {
      // fall through
    }
  }
  // eslint-disable-next-line no-console
  console[level === 'error' ? 'error' : level === 'warning' ? 'warn' : 'log'](
    '[errorReporting]',
    message
  );
}
