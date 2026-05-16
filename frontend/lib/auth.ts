/**
 * 인증 헬퍼 — Bearer 토큰을 자동으로 헤더에 첨부하여 Flask API 호출.
 *
 * Supabase 비활성(로컬 모드)에서는 빈 헤더로 패스스루.
 */
import { getSupabase } from './supabaseClient';

/**
 * 현재 세션의 access_token을 반환. 미인증/미설정 환경에서는 null.
 */
export async function getAccessToken(): Promise<string | null> {
  const supabase = getSupabase();
  if (!supabase) return null;
  try {
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token ?? null;
  } catch {
    return null;
  }
}

/**
 * fetch 래퍼 — Authorization: Bearer <token> 헤더 자동 첨부.
 *
 * 사용 예:
 *   const res = await fetchWithAuth('/api/admin/dashboard');
 *   const data = await res.json();
 */
export async function fetchWithAuth(input: string, init: RequestInit = {}): Promise<Response> {
  const token = await getAccessToken();
  const headers = new Headers(init.headers);
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  return fetch(input, { ...init, headers });
}

/**
 * fetchWithAuth + JSON 파싱 + 에러 처리 콤보. Flask 에러 응답({error: ...})을
 * Error 객체로 변환하여 throw.
 */
export async function fetchJsonWithAuth<T = unknown>(
  input: string,
  init: RequestInit = {}
): Promise<T> {
  const res = await fetchWithAuth(input, init);
  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body?.error) message = body.error;
    } catch {
      // 본문이 JSON이 아니면 status만 사용
    }
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}
