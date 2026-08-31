const SHARE_PATH = /^\/share\/[A-Za-z0-9_-]{8,64}\/?$/;

/**
 * 과거 내부/Tailscale origin으로 저장된 공유 링크를 현재 공개 origin으로 교정한다.
 * 공유 페이지가 아닌 일반 외부 URL은 건드리지 않는다.
 */
export function canonicalizeShareUrl(value: string, publicOrigin?: string): string {
  if (!value) return value;
  const origin = (publicOrigin || (typeof window !== 'undefined' ? window.location.origin : '')).replace(/\/$/, '');
  if (!origin) return value;

  try {
    const parsed = new URL(value, origin);
    if (!SHARE_PATH.test(parsed.pathname)) return value;
    return `${origin}${parsed.pathname.replace(/\/$/, '')}`;
  } catch {
    return value;
  }
}
